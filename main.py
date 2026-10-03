from __future__ import annotations

import asyncio
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from flight_finder import (
    find_nearby_airports,
    resolve_location,
    search_airports,
    airports_around,
    build_combos,
    search_route,
    deduplicate,
    make_client,
    generate_date_shifts,
    AIRPORT_DB,
    DEFAULT_RADIUS_DEST,
    DEFAULT_RADIUS_ORIGIN,
    DEFAULT_MAX_DEST,
    DEFAULT_MAX_ORIGIN,
)
from fast_flights import Passengers

# Google requests across all searches together; 10 is about 2.5x faster than 4 without errors.
CONCURRENCY = 10
ROUTE_TTL = 600

tasks: dict[str, dict] = {}
TASK_TTL = 600

_pool = ThreadPoolExecutor(max_workers=CONCURRENCY)
_client = make_client()
_google: Optional[asyncio.Semaphore] = None
_routes: dict[tuple, tuple[float, asyncio.Future]] = {}


async def _cleanup_stale_tasks():
    while True:
        await asyncio.sleep(60)
        now = time.time()
        stale = [tid for tid, t in tasks.items() if now - t["created"] > TASK_TTL]
        for tid in stale:
            tasks.pop(tid, None)
        for key in [k for k, (at, fut) in _routes.items() if fut.done() and now - at > ROUTE_TTL]:
            _routes.pop(key, None)


def _fresh_route(key: tuple) -> Optional[asyncio.Future]:
    hit = _routes.get(key)
    return hit[1] if hit and time.time() - hit[0] < ROUTE_TTL else None


def _search_key(key: tuple) -> dict:
    frm, to, dep, ret, adults, seat, max_stops = key
    passengers = Passengers(adults=adults, children=0, infants_in_seat=0, infants_on_lap=0)
    return search_route(frm, to, dep, ret, passengers, seat, None, _client, max_stops)


async def _route(frm: str, to: str, dep: str, ret: Optional[str], adults: int, seat: str, max_stops: Optional[int]) -> dict:
    # Results are shared for ten minutes, so a repeated or overlapping search reuses them at once.
    # A cancelled search stops waiting for a slot, but a request that already runs completes and fills the cache.
    key = (frm, to, dep, ret, adults, seat, max_stops)
    fut = _fresh_route(key)
    if fut is None:
        async with _google:
            fut = _fresh_route(key)
            if fut is None:
                fut = asyncio.get_event_loop().run_in_executor(_pool, _search_key, key)
                _routes[key] = (time.time(), fut)
                await asyncio.wait({fut})
    result = await asyncio.shield(fut)
    if result.get("error") not in (None, "no flights") and _routes.get(key, (0, None))[1] is fut:
        _routes.pop(key, None)
    return result


@asynccontextmanager
async def _lifespan(app: FastAPI):
    global _google
    _google = asyncio.Semaphore(CONCURRENCY)
    asyncio.create_task(_cleanup_stale_tasks())
    # Load the airport data at startup instead of on the first visitor's request.
    asyncio.get_event_loop().run_in_executor(None, find_nearby_airports, "AMS", DEFAULT_RADIUS_ORIGIN, DEFAULT_MAX_ORIGIN)
    yield


app = FastAPI(title="Flight Finder", lifespan=_lifespan)
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# ── Pages ────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Link previews need an absolute image URL; behind nginx the scheme comes from X-Forwarded-Proto.
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    base_url = f"{scheme}://{request.headers.get('host', request.url.netloc)}"
    return templates.TemplateResponse("index.html", {"request": request, "base_url": base_url})


# ── API: Airport Discovery ───────────────────────────────

@app.get("/airports")
async def airports(q: str, radius: int = DEFAULT_RADIUS_DEST, max_dest: int = DEFAULT_MAX_DEST):
    if not q or len(q.strip()) < 2:
        return JSONResponse({"airports": {}, "label": ""})

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, find_nearby_airports, q.strip(), radius, max_dest)

    if not result:
        return JSONResponse({"airports": {}, "label": "", "error": f"Geen airports gevonden voor '{q}'"})

    airport_dict, label = result
    return JSONResponse({"airports": airport_dict, "label": label})


@app.get("/origins")
async def origins(home: str = "7991AW", radius: int = DEFAULT_RADIUS_ORIGIN, max_origin: int = DEFAULT_MAX_ORIGIN):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, find_nearby_airports, home, radius, max_origin)
    if not result:
        return JSONResponse({"airports": {home: home}, "home": home})
    airport_dict, label = result
    return JSONResponse({"airports": airport_dict, "home": home, "label": label.removesuffix(" (via geocoding)")})


async def _locate(query: str) -> tuple[float, float] | None:
    if not query.strip():
        return None
    location = await asyncio.get_event_loop().run_in_executor(None, resolve_location, query)
    return location[:2] if location else None


@app.get("/airport-search")
async def airport_search(q: str, ref: str = ""):
    loop = asyncio.get_event_loop()
    near = await _locate(ref)
    results = await loop.run_in_executor(None, search_airports, q, near)
    if not results and len(q.strip()) >= 3:
        place = await _locate(q)
        if place:
            results = await loop.run_in_executor(None, airports_around, place, near)
            # The query is a place without its own airport, such as "Brugge" or "Costa Brava".
            return JSONResponse({"airports": results, "place": q.strip()})
    return JSONResponse({"airports": results})


# ── API: Return flights ──────────────────────────────────
# Google lists only outbound flights for a round trip; the return flight is chosen later.
# This shows which return flights fly that day, as one-way results without their prices.

@app.get("/return-flights")
async def return_flights(frm: str, to: str, date: str, adults: int = 1, seat: str = "economy", max_stops: Optional[int] = None):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return JSONResponse({"error": "Ongeldig datumformaat (YYYY-MM-DD)"}, status_code=400)
    result = await _route(frm.strip().upper(), to.strip().upper(), date, None, adults, seat, max_stops)
    flights = {
        (f["name"], f["departure"]): {k: f.get(k) for k in ("name", "departure", "arrival", "duration", "stops")}
        for f in result["flights"]
    }
    return JSONResponse({"flights": list(flights.values())})


# ── API: Search ──────────────────────────────────────────

@app.post("/search")
async def start_search(request: Request):
    body = await request.json()

    destination = (body.get("destination") or "").strip()
    depart = (body.get("depart") or "").strip()
    return_date = (body.get("return_date") or "").strip() or None
    combi = body.get("combi", body.get("open_jaw", False))
    seat = body.get("seat", "economy")
    try:
        adults = int(body.get("adults", 1))
        radius_dest = int(body.get("radius_dest", DEFAULT_RADIUS_DEST))
        radius_origin = int(body.get("radius_origin", DEFAULT_RADIUS_ORIGIN))
        max_dest = int(body.get("max_dest", DEFAULT_MAX_DEST))
        max_origin = int(body.get("max_origin", DEFAULT_MAX_ORIGIN))
        max_stops_raw = body.get("max_stops", None)
        max_stops = int(max_stops_raw) if max_stops_raw is not None else None
        flex_days = int(body.get("flex_days", 0))
        flex_depart = min(int(body.get("flex_depart", flex_days)), 3)
        flex_return = min(int(body.get("flex_return", flex_days)), 3)
    except (TypeError, ValueError):
        return JSONResponse({"error": "Ongeldige waarde: aantallen en flexibele dagen moeten hele getallen zijn"}, status_code=400)
    dest_codes = body.get("dest_codes", None)
    origin_codes = body.get("origins", None)
    return_from = body.get("return_from") or None
    return_to = body.get("return_to") or None
    home = body.get("home", "7991AW")

    if not destination or not depart:
        return JSONResponse({"error": "Bestemming en vertrekdatum zijn verplicht"}, status_code=400)

    try:
        datetime.strptime(depart, "%Y-%m-%d")
        if return_date:
            datetime.strptime(return_date, "%Y-%m-%d")
    except ValueError:
        return JSONResponse({"error": "Ongeldig datumformaat (YYYY-MM-DD)"}, status_code=400)

    task_id = uuid.uuid4().hex[:12]
    tasks[task_id] = {
        "status": "initializing",
        "progress": 0,
        "total": 0,
        "searched": 0,
        "hits": 0,
        "current_route": "",
        "flights": [],
        "results": [],
        "cheapest": None,
        "dest_airports": {},
        "origin_airports": {},
        "error": None,
        "created": time.time(),
        "events": asyncio.Queue(),
    }

    tasks[task_id]["runner"] = asyncio.create_task(_run_search(
        task_id, destination, depart, return_date, combi,
        adults, seat, radius_dest, radius_origin, max_dest, max_origin,
        max_stops, dest_codes, origin_codes, home, flex_depart, flex_return,
        return_from, return_to,
    ))

    return JSONResponse({"task_id": task_id})


def _resolve_codes(codes: list[str]) -> dict[str, str]:
    result = {}
    for c in codes:
        c = c.strip().upper()
        if c in AIRPORT_DB:
            ap = AIRPORT_DB[c]
            result[c] = ap.get("city") or ap.get("name", c)
        else:
            result[c] = c
    return result


async def _run_search(
    task_id: str,
    destination: str,
    depart: str,
    return_date: str | None,
    combi: bool,
    adults: int,
    seat: str,
    radius_dest: int,
    radius_origin: int,
    max_dest: int,
    max_origin: int,
    max_stops: int | None,
    dest_codes: list[str] | None,
    origin_codes: list[str] | None,
    home: str,
    flex_depart: int = 0,
    flex_return: int = 0,
    return_from: list[str] | None = None,
    return_to: list[str] | None = None,
):
    task = tasks[task_id]
    loop = asyncio.get_event_loop()
    eq = task["events"]

    try:
        task["status"] = "discovering"
        await eq.put({"type": "progress", "data": {"status": "discovering", "message": "Airports zoeken...", "progress": 0, "searched": 0, "total": 0, "hits": 0, "current_route": ""}})

        if dest_codes:
            dest_airports = _resolve_codes(dest_codes)
        else:
            found = await loop.run_in_executor(
                None, find_nearby_airports, destination, radius_dest, max_dest
            )
            if not found:
                task["status"] = "error"
                task["error"] = f"Geen airports gevonden voor '{destination}'"
                await eq.put({"type": "error", "data": {"error": task["error"]}})
                return
            dest_airports, _ = found
        task["dest_airports"] = dest_airports

        if origin_codes:
            origin_airports = _resolve_codes(origin_codes)
        else:
            found = await loop.run_in_executor(
                None, find_nearby_airports, home, radius_origin, max_origin
            )
            if not found:
                origin_airports = {home: home}
            else:
                origin_airports, _ = found
        task["origin_airports"] = origin_airports

        dests = list(dest_airports.keys())
        origins_list = list(origin_airports.keys())
        query = (adults, seat, max_stops)
        # The exact dates first, so every route shows a price early; the flexible dates follow.
        date_shifts = sorted(
            generate_date_shifts(depart, return_date, flex_depart, flex_return),
            key=lambda s: _days_apart(s[0], depart) + _days_apart(s[1], return_date),
        )

        if combi and return_date:
            ret_from = [c.strip().upper() for c in return_from] if return_from else None
            ret_to = [c.strip().upper() for c in return_to] if return_to else None
            await _search_combi(task, origins_list, dests, date_shifts, query, ret_from, ret_to)
        else:
            await _search_standard(task, origins_list, dests, date_shifts, query)

    except asyncio.CancelledError:
        task["status"] = "cancelled"
        raise
    except Exception as e:
        task["status"] = "error"
        task["error"] = str(e)[:200]
        await eq.put({"type": "error", "data": {"error": task["error"]}})


def _days_apart(a: Optional[str], b: Optional[str]) -> int:
    if not a or not b:
        return 0
    return abs((datetime.strptime(a, "%Y-%m-%d") - datetime.strptime(b, "%Y-%m-%d")).days)


async def _search_standard(task, origins, dests, date_shifts, query):
    combos = [(o, d, dep, ret) for dep, ret in date_shifts for o in origins for d in dests]
    task["total"] = len(combos)
    task["mode"] = "standard"
    task["status"] = "searching"
    eq = task["events"]

    searched_count = 0
    lock = asyncio.Lock()

    async def search_one(origin, dest, dep, ret):
        nonlocal searched_count
        result = await _route(origin, dest, dep, ret, *query)

        async with lock:
            searched_count += 1
            new_flights = []
            if result and result["flights"]:
                task["flights"].extend(result["flights"])
                task["hits"] += 1
                new_flights = [_serialize_flight(f) for f in result["flights"] if f.get("price") is not None]

            task["searched"] = searched_count
            task["progress"] = searched_count / len(combos)

            interim_cheapest = None
            priced = [f for f in task["flights"] if f.get("price")]
            if priced:
                best = min(priced, key=lambda f: f["price"])
                interim_cheapest = {"price": best["price_raw"], "route": f"{best['origin']} → {best['dest_out']}", "name": best["name"]}

            date_label = f" ({dep}{f' / {ret}' if ret else ''})" if len(date_shifts) > 1 else ""
            await eq.put({"type": "progress", "data": {
                "status": "searching", "mode": "standard",
                "message": f"{origin} → {dest}{date_label}",
                "progress": round(task["progress"], 3),
                "searched": searched_count, "total": len(combos),
                "hits": task["hits"], "current_route": f"{origin} → {dest}{date_label}",
                "flights_found": len(task["flights"]), "cheapest": interim_cheapest,
                "new_flights": new_flights,
            }})

    await asyncio.gather(*(search_one(o, d, dep, ret) for o, d, dep, ret in combos))

    all_flights = deduplicate(task["flights"])
    priced = [f for f in all_flights if f["price"] is not None]
    priced.sort(key=lambda f: f["price"])

    task["results"] = _shown(priced)
    task["cheapest"] = priced[0] if priced else None
    task["total_found"] = len(priced)
    task["status"] = "complete"

    cheapest = task["cheapest"]
    serialized_cheapest = _serialize_flight(cheapest) if cheapest else None
    serialized_results = [_serialize_flight(f) for f in task["results"]]

    await eq.put({"type": "complete", "data": {
        "mode": "standard",
        "total_found": task["total_found"],
        "hits": task["hits"],
        "misses": task["total"] - task["hits"],
        "results": serialized_results,
        "cheapest": serialized_cheapest,
        "dest_airports": task["dest_airports"],
        "origin_airports": task["origin_airports"],
    }})


async def _search_combi(task, origins, dests, date_shifts, query, return_from=None, return_to=None):
    ret_froms = return_from or dests
    ret_homes = return_to or origins
    all_searches = []
    seen = set()
    for dep, ret in date_shifts:
        for o in origins:
            for d in dests:
                key = ("out", o, d, dep)
                if key not in seen:
                    seen.add(key)
                    all_searches.append(("out", o, d, dep))
        for d in ret_froms:
            for h in ret_homes:
                key = ("ret", d, h, ret)
                if key not in seen:
                    seen.add(key)
                    all_searches.append(("ret", d, h, ret))

    task["total"] = len(all_searches)
    task["mode"] = "combi"
    task["status"] = "searching"
    eq = task["events"]

    outbound_best = {}
    return_best = {}
    searched_count = 0
    lock = asyncio.Lock()

    async def search_one(direction, frm, to, date):
        nonlocal searched_count
        result = await _route(frm, to, date, None, *query)

        async with lock:
            searched_count += 1
            if result and result["flights"]:
                priced = [f for f in result["flights"] if f.get("price") is not None]
                if priced:
                    best = min(priced, key=lambda f: f["price"])
                    (outbound_best if direction == "out" else return_best)[(frm, to, date)] = best
                    task["hits"] += 1
                    _update_interim_cheapest(task, outbound_best, return_best, origins, dests, date_shifts, return_from, return_to)

            task["searched"] = searched_count
            task["progress"] = searched_count / len(all_searches)

            phase = "Heen" if direction == "out" else "Terug"
            evt = {
                "status": "searching", "mode": "combi",
                "message": f"{phase}: {frm} → {to}",
                "progress": round(task["progress"], 3),
                "searched": searched_count, "total": len(all_searches),
                "hits": task["hits"], "current_route": f"{phase}: {frm} → {to}",
                "flights_found": 0, "cheapest": task.get("interim_cheapest"),
            }
            ic = task.get("interim_combos")
            if ic:
                evt["new_combos"] = ic
                evt["cell_best"] = task["interim_cells"]
            await eq.put({"type": "progress", "data": evt})

    await asyncio.gather(*(search_one(d, f, t, dt) for d, f, t, dt in all_searches))

    combos = build_combos(outbound_best, return_best, origins, dests, date_shifts, return_from, return_to)
    task["results"] = _shown(combos)
    task["cheapest"] = combos[0] if combos else None
    task["total_found"] = len(combos)
    task["status"] = "complete"

    cheapest = task["cheapest"]
    serialized_cheapest = _serialize_combo(cheapest) if cheapest else None
    serialized_results = [_serialize_combo(c) for c in task["results"]]

    await eq.put({"type": "complete", "data": {
        "mode": "combi",
        "total_found": task["total_found"],
        "hits": task["hits"],
        "misses": task["total"] - task["hits"],
        "results": serialized_results,
        "cheapest": serialized_cheapest,
        "dest_airports": task["dest_airports"],
        "origin_airports": task["origin_airports"],
    }})


def _shown(items: list[dict], top: int = 50, per_route: int = 5) -> list[dict]:
    # The cheapest overall plus the cheapest per route, so every price in the matrix has rows to filter to.
    shown, counts = [], {}
    for i, item in enumerate(items):
        route = (item["origin"], item["dest_out"])
        counts[route] = counts.get(route, 0) + 1
        if i < top or counts[route] <= per_route:
            shown.append(item)
    return shown


def _update_interim_cheapest(task, outbound_best, return_best, origins, dests, date_shifts, return_from=None, return_to=None):
    all_combos = build_combos(outbound_best, return_best, origins, dests, date_shifts, return_from, return_to)
    if not all_combos:
        return
    best = all_combos[0]
    task["interim_cheapest"] = {
        "price": f"\u20AC{best['total_price']:.0f}",
        "route": f"{best['origin']} → {best['dest_out']}, terug {best['dest_return']} → {best['return_to']}",
        "name": f"{best['outbound']['name']} / {best['return']['name']}",
    }
    task["interim_combos"] = [_serialize_combo(c) for c in all_combos[:15]]
    cells = {}
    for c in all_combos:
        cells.setdefault(f"{c['origin']}>{c['dest_out']}", c["total_price"])
    task["interim_cells"] = cells


# ── API: Progress SSE ────────────────────────────────────

@app.get("/progress/{task_id}")
async def progress(task_id: str):
    async def stream():
        task = tasks.get(task_id)
        if not task:
            yield _sse("error", {"error": "Task niet gevonden"})
            return

        eq = task["events"]
        try:
            while True:
                try:
                    event = await asyncio.wait_for(eq.get(), timeout=30)
                except asyncio.TimeoutError:
                    yield _sse("progress", {"status": "waiting", "message": "Wachten...", "progress": task.get("progress", 0), "searched": task.get("searched", 0), "total": task.get("total", 0), "hits": task.get("hits", 0), "current_route": ""})
                    continue

                etype = event["type"]
                yield _sse(etype, event["data"])
                if etype in ("complete", "error"):
                    break
        finally:
            # The browser closed the stream (Stoppen, a new search, or a closed tab): stop searching.
            if task["status"] not in ("complete", "error"):
                task["runner"].cancel()

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _serialize_flight(f: dict) -> dict:
    return {
        "origin": f.get("origin"),
        "dest_out": f.get("dest_out"),
        "dest_return": f.get("dest_return"),
        "price": f.get("price"),
        "price_raw": f.get("price_raw"),
        "name": f.get("name"),
        "departure": f.get("departure"),
        "arrival": f.get("arrival"),
        "duration": f.get("duration"),
        "stops": f.get("stops"),
        "is_best": f.get("is_best"),
        "url": f.get("url"),
        "depart_date": f.get("depart_date"),
        "return_date": f.get("return_date"),
    }


def _serialize_combo(c: dict) -> dict:
    return {
        "origin": c.get("origin"),
        "dest_out": c.get("dest_out"),
        "dest_return": c.get("dest_return"),
        "return_to": c.get("return_to", c.get("origin")),
        "total_price": c.get("total_price"),
        "outbound": _serialize_flight(c["outbound"]) if c.get("outbound") else None,
        "return": _serialize_flight(c["return"]) if c.get("return") else None,
    }


# ── API: Results ─────────────────────────────────────────

@app.get("/results/{task_id}")
async def results(task_id: str):
    task = tasks.get(task_id)
    if not task:
        return JSONResponse({"error": "Task niet gevonden"}, status_code=404)
    if task["status"] != "complete":
        return JSONResponse({"error": "Zoeken nog bezig", "status": task["status"]}, status_code=202)

    mode = task.get("mode", "standard")
    cheapest = task.get("cheapest")

    if mode == "combi":
        serialized_results = [_serialize_combo(c) for c in task["results"]]
        serialized_cheapest = _serialize_combo(cheapest) if cheapest else None
    else:
        serialized_results = [_serialize_flight(f) for f in task["results"]]
        serialized_cheapest = _serialize_flight(cheapest) if cheapest else None

    return JSONResponse({
        "mode": mode,
        "results": serialized_results,
        "cheapest": serialized_cheapest,
        "total_found": task.get("total_found", 0),
        "dest_airports": task["dest_airports"],
        "origin_airports": task["origin_airports"],
    })
