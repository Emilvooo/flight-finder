#!/usr/bin/env python3
"""
Flight Finder - Vind creatief de goedkoopste vluchten door nabijgelegen airports te doorzoeken.

Usage:
    python3 flight_finder.py
    python3 flight_finder.py --to bratislava --depart 2026-06-18 --return 2026-06-21
    python3 flight_finder.py --to "brugge" --depart 2026-07-01 --home AMS --radius 200
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime, timedelta
from math import asin, cos, radians, sin, sqrt

import airportsdata
from airports.airport_data import get_airport_by_iata as _get_ap
from fast_flights import FlightData, Passengers, create_filter
from fast_flights.schema import Flight, Result
from primp import Client
from selectolax.lexbor import LexborHTMLParser
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
)
from rich.table import Table

console = Console()

AIRPORT_DB = airportsdata.load("IATA")

CONSENT_COOKIES = {
    "CONSENT": "PENDING+987",
    "SOCS": "CAISHAgCEhJnd3NfMjAyNDAxMTAtMF9SQzIaAmVuIAEaBgiA_LyaBg",
}

DEFAULT_HOME = "7991AW"
DEFAULT_RADIUS_DEST = 250
DEFAULT_RADIUS_ORIGIN = 350
DEFAULT_MAX_DEST = 1
DEFAULT_MAX_ORIGIN = 5
REQUEST_DELAY = 0.3

_ap_info_cache: dict[str, dict | None] = {}


def _ap_info(iata: str) -> dict | None:
    """Cached lookup of airports-py data for an IATA code."""
    if iata not in _ap_info_cache:
        result = _get_ap(iata)
        _ap_info_cache[iata] = result[0] if result else None
    return _ap_info_cache[iata]


# ──────────────────────────────────────────────
# AIRPORT DISCOVERY
# ──────────────────────────────────────────────


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


def iata_code(query: str) -> str | None:
    code = query.strip().upper()
    return code if len(code) == 3 and code in AIRPORT_DB else None


def lookup_airport(query: str) -> str | None:
    code = iata_code(query)
    if code:
        return code

    # Loose substring matching would turn "assen" into Massena (Canada).
    q_lower = query.strip().lower()
    exact, prefix = [], []
    word_start = re.compile(rf"\b{re.escape(q_lower)}")
    for iata, ap in AIRPORT_DB.items():
        city = (ap.get("city") or "").lower()
        if not city or airport_score(iata, ap) < 2:
            continue
        if city == q_lower:
            exact.append(iata)
        elif len(q_lower) >= 4 and word_start.search(city):
            prefix.append(iata)

    matches = exact or prefix
    return max(matches, key=lambda c: airport_score(c, AIRPORT_DB[c])) if matches else None


def search_airports(query: str, near: tuple[float, float] | None = None, limit: int = 8) -> list[dict]:
    q = query.strip().lower()
    if len(q) < 2:
        return []

    word_start = re.compile(rf"\b{re.escape(q)}")
    hits = []
    for iata, ap in AIRPORT_DB.items():
        code = iata.lower()
        city = (ap.get("city") or "").lower()
        name = (ap.get("name") or "").lower()
        if code == q:
            rank = 0
        elif city == q:
            rank = 1
        elif code.startswith(q) or word_start.search(city):
            rank = 2
        elif word_start.search(name):
            rank = 3
        else:
            continue
        score = airport_score(iata, ap)
        if score < 2 and rank > 0:
            continue
        km = round(haversine(near[0], near[1], ap["lat"], ap["lon"])) if near else None
        # Nearby first (driving or regional distance), then match quality, then bigger airports.
        # So "rot" near home gives Rotterdam before Rotorua, whose code is ROT.
        nearness = 0 if km is None or km <= 600 else 1 if km <= 2500 else 2
        hits.append((nearness, rank, -score, km or 0, iata, ap, km))

    hits.sort(key=lambda h: h[:4])
    return [_airport_entry(iata, ap, km) for *_, iata, ap, km in hits[:limit]]


def airports_around(
    place: tuple[float, float], near: tuple[float, float] | None = None, radius_km: int = 100, limit: int = 8
) -> list[dict]:
    # For place names the airport database does not know, such as Dutch "Wenen" or "Praag".
    hits = []
    for iata, ap in AIRPORT_DB.items():
        score = airport_score(iata, ap)
        if score < 2 or haversine(place[0], place[1], ap["lat"], ap["lon"]) > radius_km:
            continue
        km = round(haversine(near[0], near[1], ap["lat"], ap["lon"])) if near else None
        hits.append((-score, haversine(place[0], place[1], ap["lat"], ap["lon"]), iata, ap, km))
    hits.sort(key=lambda h: h[:2])
    return [_airport_entry(iata, ap, km) for *_, iata, ap, km in hits[:limit]]


def _airport_entry(iata: str, ap: dict, km: int | None) -> dict:
    return {
        "code": iata,
        "city": ap.get("city") or ap.get("name", iata),
        "name": ap.get("name", ""),
        "country": ap.get("country", ""),
        "km": km,
    }


def resolve_location(query: str) -> tuple[float, float, str] | None:
    q = query.strip()

    code = lookup_airport(q)
    if code:
        ap = AIRPORT_DB[code]
        return ap["lat"], ap["lon"], f"{ap['city']} ({code})"

    # 3. Nominatim geocoding fallback (OpenStreetMap, no API key needed).
    # Only hits are cached, so a network failure can be retried.
    key = q.lower()
    if key in _geocoded:
        return _geocoded[key]
    try:
        client = Client(impersonate=IMPERSONATE, verify=False)
        res = client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": q, "format": "json", "limit": "1"},
            headers={"User-Agent": "FlightFinder/1.0"},
        )
        data = res.json()
        if data:
            lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
            parts = [p.strip() for p in data[0].get("display_name", q).split(",")]
            # A postcode alone means little to people, so add the town: "7991 AW, Dwingeloo".
            label = ", ".join(parts[:2]) if data[0].get("type") == "postcode" else parts[0]
            _geocoded[key] = (lat, lon, f"{label} (via geocoding)")
            return _geocoded[key]
    except Exception:
        pass

    return None


_geocoded: dict[str, tuple[float, float, str]] = {}


def airport_score(iata: str, ap: dict) -> int:
    """Score airport by likelihood of having commercial flights.
    Uses airports-py (OurAirports data) for scheduled_service and type.
    Returns -1 to exclude, 0+ as ranking score."""
    info = _ap_info(iata)

    if info and info.get("scheduled_service") == "TRUE":
        tp = info.get("type", "")
        if tp == "large_airport":
            return 15
        if tp == "medium_airport":
            return 5
        return 3  # scheduled but small/other type

    # No airports-py data or not scheduled — fall back to name heuristics
    name = (ap.get("name") or "").lower()
    if iata.startswith("Q"):
        return -1
    for kw in ("air base", "afb", "military", "heliport", "helipad",
               "air force", "naval", "army", "seaplane", "flying club",
               "executive", "general aviation", "aeroclub", "glider",
               "ultralight", "privat"):
        if kw in name:
            return -1
    if "international" in name:
        return 2
    return 0


def find_nearby_airports(
    query: str,
    radius_km: int = DEFAULT_RADIUS_DEST,
    max_count: int = DEFAULT_MAX_DEST,
) -> tuple[dict[str, str], str] | None:
    location = resolve_location(query)
    if not location:
        return None

    lat, lon, label = location
    pinned = iata_code(query)

    nearby = []
    for iata, ap in AIRPORT_DB.items():
        sc = airport_score(iata, ap)
        if sc < 2 and iata != pinned:
            continue
        dist = haversine(lat, lon, ap["lat"], ap["lon"])
        if dist <= radius_km:
            nearby.append((sc, dist, iata, ap))

    # Sort by composite: score * 10 - distance.
    # large_airport (15) vs medium (5) = 100km equivalent advantage: big airports still lead,
    # but not over a much closer one ("Costa Brava" gives Girona at 27km before Toulouse at 250km).
    # A typed IATA code always comes first, so "GRO" gives Girona rather than nearby Barcelona.
    nearby.sort(key=lambda x: (x[2] != pinned, -(x[0] * 10 - x[1])))
    nearby = nearby[:max_count]

    if not nearby:
        return None

    result = {}
    for sc, dist, iata, ap in nearby:
        km = round(dist)
        city = ap.get("city") or ap.get("name", iata)
        result[iata] = f"{city} ({km}km)" if km > 0 else city

    return result, label


# ──────────────────────────────────────────────
# FLIGHT FETCHING
# ──────────────────────────────────────────────


def _detect_impersonate() -> str:
    for imp in ("chrome_145", "chrome_133", "chrome_131", "chrome_130"):
        try:
            Client(impersonate=imp, verify=False)
            return imp
        except Exception:
            continue
    return "chrome_131"


IMPERSONATE = _detect_impersonate()


def make_client() -> Client:
    return Client(impersonate=IMPERSONATE, verify=False)


def parse_response(r) -> Result:
    """Parse Google Flights HTML, handling both full and simplified page layouts."""
    parser = LexborHTMLParser(r.text)
    flights = []

    for i, fl in enumerate(parser.css('div[jsname="IWWDBc"], div[jsname="YdtKid"]')):
        is_best = i == 0
        items = fl.css("ul.Rk10dc li")
        if not is_best and len(items) > 1:
            items = items[:-1]

        for item in items:
            # Price (same selector in both layouts)
            price_node = item.css_first(".YMlIz.FpEdX")
            price = (price_node.text(strip=True) if price_node else "0").replace(",", "")

            # Try FULL layout first, then SIMPLIFIED layout
            name = _text(item.css_first("div.sSHqwe.tPgKwe.ogfYpf span"))
            if not name:
                name = _text(item.css_first(".zD7ybd"))

            # Departure / arrival
            departure, arrival = "", ""
            dp_nodes = item.css("span.mv1WYe div")
            if len(dp_nodes) >= 2:
                departure = " ".join(dp_nodes[0].text(strip=True).split())
                arrival = " ".join(dp_nodes[1].text(strip=True).split())
            else:
                dep_node = item.css_first(".XeyHJ")
                arr_node = item.css_first(".h7Rse")
                if dep_node:
                    departure = dep_node.attributes.get("aria-label", "") or dep_node.text(strip=True)
                    departure = departure.replace("Departure time: ", "").rstrip(".")
                if arr_node:
                    arrival = arr_node.attributes.get("aria-label", "") or arr_node.text(strip=True)
                    arrival = arrival.replace("Arrival time: ", "").rstrip(".")

            # Duration
            duration = _text(item.css_first("li div.Ak5kof div"))
            if not duration:
                duration = _text(item.css_first(".Ak5kof div"))

            # Stops
            stops_text = _text(item.css_first(".BbR8Ec .ogfYpf"))

            # Simplified layout: stops + duration in .ix02Db spans
            if not stops_text or not duration:
                detail_spans = item.css(".ix02Db .ogfYpf")
                if len(detail_spans) >= 2:
                    stops_text = stops_text or detail_spans[0].text(strip=True)
                    duration = duration or detail_spans[1].text(strip=True)
                elif len(detail_spans) == 1:
                    stops_text = stops_text or detail_spans[0].text(strip=True)

            # Fallback: parse aria-label on .JMc5Xc
            if not name or not departure:
                aria = item.css_first(".JMc5Xc")
                if aria:
                    al = aria.attributes.get("aria-label", "")
                    if not name:
                        m = re.search(r"flight with (.+?)\.", al)
                        if m:
                            name = m.group(1)
                    if not departure:
                        m = re.search(r"at (\d+:\d+\s*[APap][Mm])\s+on", al)
                        if m:
                            departure = m.group(1)
                    if not duration:
                        m = re.search(r"Total duration (.+?)\.", al)
                        if m:
                            duration = m.group(1)

            time_ahead = _text(item.css_first("span.bOzv6"))
            delay = _text(item.css_first(".GsCCve")) or None

            try:
                stops_fmt = 0 if stops_text == "Nonstop" else int(stops_text.split(" ", 1)[0])
            except (ValueError, AttributeError):
                stops_fmt = "Unknown"

            flights.append(Flight(
                is_best=is_best,
                name=name,
                departure=" ".join(departure.split()),
                arrival=" ".join(arrival.split()),
                arrival_time_ahead=time_ahead,
                duration=duration,
                stops=stops_fmt,
                delay=delay,
                price=price,
            ))

    current_price = _text(parser.css_first("span.gOatQ"))
    if not flights:
        raise RuntimeError("No flights found")
    return Result(current_price=current_price, flights=flights)


def _text(node) -> str:
    return node.text(strip=True) if node else ""


# One attempt by default: a page without flights stays empty on a retry, so retrying only adds delay.
def fetch_flights(filter_obj, currency: str = "", max_retries: int = 1, client: Client | None = None):
    params = {
        "tfs": filter_obj.as_b64().decode("utf-8"),
        "hl": "en",
        "tfu": "EgQIABABIgA",
        "curr": currency,
    }
    if client is None:
        client = make_client()
    last_error = None
    for attempt in range(1, max_retries + 1):
        res = client.get(
            "https://www.google.com/travel/flights",
            params=params,
            cookies=CONSENT_COOKIES,
        )
        assert res.status_code == 200, f"HTTP {res.status_code}"
        try:
            return parse_response(res)
        except RuntimeError as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(REQUEST_DELAY + 1)
    raise last_error


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────


def parse_price(price_str: str | None) -> float | None:
    if not price_str:
        return None
    cleaned = price_str.replace("\xa0", "").replace(",", "")
    numbers = re.findall(r"\d+", cleaned)
    if numbers:
        try:
            val = float(numbers[0])
            return val if val > 0 else None
        except ValueError:
            return None
    return None


def _stops_within(stops_raw, max_stops: int) -> bool:
    s = str(stops_raw).strip().lower()
    if s in ("0", "nonstop"):
        return max_stops >= 0
    nums = re.findall(r"\d+", s)
    if nums:
        return int(nums[0]) <= max_stops
    return True


def format_day(date_str: str) -> str:
    days_nl = ["ma", "di", "wo", "do", "vr", "za", "zo"]
    months_nl = [
        "jan",
        "feb",
        "mrt",
        "apr",
        "mei",
        "jun",
        "jul",
        "aug",
        "sep",
        "okt",
        "nov",
        "dec",
    ]
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{days_nl[dt.weekday()]} {dt.day} {months_nl[dt.month - 1]}"


def build_google_flights_url(filter_obj) -> str:
    b64 = filter_obj.as_b64().decode("utf-8")
    return f"https://www.google.com/travel/flights?tfs={b64}&hl=nl"


def search_route(
    origin: str,
    dest_out: str,
    depart: str,
    return_date: str | None,
    passengers: Passengers,
    seat: str,
    dest_return: str | None = None,
    client: Client | None = None,
    max_stops: int | None = None,
) -> dict | None:
    if dest_return is None:
        dest_return = dest_out
    try:
        flight_data = [
            FlightData(date=depart, from_airport=origin, to_airport=dest_out)
        ]
        trip = "one-way"

        if return_date:
            flight_data.append(
                FlightData(
                    date=return_date, from_airport=dest_return, to_airport=origin
                )
            )
            trip = "round-trip"

        filt = create_filter(
            flight_data=flight_data,
            trip=trip,
            seat=seat,  # type: ignore[arg-type]
            passengers=passengers,
            max_stops=max_stops,
        )

        url = build_google_flights_url(filt)
        result = fetch_flights(filt, client=client)

        flights = []
        for f in getattr(result, "flights", []):
            stops_raw = getattr(f, "stops", "?")
            if max_stops is not None and not _stops_within(stops_raw, max_stops):
                continue
            price = parse_price(getattr(f, "price", None))
            flights.append(
                {
                    "origin": origin,
                    "dest_out": dest_out,
                    "dest_return": dest_return,
                    "price": price,
                    "price_raw": getattr(f, "price", "?"),
                    "name": getattr(f, "name", "?"),
                    "departure": getattr(f, "departure", "?"),
                    "arrival": getattr(f, "arrival", "?"),
                    "duration": getattr(f, "duration", "?"),
                    "stops": stops_raw,
                    "is_best": getattr(f, "is_best", False),
                    "url": url,
                    "depart_date": depart,
                    "return_date": return_date,
                }
            )
        return {
            "flights": flights,
            "current_price": getattr(result, "current_price", None),
        }
    except RuntimeError:
        return {"flights": [], "error": "no flights"}
    except Exception as e:
        return {"flights": [], "error": str(e)[:80]}


# ──────────────────────────────────────────────
# INTERACTIEVE PROMPTS
# ──────────────────────────────────────────────


def ask_destination(radius_km: int, max_airports: int) -> tuple[str, dict[str, str]]:
    console.print()
    console.print(
        "[dim]Typ een stadsnaam (bijv. bratislava, brugge, barcelona) of IATA code (BTS)[/]"
    )

    while True:
        console.print()
        query = console.input("[bold cyan]Waar wil je naartoe?[/] > ").strip()
        if not query:
            continue

        console.print(f"  [dim]Zoeken naar airports binnen {radius_km}km...[/]")
        found = find_nearby_airports(
            query, radius_km=radius_km, max_count=max_airports
        )

        if found:
            airports, label = found
            console.print(f"  Airports gevonden:")
            for code, name in airports.items():
                console.print(f"    [bold]{code}[/]  {name}")
            return query, airports

        console.print(
            f"  [red]Geen airports gevonden voor '{query}'.[/] Probeer een andere naam of IATA code."
        )


def ask_dates() -> tuple[str, str | None]:
    console.print()
    while True:
        depart = console.input("[bold cyan]Vertrekdatum[/] (YYYY-MM-DD) > ").strip()
        try:
            datetime.strptime(depart, "%Y-%m-%d")
            break
        except ValueError:
            console.print("  [red]Ongeldig formaat.[/] Gebruik YYYY-MM-DD", style="dim")

    while True:
        ret = console.input(
            "[bold cyan]Retourdatum[/]  (YYYY-MM-DD, leeg voor enkel) > "
        ).strip()
        if not ret:
            return depart, None
        try:
            datetime.strptime(ret, "%Y-%m-%d")
            return depart, ret
        except ValueError:
            console.print("  [red]Ongeldig formaat.[/] Gebruik YYYY-MM-DD", style="dim")


def ask_passengers() -> Passengers:
    console.print()
    adults_str = console.input(
        "[bold cyan]Aantal volwassenen[/] (standaard 1) > "
    ).strip()
    adults = int(adults_str) if adults_str.isdigit() and int(adults_str) > 0 else 1
    return Passengers(adults=adults, children=0, infants_in_seat=0, infants_on_lap=0)


def ask_origins(home: str, radius_km: int, max_airports: int) -> dict[str, str]:
    console.print()
    console.print(
        f"[dim]Vertrekairports automatisch bepaald vanuit [bold]{home}[/] ({radius_km}km radius):[/]"
    )

    found = find_nearby_airports(home, radius_km=radius_km, max_count=max_airports)
    if not found:
        console.print(f"  [red]Geen airports gevonden rond '{home}'.[/]")
        origins = {home: home}
    else:
        origins, _ = found

    for code, name in origins.items():
        console.print(f"    [bold]{code}[/]  {name}")

    console.print()
    custom = console.input(
        "[bold cyan]Enter[/] = deze gebruiken, of typ codes (bijv. AMS,EIN) > "
    ).strip()
    if not custom:
        return origins

    selected = {}
    for code in custom.upper().replace(" ", "").split(","):
        code = code.strip()
        if re.match(r"^[A-Z]{3}$", code):
            if code in origins:
                selected[code] = origins[code]
            elif code in AIRPORT_DB:
                ap = AIRPORT_DB[code]
                selected[code] = ap.get("city") or ap.get("name", code)
            else:
                selected[code] = code
    return selected if selected else origins


# ──────────────────────────────────────────────
# SEARCH + DISPLAY
# ──────────────────────────────────────────────


def _flex_dates(base: str, flex: int, earliest: str) -> list[str]:
    start = datetime.strptime(base, "%Y-%m-%d")
    days = ((start + timedelta(days=o)).strftime("%Y-%m-%d") for o in range(-flex, flex + 1))
    return [d for d in days if d >= earliest]


def generate_date_shifts(
    depart: str, return_date: str | None, flex_depart: int, flex_return: int | None = None
) -> list[tuple[str, str | None]]:
    # Every departure date pairs with every return date on or after it.
    if flex_return is None:
        flex_return = flex_depart
    if flex_depart <= 0 and (flex_return <= 0 or not return_date):
        return [(depart, return_date)]
    departs = _flex_dates(depart, flex_depart, datetime.now().strftime("%Y-%m-%d"))
    if not return_date:
        return [(d, None) for d in departs]
    return [(d, r) for d in departs for r in _flex_dates(return_date, flex_return, d)]


def run_search(
    origins: dict,
    destinations: dict,
    depart: str,
    return_date: str | None,
    passengers: Passengers,
    seat: str = "economy",
    combi: bool = False,
    flex_days: int = 0,
    flex_return: int | None = None,
):
    if combi and return_date:
        return _run_combi_search(origins, destinations, depart, return_date, passengers, seat, flex_days, flex_return)

    date_shifts = generate_date_shifts(depart, return_date, flex_days, flex_return)
    route_combos = [(o, d) for o in origins for d in destinations]
    combos = [(o, d, dep, ret) for o, d in route_combos for dep, ret in date_shifts]
    total = len(combos)

    console.print()
    trip_label = format_day(depart)
    if return_date:
        trip_label += f" - {format_day(return_date)}"
    flex_label = f"  |  {len(date_shifts)} datumcombinaties" if len(date_shifts) > 1 else ""
    console.print(
        Panel(
            f"[bold]{total}[/] zoekopdrachten ({len(route_combos)} routes × {len(date_shifts)} datum{'s' if len(date_shifts) > 1 else ''})\n"
            f"Periode: [bold]{trip_label}[/]{flex_label}  |  {'Retour' if return_date else 'Enkel'}  |  {passengers._data[0]} volwassene(n)",
            title="Zoeken",
            border_style="cyan",
        )
    )

    all_flights = []
    hits, misses = 0, 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Routes doorzoeken...", total=total)

        for i, (origin, dest, dep, ret) in enumerate(combos):
            date_lbl = f" ({format_day(dep)}{f' / {format_day(ret)}' if ret else ''})" if len(date_shifts) > 1 else ""
            progress.update(task, description=f"[cyan]{origin}[/] -> [cyan]{dest}[/]{date_lbl}")

            result = search_route(origin, dest, dep, ret, passengers, seat)
            if result and result["flights"]:
                all_flights.extend(result["flights"])
                hits += 1
            else:
                misses += 1

            progress.advance(task)
            if i < total - 1:
                time.sleep(REQUEST_DELAY)

    if misses:
        console.print(
            f"  [dim]{hits} routes met resultaten, {misses} zonder (klein vliegveld of geen verbinding)[/]"
        )

    return {"mode": "standard", "flights": all_flights}


def _run_combi_search(origins, destinations, depart, return_date, passengers, seat, flex_days=0, flex_return=None):
    origs = list(origins.keys())
    dests = list(destinations.keys())
    date_shifts = generate_date_shifts(depart, return_date, flex_days, flex_return)

    outbound_pairs = [(o, d) for o in origs for d in dests]
    return_pairs = [(d, o) for d in dests for o in origs]

    all_searches = []
    seen = set()
    for dep, ret in date_shifts:
        for frm, to in outbound_pairs:
            key = (frm, to, dep)
            if key not in seen:
                seen.add(key)
                all_searches.append(("out", frm, to, dep))
        for frm, to in return_pairs:
            key = (frm, to, ret)
            if key not in seen:
                seen.add(key)
                all_searches.append(("ret", frm, to, ret))

    total = len(all_searches)
    n_out = sum(1 for d, *_ in all_searches if d == "out")
    n_ret = total - n_out

    console.print()
    trip_label = f"{format_day(depart)} - {format_day(return_date)}"
    console.print(
        Panel(
            f"[bold magenta]Combi (2x enkel)[/]  |  [bold]{total}[/] zoekopdrachten "
            f"({n_out} heen + {n_ret} terug)\n"
            f"Periode: [bold]{trip_label}[/]  |  {passengers._data[0]} volwassene(n)",
            title="Zoeken",
            border_style="cyan",
        )
    )

    outbound_best: dict[tuple, dict] = {}
    return_best: dict[tuple, dict] = {}
    hits, misses = 0, 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Routes doorzoeken...", total=total)

        for i, (direction, frm, to, date) in enumerate(all_searches):
            phase = "Heen" if direction == "out" else "Terug"
            progress.update(task, description=f"{phase}: [cyan]{frm}[/] -> [cyan]{to}[/]")

            result = search_route(frm, to, date, None, passengers, seat)

            if result and result["flights"]:
                priced = [f for f in result["flights"] if f.get("price") is not None]
                if priced:
                    best = min(priced, key=lambda f: f["price"])
                    (outbound_best if direction == "out" else return_best)[(frm, to, date)] = best
                    hits += 1
                else:
                    misses += 1
            else:
                misses += 1

            progress.advance(task)
            if i < total - 1:
                time.sleep(REQUEST_DELAY)

    if misses:
        console.print(
            f"  [dim]{hits} routes met resultaten, {misses} zonder (klein vliegveld of geen verbinding)[/]"
        )

    combos = build_combos(outbound_best, return_best, origs, dests, date_shifts)
    return {"mode": "combi", "combos": combos}


def build_combos(
    outbound_best: dict[tuple, dict],
    return_best: dict[tuple, dict],
    origins: list[str],
    dests: list[str],
    date_shifts: list[tuple[str, str | None]],
    return_from: list[str] | None = None,
    return_to: list[str] | None = None,
) -> list[dict]:
    # Pair legs only within the planned date pairs, so a return never departs before the outbound.
    # Without return_to, the return flight lands where the outbound flight departed.
    combos = []
    for dep, ret_date in date_shifts:
        for o in origins:
            for d_out in dests:
                ob = outbound_best.get((o, d_out, dep))
                if not ob:
                    continue
                for d_ret in return_from or dests:
                    for home in return_to or [o]:
                        ret = return_best.get((d_ret, home, ret_date))
                        if ret:
                            combos.append({
                                "origin": o,
                                "dest_out": d_out,
                                "dest_return": d_ret,
                                "return_to": home,
                                "total_price": ob["price"] + ret["price"],
                                "outbound": ob,
                                "return": ret,
                            })
    combos.sort(key=lambda c: c["total_price"])
    return combos


def deduplicate(flights: list) -> list:
    seen = set()
    unique = []
    for f in flights:
        key = (
            f["origin"],
            f["dest_out"],
            f["dest_return"],
            f["name"],
            f["departure"],
            f.get("return_date"),
            f["price"],
        )
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def display_results(
    search_result: dict, destinations: dict, depart: str, return_date: str | None
):
    console.print()
    mode = search_result.get("mode", "standard")

    if mode == "combi":
        _display_combi(search_result, destinations, depart, return_date)
    else:
        _display_standard(search_result, destinations, depart, return_date)


def _display_standard(
    search_result: dict, destinations: dict, depart: str, return_date: str | None
):
    flights = deduplicate(search_result.get("flights", []))
    priced = [f for f in flights if f["price"] is not None]
    priced.sort(key=lambda f: f["price"])

    if not priced:
        console.print("[bold red]Geen vluchten gevonden.[/] Probeer andere data of bestemmingen.")
        return

    trip_label = format_day(depart)
    if return_date:
        trip_label += f" -> {format_day(return_date)}"

    table = Table(
        title=f"Goedkoopste vluchten ({trip_label})",
        box=box.ROUNDED, show_lines=False,
        title_style="bold green", header_style="bold", border_style="dim", padding=(0, 1),
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Van", style="cyan", min_width=3)
    table.add_column("Naar", style="cyan", min_width=3)
    table.add_column("Prijs", style="bold green", min_width=6, justify="right")
    table.add_column("Airline", min_width=12, no_wrap=True)
    table.add_column("Vertrek", min_width=10, no_wrap=True)
    table.add_column("Duur", min_width=8, no_wrap=True)
    table.add_column("Stops", min_width=6, justify="center")

    for i, f in enumerate(priced[:15], 1):
        stops_str = _format_stops(f["stops"])
        row_style = "bold on grey11" if i == 1 else ("bold" if i <= 3 else "")
        table.add_row(
            str(i), f["origin"], f["dest_out"], f["price_raw"],
            str(f["name"])[:20], str(f["departure"])[:22],
            str(f["duration"])[:12], stops_str, style=row_style,
        )

    console.print(table)
    console.print(f"\n  [dim]{len(priced)} unieke vluchten gevonden[/]")

    _print_links(priced[:3])
    _print_winner_standard(priced[0])


def _display_combi(
    search_result: dict, destinations: dict, depart: str, return_date: str | None
):
    combos = search_result.get("combos", [])

    if not combos:
        console.print("[bold red]Geen combinaties gevonden.[/] Probeer andere data of bestemmingen.")
        return

    trip_label = f"{format_day(depart)} -> {format_day(return_date)}"

    table = Table(
        title=f"Goedkoopste combi's ({trip_label})",
        box=box.ROUNDED, show_lines=False,
        title_style="bold green", header_style="bold", border_style="dim", padding=(0, 1),
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Van", style="cyan", min_width=3)
    table.add_column("Heen", style="cyan", min_width=3)
    table.add_column("Terug via", style="magenta", min_width=3)
    table.add_column("Heen €", style="green", min_width=6, justify="right")
    table.add_column("Terug €", style="green", min_width=6, justify="right")
    table.add_column("Totaal", style="bold green", min_width=6, justify="right")
    table.add_column("Heen airline", min_width=10, no_wrap=True)
    table.add_column("Terug airline", min_width=10, no_wrap=True)

    for i, c in enumerate(combos[:15], 1):
        ob = c["outbound"]
        ret = c["return"]
        row_style = "bold on grey11" if i == 1 else ("bold" if i <= 3 else "")
        total_str = f"€{c['total_price']:.0f}"

        table.add_row(
            str(i), c["origin"], c["dest_out"], c["dest_return"],
            ob["price_raw"], ret["price_raw"], total_str,
            str(ob["name"])[:16], str(ret["name"])[:16],
            style=row_style,
        )

    console.print(table)
    console.print(f"\n  [dim]{len(combos)} mogelijke combinaties[/]")

    if combos:
        console.print()
        console.print("[bold]Google Flights links (goedkoopste combo):[/]")
        best = combos[0]
        console.print(f"  Heen: {best['origin']} -> {best['dest_out']}")
        console.print(f"  [dim]{best['outbound']['url']}[/]")
        console.print(f"  Terug: {best['dest_return']} -> {best['origin']}")
        console.print(f"  [dim]{best['return']['url']}[/]")

    _print_winner_combi(combos[0])


def _format_stops(stops) -> str:
    s = str(stops) if stops not in (None, "?", "Unknown") else "?"
    if s == "0" or "nonstop" in s.lower():
        return "[green]Direct[/]"
    return s


def _print_links(flights: list):
    if not flights:
        return
    console.print()
    console.print("[bold]Google Flights links (top routes):[/]")
    seen = set()
    for f in flights:
        if f["url"] not in seen:
            seen.add(f["url"])
            console.print(f"  {f['origin']} -> {f['dest_out']}")
            console.print(f"  [dim]{f['url']}[/]")


def _print_winner_standard(cheapest: dict):
    stops = "Direct" if str(cheapest["stops"]) in ("0", "Nonstop", "nonstop") else f"{cheapest['stops']} stop(s)"
    route = f"{cheapest['origin']} -> {cheapest['dest_out']}"
    console.print()
    console.print(Panel(
        f"[bold green]Goedkoopst:[/] {route} voor [bold]{cheapest['price_raw']}[/] met {cheapest['name']}\n"
        f"[dim]{cheapest['departure']} | {cheapest['duration']} | {stops}[/]",
        border_style="green", title="Winnaar",
    ))


def _print_winner_combi(best: dict):
    ob, ret = best["outbound"], best["return"]
    console.print()
    console.print(Panel(
        f"[bold green]Goedkoopst:[/] [bold]€{best['total_price']:.0f}[/] totaal\n"
        f"  Heen:  {best['origin']} -> {best['dest_out']}  [bold]{ob['price_raw']}[/]  {ob['name']}  {str(ob['departure'])[:22]}\n"
        f"  Terug: {best['dest_return']} -> {best['origin']}  [bold]{ret['price_raw']}[/]  {ret['name']}  {str(ret['departure'])[:22]}",
        border_style="green", title="Winnaar",
    ))


# ──────────────────────────────────────────────
# CLI + MAIN
# ──────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Flight Finder - Vind goedkope vluchten via nabijgelegen airports"
    )
    parser.add_argument("--to", help="Bestemming (stadsnaam of IATA code)")
    parser.add_argument("--depart", help="Vertrekdatum (YYYY-MM-DD)")
    parser.add_argument("--return", dest="return_date", help="Retourdatum (YYYY-MM-DD)")
    parser.add_argument(
        "--origins", help="Vertrekairports, komma-gescheiden (bijv. AMS,EIN)"
    )
    parser.add_argument(
        "--home",
        default=DEFAULT_HOME,
        help=f"Thuisairport voor origin-berekening (default: {DEFAULT_HOME})",
    )
    parser.add_argument(
        "--radius",
        type=int,
        default=DEFAULT_RADIUS_DEST,
        help=f"Zoekradius bestemming in km (default: {DEFAULT_RADIUS_DEST})",
    )
    parser.add_argument(
        "--radius-origin",
        type=int,
        default=DEFAULT_RADIUS_ORIGIN,
        help=f"Zoekradius vertrek in km (default: {DEFAULT_RADIUS_ORIGIN})",
    )
    parser.add_argument(
        "--max-dest",
        type=int,
        default=DEFAULT_MAX_DEST,
        help=f"Max bestemming-airports (default: {DEFAULT_MAX_DEST})",
    )
    parser.add_argument(
        "--max-origin",
        type=int,
        default=DEFAULT_MAX_ORIGIN,
        help=f"Max vertrek-airports (default: {DEFAULT_MAX_ORIGIN})",
    )
    parser.add_argument(
        "--combi",
        action="store_true",
        help="Combi: zoek 2 losse enkele reizen (heen + terug via ander airport)",
    )
    parser.add_argument("--adults", type=int, default=1, help="Aantal volwassenen")
    parser.add_argument(
        "--seat",
        default="economy",
        choices=["economy", "premium-economy", "business", "first"],
    )
    parser.add_argument(
        "--flex", type=int, default=0, choices=[0, 1, 2, 3],
        help="Flexibele vertrekdatum: ±N dagen",
    )
    parser.add_argument(
        "--flex-terug", type=int, default=None, choices=[0, 1, 2, 3],
        help="Flexibele terugdatum: ±N dagen (standaard gelijk aan --flex)",
    )
    parser.add_argument(
        "--delay", type=float, default=None, help="Delay tussen requests in seconden"
    )
    args = parser.parse_args()

    if args.delay is not None:
        global REQUEST_DELAY
        REQUEST_DELAY = args.delay

    console.print(
        Panel(
            "[bold]Flight Finder[/]\n"
            "Zoek de goedkoopste vluchten door [cyan]nabijgelegen airports[/] automatisch te vergelijken\n"
            f"[dim]{len(AIRPORT_DB):,} airports in database | Haversine radius discovery[/]",
            border_style="blue",
        )
    )

    interactive = not any([args.to, args.depart])

    # Destination
    if args.to:
        found = find_nearby_airports(
            args.to, radius_km=args.radius, max_count=args.max_dest
        )
        if not found:
            console.print(f"[red]Geen airports gevonden voor '{args.to}'.[/]")
            sys.exit(1)
        dest_airports, _ = found
        console.print(f"Bestemming airports ({args.radius}km radius, max {args.max_dest}):")
        for code, name in dest_airports.items():
            console.print(f"  [bold]{code}[/]  {name}")
    else:
        _, dest_airports = ask_destination(
            radius_km=args.radius, max_airports=args.max_dest
        )

    # Dates
    if args.depart:
        depart = args.depart
        return_date = args.return_date
    else:
        depart, return_date = ask_dates()

    # Passengers
    passengers = Passengers(
        adults=args.adults, children=0, infants_in_seat=0, infants_on_lap=0
    )
    if interactive:
        passengers = ask_passengers()

    # Origins
    if args.origins:
        codes = [c.strip().upper() for c in args.origins.split(",")]
        origins = {}
        for c in codes:
            if c in AIRPORT_DB:
                ap = AIRPORT_DB[c]
                origins[c] = ap.get("city") or ap.get("name", c)
            else:
                origins[c] = c
    elif interactive:
        origins = ask_origins(
            home=args.home, radius_km=args.radius_origin, max_airports=args.max_origin
        )
    else:
        found = find_nearby_airports(
            args.home, radius_km=args.radius_origin, max_count=args.max_origin
        )
        if not found:
            origins = {args.home: args.home}
        else:
            origins, _ = found
        console.print(f"\nVertrekairports ({args.radius_origin}km rond {args.home}, max {args.max_origin}):")
        for code, name in origins.items():
            console.print(f"  [bold]{code}[/]  {name}")

    # Search
    search_result = run_search(
        origins,
        dest_airports,
        depart,
        return_date,
        passengers,
        args.seat,
        combi=args.combi,
        flex_days=args.flex,
        flex_return=args.flex_terug,
    )

    # Results
    display_results(search_result, dest_airports, depart, return_date)


if __name__ == "__main__":
    main()
