# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

The owner (home postcode 7991AW, Drenthe) and family and friends. They plan leisure trips and want the lowest fare. Other users must understand the tool without explanation, so the home location must be visible and easy to change, not an unexplained default. Interface language: Dutch.

## Product Purpose

Flight Finder finds the cheapest flight to a destination by searching every reasonable combination at once: all airports near home, all airports near the destination, and optional flexible dates. Success: a user starts a search in seconds, follows a long-running search with confidence, and compares the results quickly enough to pick one and continue to Google Flights to book.

## Positioning

Google Flights searches one origin at a time. Flight Finder sweeps many origin airports (also across the German border) against many destination airports and date shifts in one run, ranks them by price, and can combine two one-way tickets into an open-jaw "combi" trip.

## Operating Context

- A search is not instant: it runs dozens of route queries (about 0.8 s each, ten at a time across all searches) and streams progress over SSE. The exact dates are searched first, then the flexible dates. Partial results arrive during the search; a typical 135-query round trip takes about 8 seconds.
- Route results are cached for ten minutes, so repeating or adjusting a search is near-instant. Closing the progress stream (Stoppen, a new search, a closed tab) cancels the remaining queries.
- Results link out to Google Flights; there is no booking in the app.
- Recent searches are stored in localStorage and restored with one click.

## Capabilities and Constraints

- Backend: FastAPI + one Jinja template (`templates/index.html`) with vanilla JS and inline CSS; no build step. The API (`/airports`, `/origins`, `/search`, `/progress/{id}`, `/results/{id}`) stays unchanged.
- Inputs: destination (city or IATA), number of destination airports, depart date, optional return date, flex ±0–3 days set separately for departure and return (every departure date pairs with every return date on or after it), passengers 1–4, max stops, cabin class, mode (round trip or combi), home location (postcode, city, or IATA), number of origin airports. Each discovered airport can be switched off.
- Flight data comes scraped from Google Flights in English text (for example "10:05 AM on Mon, Jun 16"); fields can be missing or "?".
- Results: up to 50 ranked items; standard mode lists flights, combi mode lists outbound + return pairs with a total price.

## Evidence on Hand

No logo, brand assets, or testimonials exist. Do not invent prices, airlines, or claims beyond what the search returns.

## Product Principles

1. Speed to a search: the common path is destination, dates, go.
2. Price first, then the trade-offs (time, duration, stops, travel to the origin airport).
3. Make the long search feel alive and trustworthy; show the best find as soon as it exists.
4. Understandable for non-owners: no jargon such as "combi" or "hits" without a plain explanation.
