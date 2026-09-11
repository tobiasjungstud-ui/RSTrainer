"""Aufträge: Parameter → Prompt → Chat → Ergebnis zurücklesen.

Warum dieser Umweg statt eines einfachen Textfeldes?

Der naheliegende Weg wäre: Prompt anzeigen, Antwort in ein Feld kleben,
speichern. Das geht schief, sobald mehr als ein Auftrag im Umlauf ist – das
Diktat für Kind A landet im Profil von Kind B, oder eine halbe Chat-Antwort
inklusive «Gerne! Hier ist dein Diktat:» wandert in die Datenbank.

Deshalb bekommt jeder Auftrag eine **Auftragsnummer**, die im Prompt steht
und die der Chat in seiner Antwort wiederholen soll. Die Antwort ist in
Markierungen eingefasst und hat einen kleinen Kopfbereich. Beim Einfügen:

1. Markierungen suchen – fehlen sie, wird der Text als reiner Fliesstext
   übernommen (nichts geht verloren).
2. Auftragsnummer vergleichen – passt sie nicht, warnt die App deutlich,
   blockiert aber nicht.
3. Kopfbereich auswerten und die Formularfelder vorbelegen.

Der Auftrag selbst wird in der Datenbank mitgeführt (offen → eingefügt →
freigegeben), damit zwischen App und Chat nichts verloren geht.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass, field
from typing import Any

from . import prompt_templates as pt
from .olfa import Kategorienliste

TYP_PRAEFIX = {"diktat": "DIK", "uebungsblatt": "UEB", "minitest": "TST"}

STATUS_OFFEN = "offen"
STATUS_EINGEFUEGT = "eingefuegt"
STATUS_FREIGEGEBEN = "freigegeben"
STATUS_VERWORFEN = "verworfen"


def auftrag_code(typ: str) -> str:
    """Kurze, gut abtippbare Auftragsnummer, z. B. ``RST-DIK-4F7A2B``."""
    praefix = TYP_PRAEFIX.get(typ, "GEN")
    return f"RST-{praefix}-{secrets.token_hex(3).upper()}"


def kategorienblock(nummern: list[str], liste: Kategorienliste) -> str:
    """Formatiert die gewählten Kategorien exakt so, wie sie im Prompt stehen.

    Bewusst mit Nummer, Bezeichnung, Kurzbeschreibung und Beispiel: Das Modell
    im Chat kennt die OLFA-Nummerierung nicht und braucht die Erläuterung,
    sonst rät es.
    """
    zeilen = []
    for nr in nummern:
        k = liste.get(nr)
        if k is None:
            zeilen.append(f"- **{nr}** – (Kategorie nicht in der Liste gefunden)")
            continue
        teil = f"- **{k.nr} – {k.name}**: {k.kurzbeschreibung}"
        if k.beispiel and k.beispiel != "-":
            teil += f" Typischer Fehler: {k.beispiel}."
        zeilen.append(teil)
    return "\n".join(zeilen) if zeilen else "- (keine Kategorie gewählt)"


def prompt_bauen(typ: str, parameter: dict[str, Any], liste: Kategorienliste,
                 code: str | None = None,
                 rechtschreibvariante: str = "schweiz") -> tuple[str, str]:
    """Baut den fertigen Prompt. Rückgabe: ``(auftrag_code, prompt_text)``."""
    if typ not in pt.VORLAGEN:
        raise ValueError(f"Unbekannter Auftragstyp: {typ}")
    code = code or auftrag_code(typ)

    hinweis = pt.RECHTSCHREIBHINWEIS.get(
        rechtschreibvariante, pt.RECHTSCHREIBHINWEIS["schweiz"]
    )
    werte: dict[str, Any] = {
        "rolle": pt.ROLLE,
        "qualitaetsregeln": pt.QUALITAETSREGELN.format(rechtschreibhinweis=hinweis),
        "auftrag_code": code,
        "marke_anfang": pt.MARKE_ANFANG,
        "marke_ende": pt.MARKE_ENDE,
        "marke_uebung": pt.MARKE_UEBUNG,
        "marke_test": pt.MARKE_TEST,
        "marke_loesung": pt.MARKE_LOESUNG,
        "kopf_trenner": pt.KOPF_TRENNER,
        "kategorienblock": kategorienblock(
            list(parameter.get("kategorien", [])), liste
        ),
    }
    werte.update({k: v for k, v in parameter.items() if k != "kategorien"})

    try:
        text = pt.VORLAGEN[typ].format(**werte)
    except KeyError as fehler:
        raise KeyError(
            f"In der Vorlage '{typ}' steht der Platzhalter {fehler} , für den kein "
            "Wert übergeben wurde. Bitte prompt_templates.py prüfen."
        ) from fehler
    return code, text


# ---------------------------------------------------------------------------
# Ergebnis zurücklesen
# ---------------------------------------------------------------------------

@dataclass
class Ergebnis:
    """Was die App aus dem eingefügten Chat-Text herauslesen konnte."""

    typ: str | None = None
    auftrag_code: str | None = None
    titel: str = ""
    kopf: dict[str, str] = field(default_factory=dict)
    haupttext: str = ""
    uebungsteil: str = ""
    testteil: str = ""
    loesungen: str = ""
    strukturiert: bool = False
    hinweise: list[str] = field(default_factory=list)

    @property
    def ist_leer(self) -> bool:
        return not any([self.haupttext.strip(), self.uebungsteil.strip(),
                        self.testteil.strip()])


_KOPFZEILE = re.compile(r"^([A-ZÄÖÜ_]{3,20}):\s*(.*)$")


def _block_extrahieren(text: str) -> tuple[str, bool]:
    """Schneidet den Bereich zwischen den Markierungen heraus."""
    start = text.find(pt.MARKE_ANFANG)
    ende = text.rfind(pt.MARKE_ENDE)
    if start == -1 or ende == -1 or ende <= start:
        return text.strip(), False
    return text[start + len(pt.MARKE_ANFANG):ende].strip(), True


def _kopf_lesen(block: str) -> tuple[dict[str, str], str]:
    """Trennt ``SCHLUESSEL: Wert``-Zeilen am Anfang vom restlichen Text."""
    kopf: dict[str, str] = {}
    zeilen = block.splitlines()
    index = 0
    for zeile in zeilen:
        blank = zeile.strip()
        if not blank:
            index += 1
            continue
        if blank == pt.KOPF_TRENNER:
            index += 1
            break
        treffer = _KOPFZEILE.match(blank)
        if not treffer:
            break
        kopf[treffer.group(1).upper()] = treffer.group(2).strip()
        index += 1
    return kopf, "\n".join(zeilen[index:]).strip()


def _abschnitte_lesen(rest: str) -> dict[str, str]:
    """Zerlegt den Rest an den Abschnittsmarkierungen."""
    marken = [
        ("uebung", pt.MARKE_UEBUNG),
        ("test", pt.MARKE_TEST),
        ("loesung", pt.MARKE_LOESUNG),
    ]
    positionen = []
    for name, marke in marken:
        pos = rest.find(marke)
        if pos != -1:
            positionen.append((pos, name, marke))
    if not positionen:
        return {}
    positionen.sort()
    abschnitte: dict[str, str] = {}
    for i, (pos, name, marke) in enumerate(positionen):
        start = pos + len(marke)
        ende = positionen[i + 1][0] if i + 1 < len(positionen) else len(rest)
        abschnitte[name] = rest[start:ende].strip()
    return abschnitte


def ergebnis_lesen(eingefuegt: str, erwarteter_code: str | None = None,
                   erwarteter_typ: str | None = None) -> Ergebnis:
    """Wertet den aus dem Chat kopierten Text aus.

    Schlägt die strukturierte Auswertung fehl, wird der komplette Text als
    ``haupttext`` übernommen und ein Hinweis gesetzt. Es geht nie etwas
    verloren.
    """
    ergebnis = Ergebnis()
    if not (eingefuegt or "").strip():
        ergebnis.hinweise.append("Es wurde kein Text eingefügt.")
        return ergebnis

    block, strukturiert = _block_extrahieren(eingefuegt)
    ergebnis.strukturiert = strukturiert
    if not strukturiert:
        ergebnis.hinweise.append(
            "Die Markierungen ===RSTRAINER-ANFANG=== / ===RSTRAINER-ENDE=== wurden "
            "nicht gefunden. Der eingefügte Text wird unverändert als Fliesstext "
            "übernommen – bitte besonders sorgfältig gegenlesen."
        )

    kopf, rest = _kopf_lesen(block)
    ergebnis.kopf = kopf
    ergebnis.titel = kopf.get("TITEL", "").strip()
    ergebnis.auftrag_code = kopf.get("AUFTRAG") or None
    ergebnis.typ = (kopf.get("TYP") or "").strip().lower() or None

    abschnitte = _abschnitte_lesen(rest)
    if abschnitte:
        ergebnis.uebungsteil = abschnitte.get("uebung", "")
        ergebnis.testteil = abschnitte.get("test", "")
        ergebnis.loesungen = abschnitte.get("loesung", "")
        ergebnis.haupttext = ergebnis.uebungsteil or ergebnis.testteil
    else:
        ergebnis.haupttext = rest

    if erwarteter_code and ergebnis.auftrag_code and \
            ergebnis.auftrag_code.strip().upper() != erwarteter_code.upper():
        ergebnis.hinweise.append(
            f"Achtung: Die Antwort nennt die Auftragsnummer "
            f"{ergebnis.auftrag_code}, erwartet war {erwarteter_code}. "
            "Stammt der Text wirklich aus diesem Auftrag?"
        )
    elif erwarteter_code and not ergebnis.auftrag_code:
        ergebnis.hinweise.append(
            "Die Antwort enthält keine Auftragsnummer. Bitte prüfen, ob der "
            "Text zum richtigen Auftrag gehört."
        )

    if erwarteter_typ and ergebnis.typ and ergebnis.typ != erwarteter_typ:
        ergebnis.hinweise.append(
            f"Achtung: Die Antwort ist als «{ergebnis.typ}» gekennzeichnet, "
            f"erwartet war «{erwarteter_typ}»."
        )

    if ergebnis.ist_leer:
        ergebnis.hinweise.append("Im eingefügten Text war kein Inhalt zu finden.")
    return ergebnis
