# AGENTS.md

Flight Finder sweeps many origin airports × destination airports × dates on Google Flights and streams the results over SSE. Users are the owner plus family and friends, all Dutch.

## Context docs

- **Visual change** to `templates/index.html`: read `DESIGN.md` first (tokens, components, the "routeboekje & wegwijzer" direction).
- **Product change** (who uses it, what a search does, the API): read `PRODUCT.md` first.

## Product rules

- All user-facing text is Dutch: UI, API error messages, CLI output. Code, comments and docs are English.
- One theme: dark.
- Keep the HTTP API backward compatible, and keep reading existing localStorage entries (`flight-finder-home`, `flight-finder-history`): family members' browsers hold saved searches.
- The whole UI stays in `templates/index.html`: inline CSS and vanilla JS, no build step.

## Backend gotchas

- Local Python is 3.9 (Docker uses 3.12). FastAPI evaluates route-signature annotations at runtime, so write `Optional[str]` in route signatures; `str | None` works elsewhere through `from __future__ import annotations`.
- Create asyncio primitives inside `_lifespan` or a request handler, where the event loop exists.
- Send every Google Flights query from the server through `_route()` in `main.py`. It owns the shared concurrency limit, the 10-minute route cache and the in-flight dedupe.
- Keep responses uncompressed: compression middleware buffers the SSE stream of `/progress/{id}`.
- `flight_finder.py` is both the library `main.py` imports and a standalone CLI. A change to a shared function must keep both working.

## Running and checking

- Dev server: `python3 -m uvicorn main:app --port 8000`, without `--reload`. Restart it after every Python change.
- The owner often has port 8000 open in a browser. Try Python changes on port 8001 first, then restart 8000.
- The repo has no test suite. Check backend changes with `curl` against the endpoints, and UI changes in a browser at desktop width and at 390px with an error-free console.
- Real searches call Google Flights (~0.8 s per route) and Nominatim. Keep test searches small: one destination airport, no flex.
