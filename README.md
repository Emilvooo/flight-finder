# Flight Finder

Flight Finder zoekt de goedkoopste vlucht door alle zinnige combinaties tegelijk te doorzoeken: elke luchthaven rond je huis (ook over de Duitse grens), elke luchthaven rond je bestemming en, als je wilt, een paar dagen eerder of later. De prijzen komen van Google Flights. Daar boek je ook.

## Wat het kan

- Vertrekken vanaf meerdere luchthavens rond een adres of postcode (standaard 7991AW).
- Een bestemming als stad, streek of luchthavencode (“Rome”, “Costa Brava”, “GRO”). De app kiest de luchthavens eromheen.
- Enkele reis of retour, met flexibele data apart voor heen en terug (tot ±3 dagen).
- Combi-reis: twee losse enkele reizen, bijvoorbeeld terug vanaf een andere luchthaven of landen op een ander vliegveld bij huis.
- Live voortgang: de eerste resultaten verschijnen al tijdens het zoeken, en je kunt de zoekopdracht stoppen.
- Een prijstabel per datum en de terugvluchten van die dag.
- Je thuislocatie en recente zoekopdrachten blijven in je browser bewaard.

## Starten

Je hebt Python 3.9 of nieuwer nodig.

```sh
pip install -r requirements.txt
python3 -m uvicorn main:app --port 8000
```

Open daarna http://127.0.0.1:8000.

Met Docker:

```sh
docker build -t flight-finder .
docker run -p 8000:8000 flight-finder
```

## Command line

`flight_finder.py` werkt ook zonder webinterface:

```sh
python3 flight_finder.py --to Barcelona --depart 2026-12-04 --return 2026-12-08 --flex 1
```

Zonder `--to` en `--depart` stelt het script de vragen zelf. `python3 flight_finder.py --help` toont alle opties.

## Hoe het werkt

| Bestand | Inhoud |
|---|---|
| `main.py` | FastAPI-server. Start zoekopdrachten en stuurt de voortgang via Server-Sent Events. |
| `flight_finder.py` | Luchthavens zoeken (airportsdata, plus OpenStreetMap Nominatim en Wikidata voor plaatsnamen, streken en postcodes), Google Flights bevragen via fast-flights, en de command line. |
| `templates/index.html` | De hele interface, met CSS en JavaScript inline. Er is geen buildstap. |
| `DESIGN.md`, `PRODUCT.md` | Ontwerpsysteem en productcontext. |

Een zoekopdracht bevraagt maximaal 10 routes tegelijk, en elke route duurt ongeveer 0,8 seconde. Resultaten per route blijven 10 minuten bewaard, dus dezelfde of een aangepaste zoekopdracht is daarna bijna direct klaar.

## Let op

Flight Finder gebruikt geen officiële API. fast-flights leest de pagina's van Google Flights, dus als Google die verandert, kan het zoeken stoppen met werken. Controleer de prijs altijd op Google Flights voordat je boekt.
