#!/usr/bin/env python3

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


PDF_PATH = "torun-vluchtopties.pdf"


def p(text, style):
    return Paragraph(text, style)


def main():
    doc = SimpleDocTemplate(
        PDF_PATH,
        pagesize=landscape(A4),
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8.5, leading=11))
    styles.add(ParagraphStyle(name="Note", parent=styles["BodyText"], fontSize=9, leading=12, textColor=colors.HexColor("#444444")))
    styles.add(ParagraphStyle(name="H", parent=styles["Heading2"], fontSize=13, leading=16, spaceBefore=10, spaceAfter=6))

    story = []
    story.append(p("Vluchtopties naar Torun via Warschau of Gdansk", styles["Title"]))
    story.append(p("Periode: do 24 sep - zo 27 sep of vr 25 sep - ma 28 sep 2026. Voorwaarde: retourvlucht vertrekt na 12:00.", styles["Note"]))
    story.append(Spacer(1, 0.35 * cm))

    cell = styles["Small"]
    head = ParagraphStyle(name="TableHead", parent=styles["Small"], textColor=colors.white, fontName="Helvetica-Bold")
    data = [
        [p("#", head), p("Route", head), p("Data", head), p("Heen", head), p("Terug", head), p("Vlucht", head), p("Parkeren", head), p("Totaal", head)],
        [
            p("1", cell),
            p("Dortmund (DTM) - Warsaw Chopin (WAW)", cell),
            p("do 24 - zo 27 sep", cell),
            p("13:35 Wizz Air<br/>direct, 1u45", cell),
            p("14:00 Wizz Air<br/>direct, 1u50", cell),
            p("ca. EUR 152", cell),
            p("DTM: P3/P6/P7 zijn de goedkoopste categorieen. Reken indicatief EUR 40-70 voor 3-4 dagen, plus evt. shuttle EUR 2 p.p. vanaf P6/P7.", cell),
            p("ca. EUR 192-222", cell),
        ],
        [
            p("2", cell),
            p("Eindhoven (EIN) - Warsaw Chopin (WAW)", cell),
            p("vr 25 - ma 28 sep", cell),
            p("15:30 Wizz Air<br/>direct, 1u55", cell),
            p("12:50 Wizz Air<br/>direct, 2u05", cell),
            p("ca. EUR 154", cell),
            p("EIN: officiele parking vanaf EUR 7/dag indien beschikbaar en online gereserveerd. P5/P4/P3 liggen op 10/6/4 min lopen. Reken indicatief EUR 28-65.", cell),
            p("ca. EUR 182-219", cell),
        ],
        [
            p("3", cell),
            p("Eindhoven (EIN) - Warsaw Chopin (WAW)", cell),
            p("do 24 - zo 27 sep", cell),
            p("15:30 Wizz Air<br/>direct, 1u55", cell),
            p("12:50 Wizz Air<br/>direct, 2u05", cell),
            p("ca. EUR 175", cell),
            p("EIN: zelfde parkeerinschatting als optie 2; indicatief EUR 28-65 afhankelijk van P5/P4/P3 en beschikbaarheid.", cell),
            p("ca. EUR 203-240", cell),
        ],
    ]
    table = Table(data, colWidths=[0.6 * cm, 4.0 * cm, 2.4 * cm, 3.0 * cm, 3.0 * cm, 1.8 * cm, 6.9 * cm, 2.3 * cm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
    ]))
    story.append(table)

    story.append(p("Aanbeveling", styles["H"]))
    story.append(p("Mijn voorkeur is optie 2: Eindhoven - Warschau, vrijdag tot maandag. De vluchtprijs is vrijwel gelijk aan optie 1, beide vluchten zijn direct, de retour vertrekt netjes na 12:00, en Eindhoven is praktischer/comfortabeler vanaf Assen dan Dortmund. Parkeren op Eindhoven is overzichtelijk en lopend naar de terminal; bij Dortmund zijn de goedkoopste terreinen vaak verder weg en mogelijk met shuttle.", styles["BodyText"]))

    story.append(p("Waarom niet Gdansk?", styles["H"]))
    story.append(p("Eindhoven - Gdansk was goedkoop op de heenweg, maar de goedkope directe terugvlucht vertrekt rond 06:45. Als retour na 12:00 vereist is, kom je uit op duurdere KLM-opties met overstap en veel langere reistijd. Daardoor wordt Gdansk minder logisch dan Warschau.", styles["BodyText"]))

    story.append(p("Parkeren: bronnen en kanttekeningen", styles["H"]))
    story.append(p("Eindhoven Airport: officiele site vermeldt parkeren vanaf EUR 7 per dag indien beschikbaar en online gereserveerd. P3 Silver ligt op ca. 4 min lopen, P4 Bronze+ op ca. 6 min en P5 Bronze op ca. 10 min. De exacte prijs moet via de reserveringsmodule worden gecontroleerd voor 24-27 of 25-28 september 2026.", styles["Small"]))
    story.append(Spacer(1, 0.1 * cm))
    story.append(p("Dortmund Airport: officiele site noemt P3, P6 en P7 als goedkoopste categorieen. P6/P7 hebben shuttle/buslijn 490 naar de terminal; die kost EUR 2 per persoon per enkele rit. De officiele tabel toont korte-duur tarieven en verwijst voor reserveringen naar de online module, dus de meerdaagse prijs is indicatief.", styles["Small"]))

    story.append(p("Google Flights links", styles["H"]))
    links = [
        "1. DTM-WAW do-zo: https://www.google.com/travel/flights?tfs=GhoSCjIwMjYtMDktMjRqBRIDRFRNcgUSA1dBVxoaEgoyMDI2LTA5LTI3agUSA1dBV3IFEgNEVE1CAQFIAZgBAQ==&hl=nl",
        "2. EIN-WAW vr-ma: https://www.google.com/travel/flights?tfs=GhoSCjIwMjYtMDktMjVqBRIDRUlOcgUSA1dBVxoaEgoyMDI2LTA5LTI4agUSA1dBV3IFEgNFSU5CAQFIAZgBAQ==&hl=nl",
        "3. EIN-WAW do-zo: https://www.google.com/travel/flights?tfs=GhoSCjIwMjYtMDktMjRqBRIDRUlOcgUSA1dBVxoaEgoyMDI2LTA5LTI3agUSA1dBV3IFEgNFSU5CAQFIAZgBAQ==&hl=nl",
    ]
    for link in links:
        story.append(p(link, styles["Small"]))

    doc.build(story)


if __name__ == "__main__":
    main()
