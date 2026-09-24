"""PDF-Ausgabe der Blätter – dieselben Dokumente wie in :mod:`rstrainer.docx_export`.

Warum beides? Die Word-Datei lässt sich vor dem Ausdrucken noch anpassen: eine
Aufgabe streichen, eine Zeile zufügen, den Namen korrigieren. Das PDF kann das
nicht, dafür sieht es überall gleich aus – auf dem Schulrechner, auf dem
Tablet, im Kopierraum. Wer ein Blatt nur noch drucken oder verschicken will,
nimmt das PDF; wer es weiterbearbeiten will, die Word-Datei.

Die drei Funktionen haben **dieselben Signaturen** wie ihre Gegenstücke in
``docx_export``. Die Oberfläche wählt darum nur das Modul aus und ruft
unverändert dieselbe Funktion auf::

    modul = pdf_export if format == "pdf" else docx_export
    modul.uebungsblatt_schreiben(pfad, ...)

Gesetzt wird mit reportlab: ein reines Python-Paket ohne Systemabhängigkeiten,
das sich auf einem Lehrerlaptop ohne Administratorrechte installieren lässt.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (Image, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

from .kategorien import Register, schwerpunkte

GRAU = colors.HexColor("#555555")
ROT = colors.HexColor("#B02222")
LINIE = colors.HexColor("#999999")

#: Wie in der Word-Fassung: Calibri-Anmutung, 12 pt, ruhiger Zeilenabstand.
#: Helvetica ist in jedem PDF-Betrachter vorhanden – kein eingebetteter Font,
#: keine Überraschung beim Öffnen auf einem fremden Gerät.
BASIS = ParagraphStyle("basis", fontName="Helvetica", fontSize=12, leading=17,
                       spaceAfter=4)
TITEL = ParagraphStyle("titel", parent=BASIS, fontName="Helvetica-Bold",
                       fontSize=16, leading=20, spaceBefore=10, spaceAfter=2)
UNTER = ParagraphStyle("unter", parent=BASIS, fontName="Helvetica-Oblique",
                       fontSize=10, leading=13, textColor=GRAU, spaceAfter=0)
FETT = ParagraphStyle("fett", parent=BASIS, fontName="Helvetica-Bold",
                      spaceBefore=12)
KOPFRECHTS = ParagraphStyle("kopfrechts", parent=BASIS, alignment=TA_RIGHT,
                            fontSize=11, spaceAfter=0)
KOPFLINKS = ParagraphStyle("kopflinks", parent=BASIS, fontSize=11, spaceAfter=0)
WARNUNG = ParagraphStyle("warnung", parent=BASIS, fontName="Helvetica-Bold",
                         fontSize=14, textColor=ROT, spaceAfter=8)
ZELLE = ParagraphStyle("zelle", parent=BASIS, fontSize=10, leading=13, spaceAfter=0)
ZELLE_FETT = ParagraphStyle("zellefett", parent=ZELLE, fontName="Helvetica-Bold")

TABELLENSTIL = TableStyle([
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFEFEF")),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ("TOPPADDING", (0, 0), (-1, -1), 3),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
])


def _dokument(pfad: Path, titel: str) -> SimpleDocTemplate:
    """A4 mit denselben Rändern wie die Word-Fassung."""
    return SimpleDocTemplate(
        str(pfad), pagesize=A4,
        topMargin=2.0 * cm, bottomMargin=2.0 * cm,
        leftMargin=2.2 * cm, rightMargin=2.0 * cm,
        title=titel, author="RSTrainer",
    )


#: Zeichen, die die eingebauten PDF-Schriften nicht kennen, samt Ersatz.
#: Der Blatttext kommt aus einem Sprachmodell und enthält gern einen Pfeil
#: («Flus → Fluss») oder ein Aufzählungszeichen. Ohne Ersatz druckte das PDF
#: dafür ein falsches Zeichen – ein Pfeil erschien als «fi». Lieber eine
#: schlichte, aber richtige Darstellung als ein hübsches Rätsel.
ERSATZZEICHEN = {
    "\u2022": "\u00b7",      # Aufzählungspunkt → Mittelpunkt
    "\u25aa": "\u00b7", "\u25cf": "\u00b7", "\u2219": "\u00b7",
    "\u2192": "->", "\u2190": "<-", "\u21d2": "=>", "\u2194": "<->",
    "\u2713": "ok", "\u2714": "ok", "\u2717": "x", "\u2718": "x",
    "\u2026": "...", "\u2011": "-", "\u2012": "-", "\u2015": "-",
    "\u00a0": " ", "\u202f": " ", "\u2009": " ",
    "\u2032": "'", "\u2033": '"',
}


def _winansi(text: str) -> str:
    """Text auf den Zeichenvorrat der eingebauten PDF-Schriften bringen.

    Helvetica wird mit WinAnsi kodiert. Umlaute, «Guillemets» und Gedankenstriche
    sind darin enthalten, Pfeile und Aufzählungspunkte nicht. Was auch nach der
    Ersetzung nicht darstellbar ist, wird zu «?» – sichtbar falsch ist besser
    als unsichtbar falsch.
    """
    text = "".join(ERSATZZEICHEN.get(zeichen, zeichen) for zeichen in str(text or ""))
    return text.encode("cp1252", "replace").decode("cp1252")


def _sicher(zeile: str) -> str:
    """Eine Textzeile für reportlab aufbereiten.

    Zwei Dinge sind dabei wichtig. Erstens muss alles, was nach XML aussieht,
    entschärft werden – ein «<» im Schülertext würde sonst als Markup gelesen.
    Zweitens bleibt die Einrückung erhalten: Die Übungsblätter rücken ihre
    Fehlersuchtexte ein, und ohne führende Leerzeichen verlöre der Text seine
    Gliederung.
    """
    roh = _winansi(zeile).rstrip()
    fuehrend = len(roh) - len(roh.lstrip(" "))
    return "&nbsp;" * fuehrend + escape(roh[fuehrend:])


def _textblock(text: str, stil: ParagraphStyle = BASIS) -> list:
    """Mehrzeiligen Text absatzweise übernehmen, Leerzeilen bleiben stehen."""
    aus: list = []
    for zeile in (text or "").split("\n"):
        if zeile.strip():
            aus.append(Paragraph(_sicher(zeile), stil))
        else:
            aus.append(Spacer(1, 6))
    return aus


def _kopfzeile(name: str, datum: str, titel: str, untertitel: str = "") -> list:
    """Name und Datum links und rechts, darunter Titel und Trennlinie."""
    kopf = Table(
        [[Paragraph(f"<b>Name:</b> {_sicher(name)}", KOPFLINKS),
          Paragraph(f"<b>Datum:</b> {_sicher(datum)}", KOPFRECHTS)]],
        colWidths=["50%", "50%"],
    )
    kopf.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    aus: list = [kopf, Paragraph(_sicher(titel), TITEL)]
    if untertitel:
        aus.append(Paragraph(_sicher(untertitel), UNTER))
    strich = Table([[""]], colWidths=["100%"], rowHeights=[6])
    strich.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.7, LINIE)]))
    aus += [strich, Spacer(1, 8)]
    return aus


def _kategorien_untertitel(kategorien: list[str], register: Register) -> str:
    if not kategorien:
        return ""
    return "Förderschwerpunkte: " + "  \u00b7  ".join(register.label(nr) for nr in kategorien)


def _tabelle(kopf: list[str], zeilen: list[list[str]], breiten: list[str]) -> Table:
    daten = [[Paragraph(_sicher(x), ZELLE_FETT) for x in kopf]]
    daten += [[Paragraph(_sicher(str(x)), ZELLE) for x in zeile] for zeile in zeilen]
    tabelle = Table(daten, colWidths=breiten, repeatRows=1)
    tabelle.setStyle(TABELLENSTIL)
    return tabelle


# ---------------------------------------------------------------------------
# Übungsblatt + Mini-Test
# ---------------------------------------------------------------------------

def uebungsblatt_schreiben(pfad: Path | str, schuelername: str, titel: str,
                           kategorien: list[str], register: Register,
                           inhalt_uebung: str, inhalt_test: str,
                           loesungen: str = "", datum: str | None = None,
                           loesungen_anhaengen: bool = False) -> Path:
    """Schreibt Übungsblatt (Seite 1) und Mini-Test (Seite 2) als PDF."""
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    datum = datum or date.today().strftime("%d.%m.%Y")
    untertitel = _kategorien_untertitel(kategorien, register)

    teile: list = []
    teile += _kopfzeile(schuelername, datum, titel, untertitel)
    teile += _textblock(inhalt_uebung)

    teile.append(PageBreak())
    teile += _kopfzeile(schuelername, datum, f"Mini-Test: {titel}", untertitel)
    teile += _textblock(inhalt_test)

    # Das Lösungsblatt kommt nur auf ausdrücklichen Wunsch mit und trägt die
    # Warnung ganz oben – wer die Seiten stapelweise kopiert, soll sie sehen.
    if loesungen_anhaengen and loesungen.strip():
        teile.append(PageBreak())
        teile.append(Paragraph("LÖSUNGSBLATT – NICHT AUSTEILEN", WARNUNG))
        teile += _kopfzeile(schuelername, datum, f"Lösungen: {titel}")
        teile += _textblock(loesungen)

    _dokument(pfad, titel).build(teile)
    return pfad


# ---------------------------------------------------------------------------
# Informationsblatt zu einem Text
# ---------------------------------------------------------------------------

def informationsblatt_schreiben(pfad: Path | str, schuelername: str,
                                diktat_titel: str, datum: str,
                                fehler: list[dict], register: Register,
                                kennzahlen: dict | None = None,
                                kommentar: str = "",
                                diktattext: str = "",
                                art: str = "diktat") -> Path:
    """Fehlerliste, Schwerpunkte und Kurzkommentar zu einem Text."""
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    bezeichnung = {"freitext": "Freier Text", "diktiert": "Diktierter Text (Sprachsoftware) – nur Satzbau und Grammatik"}.get(art, "Diktat")

    teile: list = _kopfzeile(
        schuelername, datum, f"Auswertung: {diktat_titel}",
        f"Rechtschreibförderung – Informationsblatt · {bezeichnung}")

    if kennzahlen:
        text = (f"<b>Überblick:</b> {kennzahlen.get('wortzahl_original', 0)} Wörter, "
                f"{len(fehler)} erfasste Fehler")
        if kennzahlen.get("fehlerquote_prozent") is not None:
            text += f", Fehlerquote {kennzahlen['fehlerquote_prozent']} %"
        teile.append(Paragraph(text + ".", BASIS))

    # Schwerpunkte zuerst: Das ist die Antwort auf «Woran arbeiten wir?».
    # Die vollständige Fehlerliste darunter belegt sie nur.
    punkte = schwerpunkte(fehler, hoechstens=8)
    if punkte.liste:
        teile.append(Paragraph("Schwerpunkte", FETT))
        for nr, anzahl in punkte.liste:
            teile.append(Paragraph(f"\u00b7 {_sicher(register.label(nr))}: {anzahl}\u00d7", BASIS))
        if punkte.rest:
            teile.append(Paragraph(
                f"Dazu {punkte.rest} weitere Fehlerarten mit einzelnen Vorkommen.", BASIS))

    teile.append(Paragraph("Erfasste Fehler", FETT))
    if fehler:
        teile.append(_tabelle(
            ["Richtig", "Geschrieben", "Fehlerart", "Im Text"],
            [[e.get("wort_original", ""), e.get("wort_schueler", ""),
              register.label(str(e.get("kategorie_nr", ""))), e.get("kontext", "")]
             for e in fehler],
            ["18%", "18%", "30%", "34%"],
        ))
    else:
        teile.append(Paragraph("Keine Fehler erfasst.", BASIS))

    if kommentar.strip():
        teile.append(Paragraph("Kommentar", FETT))
        teile += _textblock(kommentar)

    if diktattext.strip():
        teile.append(PageBreak())
        teile.append(Paragraph(
            "Text des Kindes" if art in ("freitext", "diktiert") else "Diktattext (Original)", FETT))
        teile += _textblock(diktattext)

    _dokument(pfad, f"Auswertung: {diktat_titel}").build(teile)
    return pfad


# ---------------------------------------------------------------------------
# Verlaufsbericht (für Elterngespräche)
# ---------------------------------------------------------------------------

def verlaufsbericht_schreiben(pfad: Path | str, schuelername: str,
                              zeitraum: str, trendzeilen: list[dict],
                              register: Register,
                              diagramm_pfad: Path | str | None = None,
                              kommentar: str = "") -> Path:
    """Übersicht über den Lernverlauf, geeignet zum Ausdrucken."""
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)

    teile: list = _kopfzeile(schuelername, date.today().strftime("%d.%m.%Y"),
                             "Lernverlauf Rechtschreibung",
                             f"Betrachteter Zeitraum: {zeitraum}")

    if diagramm_pfad and Path(diagramm_pfad).exists():
        # Auf die Textbreite skalieren, Seitenverhältnis behalten.
        bild = Image(str(diagramm_pfad))
        breite = 16 * cm
        bild.drawHeight = bild.drawHeight * (breite / bild.drawWidth)
        bild.drawWidth = breite
        teile += [bild, Spacer(1, 10)]

    if trendzeilen:
        teile.append(_tabelle(
            ["Fehlerart", "Fehler gesamt", "Entwicklung", "Fehler/100 Wörter"],
            [[register.label(str(z.get("kategorie_nr", ""))), z.get("summe_gesamt", 0),
              z.get("text", ""),
              f"{z.get('rate_vorher', 0)} → {z.get('rate_aktuell', 0)}"]
             for z in trendzeilen],
            ["40%", "16%", "24%", "20%"],
        ))
    else:
        teile.append(Paragraph("Noch keine auswertbaren Daten vorhanden.", BASIS))

    if kommentar.strip():
        teile.append(Paragraph("Einschätzung der Lehrperson", FETT))
        teile += _textblock(kommentar)

    _dokument(pfad, "Lernverlauf Rechtschreibung").build(teile)
    return pfad
