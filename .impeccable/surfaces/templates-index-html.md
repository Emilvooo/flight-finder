---
version: 1
slug: "templates-index-html"
primary_target: "templates/index.html"
related_targets: []
---

## Scope

Whole app surface `templates/index.html` (search, live progress, results). Mode: Operate. Full redesign; backend API unchanged.

## Audience and task

Owner and family/friends, Dutch, at home on laptop or phone, planning a trip. Job: start a search in seconds, follow a slow multi-airport sweep with confidence, compare results, continue to Google Flights.

## Constraints

Single Jinja template, inline CSS/JS, no build step. Google Flights strings arrive in English and can be missing. Home location must be visible and editable (default 7991AW), remembered per browser.

## Direction contract

THESIS: Searching is plotting a route. The app refuses the dark-neon single-column wizard and the white-card OTA layout; it is a route booklet: blue road signs for where to and where from, and the road atlas distance table, filled live with prices.

OWN-WORLD: One dark theme only (user decision, no light mode). Near-black cover #090C11 with a yellow #FFD100 wordmark and 4px road-marking stripe, Dutch sign blue #0E4C92 panels with the inset white sign border, dark panels #161C25 with thin rules on a deep ground #0D1117, light ink #ECEFF3; ink #141A24 on every yellow surface. One family, Archivo: condensed heavy for sign lettering, normal width for body, tabular figures everywhere. Flat colour only; no glass, gradients, glow, or card shadows.

STORY: The visitor sees "Naar" on a sign, types a city, sees each airport like a signpost row with its kilometres, picks dates, presses one yellow button, watches the price table fill route by route, and books the cheapest line.

FIRST VIEWPORT: Yellow band with name and one-line promise. Left column: recent searches, the blue "Naar" sign with the large input and destination airport rows, the dates page, the blue "Vanaf" sign with home input and origin airport rows with km, the yellow "Zoek vluchten" button with the exact search count. Right column: the price table (origins as rows, destinations as columns), empty until the search fills it, teaching what will appear.

FORM: Route booklet and signposts (ANWB-style road guide), grounded candidate 7 of 7. Seed key c1bdced8. Signature interaction: the distance table becomes a live price table; clicking a cell filters the results to that route. Raises: duration drawn as exact-length bars (labanotation); no chrome, flat fields (metro); calm rows that open when chosen (click, tap or Enter) with arrival and booking link (streaming wall); never on mere keyboard focus, because auto-expanding while tabbing shifts the list under the user; tabular figures, disabled = struck row (exposure record).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
