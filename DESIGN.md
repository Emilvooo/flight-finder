---
name: Flight Finder
description: A route-booklet interface for comparing flights across nearby airports.
colors:
  route-yellow: "#FFD100"
  route-yellow-deep: "#F2C200"
  sign-blue: "#0E4C92"
  sign-blue-deep: "#0A3B73"
  sign-blue-hover: "#1C5CA6"
  sign-white: "#FFFFFF"
  sign-white-muted: "rgba(255, 255, 255, 0.8)"
  sign-white-soft: "rgba(255, 255, 255, 0.68)"
  sign-rule: "rgba(255, 255, 255, 0.26)"
  on-yellow-ink: "#141A24"
  cover: "#090C11"
  ground: "#0D1117"
  panel: "#161C25"
  panel-hover: "#1D2530"
  raised: "#2A3546"
  ink: "#ECEFF3"
  ink-muted: "#B7C0CC"
  ink-soft: "#8F99A8"
  faint: "#4A5463"
  rule: "#2E3846"
  rule-soft: "#232B36"
  route-line: "#5E9EEA"
  focus: "#8DBBF3"
  error-ink: "#FF9389"
  error-surface: "rgba(255, 100, 90, 0.12)"
  error-rule: "rgba(255, 120, 110, 0.35)"
typography:
  display:
    fontFamily: "Archivo, system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "2rem"
    fontWeight: 850
    lineHeight: 1
    letterSpacing: "-0.005em"
  headline:
    fontFamily: "Archivo, system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "1.875rem"
    fontWeight: 850
    lineHeight: 1
  title:
    fontFamily: "Archivo, system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "1.625rem"
    fontWeight: 850
    lineHeight: 1
  body:
    fontFamily: "Archivo, system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.45
  label:
    fontFamily: "Archivo, system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "0.875rem"
    fontWeight: 650
    lineHeight: 1.45
rounded:
  sign: "10px"
  control: "6px"
  compact: "4px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  2xl: "36px"
components:
  button-primary:
    backgroundColor: "{colors.route-yellow}"
    textColor: "{colors.on-yellow-ink}"
    typography: "{typography.display}"
    rounded: "{rounded.sign}"
    padding: "18px 22px"
  button-booking:
    backgroundColor: "{colors.sign-blue}"
    textColor: "{colors.sign-white}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  input-sign:
    backgroundColor: "{colors.sign-blue-deep}"
    textColor: "{colors.sign-white}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "12px 14px"
  input-panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    height: "46px"
  panel-sign:
    backgroundColor: "{colors.sign-blue}"
    textColor: "{colors.sign-white}"
    rounded: "{rounded.sign}"
    padding: "18px 18px 16px"
  panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sign}"
    padding: "18px"
  radio-segment:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink-muted}"
    rounded: "{rounded.control}"
    padding: "3px"
  chip-filter:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.panel}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "7px 10px 7px 12px"
  price-cell-best:
    backgroundColor: "{colors.route-yellow}"
    textColor: "{colors.on-yellow-ink}"
    typography: "{typography.body}"
    height: "60px"
    padding: "10px 14px 14px"
  result-row:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sign}"
    padding: "14px 16px"
---

# Design System: Flight Finder

## Overview

**Creative North Star: "The Route Booklet"**

The interface reads like a route guide at night: a near-black cover with a yellow wordmark and road-marking stripe opens onto blue wayfinding signs, dark panels, and a live fare atlas on a deep ground. There is one theme, dark; there is no light mode or theme switch. The visual hierarchy follows the travel path from location choices to dates, route prices, and flight details.

The system is direct and information-dense without looking like an online travel agency. Flat color, clear rules, tabular figures, and a single Archivo family keep the live search readable as it fills in.

**Key Characteristics:**
- Yellow wordmark, cover stripe, and search action; blue wayfinding surfaces.
- Dark panels and tables on a deeper ground.
- Condensed Archivo for sign lettering and route codes; tabular figures for comparison.
- Flat surfaces, thin rules, and structural inset frames.

## Colors

The palette pairs high-visibility route yellow and wayfinding blue with cool dark neutrals, light ink, restrained rules, and a separate soft-red error treatment.

### Primary
- **Route Yellow:** Wordmark, the 4px stripe under the cover, primary search action, best-price cells, and selected dates.
- **Deep Route Yellow:** Hover state for the primary action.

### Secondary
- **Wayfinding Blue:** Airport signs, price-table headings, and booking links.
- **Deep Wayfinding Blue:** Recessed inputs and segmented choices inside signs.
- **Route Line:** Progress meters, duration lines, and stop markers; Wayfinding Blue is too dark against the panels for these.
- **Focus:** Focus rings outside the signs (inside signs, focus is yellow).
- **Raised Wayfinding Blue:** Hover state for booking links.

### Tertiary
- **Error Red:** Validation and alert text, paired with a translucent red surface and border.

### Neutral
- **Sign White / Muted / Soft:** Text, secondary text, and disabled airport choices on blue signs.
- **Sign Rule:** Subtle dividers inside blue signs and table headings.
- **On-Yellow Ink:** All text and frames on Route Yellow.
- **Cover:** The header band.
- **Ground:** The page canvas; also the track of segmented controls.
- **Panel / Panel Hover / Raised:** Date panel, price table, and result list; hover and expanded detail; the selected segment.
- **Ink / Muted Ink / Soft Ink / Faint:** Primary text, supporting text, secondary data, and disabled calendar days.
- **Rule / Soft Rule:** Container outlines, table divisions, and control borders.

### Named Rules
**The Route Sign Rule.** Keep yellow for the wordmark and cover stripe, the main search action, the best fare, and selected dates, always with On-Yellow Ink on top. Use blue for airport wayfinding and price-table headings; keep the rest of the data on dark panels.

## Typography

**Display Font:** Archivo (with system-ui, -apple-system, and Segoe UI fallbacks)  
**Body Font:** Archivo (with the same system sans-serif fallbacks)  
**Label/Mono Font:** Archivo; tabular numerals are enabled for the interface.

**Character:** Archivo is a single-family system with a tight, variable-width voice for signs and route codes, and normal-width body copy for explanation. Heavy headings stay short and functional; numeric data aligns for scanning.

### Hierarchy
- **Display** (heavy, condensed): Brand name and primary sign lettering.
- **Headline** (heavy, condensed): Main panel and page headings.
- **Title** (heavy, condensed): Smaller section headings, especially on narrow screens.
- **Body** (regular, normal width): Instructions, status, route details, and form values.
- **Label** (semibold, normal width): Field names, table context, and compact status labels.

### Named Rules
**The Condense-for-Wayfinding Rule.** Use Archivo's condensed width for prominent signs and airport codes; keep explanatory copy at normal width.

## Layout

The desktop layout uses a capped 1320px frame with a 340–420px planner column, a flexible results column, and a 36px gutter. The planner and output each stack their own content with clear section gaps. At 1080px and below, the page becomes one column capped at 720px; the flight row changes to a compact two-row arrangement. At 560px and below, outer gutters and surface padding tighten, paired date fields stack, the Heen and Terug flex labels move above their segmented controls, and the main headings and action reduce in size.

The cover shares the content frame and edges at every width, so the mark always lines up with the first sign. On desktop it is one 72px row: mark and wordmark on the left, the one-line promise right-aligned in Soft Ink. At 1080px and below the cover narrows to the same 720px frame and the promise drops to its own line under the wordmark. At 560px and below the promise is hidden and the cover is a single compact brand row.

Spacing uses a compact 4–16px inner rhythm, 24px page gutters, and larger 32–36px separations between major regions. Tables retain their own horizontal scroll rather than forcing the whole page wider.

## Elevation & Depth

Depth is flat: the deep ground separates the panels, thin rules distinguish adjacent data, and hover surfaces shift one step lighter. Signs and the primary action use inset frames rather than floating shadows. The only external shadow belongs to the date picker popover, which floats above the page.

### Shadow Vocabulary
- **Sign frame** (`inset 0 0 0 4px var(--blue), inset 0 0 0 6px var(--on-blue)`): A blue and white inset outline around airport signs.
- **Primary action frame** (`inset 0 0 0 4px var(--yellow), inset 0 0 0 6px var(--on-yellow)`): A yellow and ink inset outline around the search action.
- **Sign field ring** (`inset 0 0 0 1px rgba(255, 255, 255, 0.32)`): Outlines recessed inputs inside blue signs.
- **Popover** (`0 16px 40px rgba(0, 0, 0, 0.55)`): The date picker only.

### Named Rules
**The Flat Print Rule.** Build depth with tone steps, rules, and inset frames. Do not add ambient card shadows, gradients, or glow; only true overlays (the date picker) cast a shadow.

## Shapes

Sign and page containers have softly rounded corners; fields and controls use a tighter radius, with compact geometry for small selection marks and tracks. Borders are thin and cool-toned. The blue sign’s double inset frame and the main action’s ink frame are the recurring graphic edges; table and result surfaces use square internal divisions.

## Components

### Buttons
- **Character:** Bold, tactile, and easy to identify by purpose.
- **Shape:** Large sign radius for the search action; tighter control radius for booking links.
- **Primary:** Route yellow with ink text and a double inset ink frame; full-width with a strong Archivo label. The search action and its count line stick to the bottom of the viewport on a Ground band while the planner scrolls, so it is always in reach, also on phones. It responds at once: "Luchthavens zoeken…" while typed places still resolve, then "Bezig met zoeken…".
- **Hover / Focus:** The primary action deepens to the yellow hover token and depresses by one pixel on press. Focus uses the light-blue Focus outline. Booking links shift to the lighter blue hover token.
- **Booking:** Blue fill, white text, and a compact control shape; it continues to the external booking provider.

### Chips
- **Style:** Filter chips use a light Ink fill, dark Panel text, and the compact control radius. Recent-search tags use a Panel surface, a thin neutral outline, and a divided remove action.
- **State:** A selected route filter is explicit and removable; recent searches restore the query rather than acting as decoration.

### Cards / Containers
- **Corner Style:** Sign and page radius tokens.
- **Background:** Blue for airport signs; Panel for the date panel, the price matrix, and result lists.
- **Shadow Strategy:** Flat at rest; see Elevation & Depth for the inset sign/action frames and the selected-segment cue.
- **Border:** Panels use the Rule color; internal table and result divisions use Soft Rule.
- **Internal Padding:** Use the spacing scale, with tighter padding at mobile widths.

### Inputs / Fields
- **Style:** Destination and home inputs are recessed Deep Wayfinding Blue fields with white text and a thin white ring, set into blue signs. Date and select controls are Panel fields with a thin neutral stroke.
- **Focus:** Use the Focus outline on panel fields and a yellow outline inside blue signs.
- **Error / Disabled:** Invalid date fields switch to the error border. Disabled airport rows fade and strike through their airport code and city.

### Segmented Choices
The panel variant sits on a Ground-colored track; the selected option becomes a Raised segment. Within a sign, the track deepens to blue and the selected option becomes white with blue text. Choices wrap when space is limited.

### Airport Signs
Blue destination and origin panels use a double inset white frame. Their large input, airport rows, distance labels, selected state, and count control stay within the same sign surface. Unselected airports are muted and struck through, not removed from the list. Under the home input, a pin line names the recognised place ("7991 AW, Dwingeloo"), so people can check that a postcode points to the right town.

### Return Sign
A third blue sign, "Terug" (mirrored route arrow), appears only when a return date is set. A segmented choice offers "Retourticket" (one round-trip ticket) or "Zelf combineren" (two one-way tickets). "Zelf combineren" reveals two sub-sections with condensed sub-headings:
- **Terug vanaf:** destination-side airports. By default this list mirrors the Naar selection; the first toggle makes it independent, and a "Zelfde als bij Naar" text link links it again.
- **Landen op:** "Waar ik vertrok" (default; the return lands where the outbound flight departed, for a parked car) or "Kies zelf", which shows a home-side airport list. That list behaves like Terug vanaf, with a "Zelfde als bij Vanaf" link.

### Add Airport
Every airport list ends with a quiet "+ Luchthaven toevoegen" button. It opens a recessed input with a close icon; the input is an ARIA combobox. While you type, a dark popover listbox shows up to eight airports, each with the condensed code, city, the country in Dutch followed by the full airport name (country first, so it survives truncation and tells two Barcelonas apart), and the distance to home or the destination. Airports already in the list are marked "Staat al aan" or "Staat uit · zet aan". Nearby airports rank first, then exact code or city matches, then larger airports. Unknown place names, such as Dutch "Wenen", fall back to geocoding and show the airports around that place. Arrow keys move through the list, Enter or click adds the airport, and Escape closes the list and then the row. An added airport joins that side's pool with its distance to home or the destination. It is switched on only in the list where it was added, so other selections do not change silently. Added airports are kept for the current destination or home location and are stored with recent searches.

The "Naar" field uses the same combobox, with distances to home. Typing does not change the airport list below; the list resolves when a suggestion is chosen, on Enter, or when the field is left with typed text (then the text is looked up as before). A chosen airport is pinned first in the list and kept with recent searches. When the text is a place without its own airport, such as "Brugge" or "Costa Brava", the first option is "Rond <plaats>" with a pin icon, separated by a fine rule; it keeps the typed text and lists the airports around that place. Choosing with Enter moves on to the departure date.

### Price Matrix
The table places origins in sticky row headers and destinations in blue column headers. A best fare is highlighted in route yellow; selecting a price filters the flight list to that route. During search, a small Route Line meter reports each route’s progress.

Above the table, the progress bar reads "12 van 45 · nog ca. 10 s". Until the first route returns, a Route Line segment sweeps through the track, so the search never looks idle. A quiet outlined "Stoppen" button ends the search, including the server-side queries, and keeps the prices found; unsearched cells then read "—" (niet gezocht). When finished, the status names the search: "Klaar: Barcelona, 20 nov – 27 nov." When the form changes after a search, a Panel note says the prices belong to the previous search, with a light-ink "Opnieuw zoeken" button; the table and list turn grey and dim until the search runs again. Live updates skip identical markup and pause while a pointer is down on the table or list, so a click during the search is never lost.

### Date Picker
Dates use Air Datepicker 3.6 (loaded from jsDelivr with SRI) on read-only fields with a calendar icon, themed entirely through its `--adp-*` variables from the tokens above. It uses a Dutch locale with Monday as the first day. The selected day is Route Yellow with ink text. In the return calendar, the departure day stays yellow, days before it are disabled, and the days between departure and return get a faint yellow tint. Choosing a departure date moves the return calendar to that month and opens it right away when no return date is set. A "Geen terugvlucht" button and a clear button in the field make the trip one-way. Field values read as `vr 13 nov`, with a short year (`do 21 jan ’27`) only when it is not the current year. Enter in a date field picks the day and never submits the form.

### Icons
Two families, both inline SVG from one sprite. UI icons (check, close, chevron, plus/minus, external link, alert, arrow, plane) are Lucide paths at a 2px stroke with round caps. Sign glyphs (the right-pointing route arrow and the home pictogram) are filled shapes, like the pictograms on road signs, and appear only on signs and the main search action. Never use emoji or Unicode symbols as icons.

### Flight Results
Rows are calm Panel surfaces with fine dividers. Each route is drawn as a duration-proportional line with stop markers, and the expanded detail appears only after a row is activated, not on keyboard focus. The best price receives a compact yellow highlight. On wide screens the cheapest row opens when the search finishes; on phones all rows stay closed, so the prices stay comparable. The return options of the three cheapest round trips load in the background, so they are ready when a row opens.

A round-trip row shows "terug" with the return date under the outbound line. Google lists only outbound flights for a round trip, so the expanded detail has a "Heen" block and a "Terug" block. The Terug block loads that day's return flights when the row opens (via `/return-flights`), lists them as time, airline and duration without a price, puts the outbound airline first with a "Zelfde maatschappij" tag, and says that the shown price is the lowest round-trip price with this outbound flight.

## Do's and Don'ts

### Do:
- **Do** reserve route yellow for the wordmark and cover stripe, main search action, best-price emphasis, and selected dates.
- **Do** use blue sign surfaces for airport wayfinding and price-table headings, with the inset white sign frame.
- **Do** keep price data on dark panels over the deeper ground, using thin rules to organize it.
- **Do** use tabular figures and duration-proportional route lines to support comparison.
- **Do** expand a flight row only after activation, so keyboard focus does not move the results list.

### Don't:
- **Don't** add ambient card shadows, gradients, glow, or glass effects.
- **Don't** use the yellow accent as a broad fill for ordinary fields or long result rows.
- **Don't** add a light theme or theme switch; the product has one dark theme.
- **Don't** expand result details merely because a row receives keyboard focus.
- **Don't** remove a toggled-off airport from its sign list; show its disabled state in place.
