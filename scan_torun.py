#!/usr/bin/env python3
"""Scan multiple date combos × WAW/WMI/GDN × NL/BE/DE origins for Torun trip."""

from __future__ import annotations

import time
from itertools import product

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

from fast_flights import Passengers
from flight_finder import (
    AIRPORT_DB,
    REQUEST_DELAY,
    build_google_flights_url,
    format_day,
    make_client,
    search_route,
)
from fast_flights import FlightData, create_filter

console = Console()

ORIGINS = {
    "GRQ": "Groningen",
    "AMS": "Amsterdam",
    "EIN": "Eindhoven",
    "BRE": "Bremen",
    "NRN": "Weeze",
    "DTM": "Dortmund",
    "DUS": "Dusseldorf",
}

DESTINATIONS = {
    "WAW": "Warsaw Chopin",
    "WMI": "Warsaw Modlin",
    "GDN": "Gdansk",
}

DATE_COMBOS = [
    ("2026-09-24", "2026-09-27"),
    ("2026-09-24", "2026-09-28"),
    ("2026-09-25", "2026-09-27"),
    ("2026-09-25", "2026-09-28"),
]

PASSENGERS = Passengers(adults=1, children=0, infants_in_seat=0, infants_on_lap=0)


def build_url(origin: str, dest: str, dep: str, ret: str) -> str:
    filt = create_filter(
        flight_data=[
            FlightData(date=dep, from_airport=origin, to_airport=dest),
            FlightData(date=ret, from_airport=dest, to_airport=origin),
        ],
        trip="round-trip",
        seat="economy",
        passengers=PASSENGERS,
        max_stops=None,
    )
    return build_google_flights_url(filt)


def main():
    combos = list(product(ORIGINS.keys(), DESTINATIONS.keys(), DATE_COMBOS))
    total = len(combos)

    console.print(
        Panel(
            f"[bold]Torun trip scan[/]\n"
            f"{len(ORIGINS)} origins × {len(DESTINATIONS)} dest × {len(DATE_COMBOS)} date combos = [bold]{total}[/] searches",
            border_style="cyan",
        )
    )

    client = make_client()
    all_results = []
    hits, misses = 0, 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("scanning...", total=total)

        for i, (origin, dest, (dep, ret)) in enumerate(combos):
            progress.update(
                task,
                description=f"[cyan]{origin}[/] -> [cyan]{dest}[/]  {dep[5:]}->{ret[5:]}",
            )

            result = search_route(
                origin, dest, dep, ret, PASSENGERS, "economy", client=client
            )

            if result and result.get("flights"):
                priced = [f for f in result["flights"] if f.get("price") is not None]
                if priced:
                    best = min(priced, key=lambda f: f["price"])
                    best["dep_date"] = dep
                    best["ret_date"] = ret
                    all_results.append(best)
                    hits += 1
                else:
                    misses += 1
            else:
                misses += 1

            progress.advance(task)
            if i < total - 1:
                time.sleep(REQUEST_DELAY)

    console.print(f"  [dim]{hits} routes with results, {misses} empty[/]")

    if not all_results:
        console.print("[red]Geen vluchten gevonden.[/]")
        return

    all_results.sort(key=lambda r: r["price"])

    table = Table(
        title="Top 20 goedkoopste round-trips Torun (WAW/WMI/GDN)",
        box=box.ROUNDED,
        title_style="bold green",
        header_style="bold",
        border_style="dim",
        padding=(0, 1),
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Van", style="cyan")
    table.add_column("Naar", style="cyan")
    table.add_column("Heen", style="white")
    table.add_column("Terug", style="white")
    table.add_column("Prijs", style="bold green", justify="right")
    table.add_column("Airline", no_wrap=True)
    table.add_column("Vertrek heen", no_wrap=True)
    table.add_column("Duur", no_wrap=True)
    table.add_column("Stops", justify="center")

    for i, f in enumerate(all_results[:20], 1):
        stops = (
            "Direct"
            if str(f["stops"]) in ("0", "Nonstop", "nonstop")
            else str(f["stops"])
        )
        row_style = "bold on grey11" if i == 1 else ("bold" if i <= 3 else "")
        table.add_row(
            str(i),
            f["origin"],
            f["dest_out"],
            format_day(f["dep_date"]),
            format_day(f["ret_date"]),
            f["price_raw"],
            str(f["name"])[:18],
            str(f["departure"])[:22],
            str(f["duration"])[:10],
            stops,
            style=row_style,
        )

    console.print()
    console.print(table)

    console.print()
    console.print("[bold]Top 5 Google Flights links (controleer return time > 12:00):[/]")
    for i, f in enumerate(all_results[:5], 1):
        url = build_url(f["origin"], f["dest_out"], f["dep_date"], f["ret_date"])
        console.print(
            f"  [bold]{i}[/]. {f['origin']} -> {f['dest_out']}  "
            f"{format_day(f['dep_date'])} -> {format_day(f['ret_date'])}  "
            f"[green]{f['price_raw']}[/]"
        )
        console.print(f"     [dim]{url}[/]")


if __name__ == "__main__":
    main()
