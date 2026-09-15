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

import json
import re
import secrets
from dataclasses import dataclass, field
from typing import Any

from . import prompt_templates as pt
from .diffing import kategorie_vorschlaege, marker_bestimmen
from .olfa import Kategorienliste
from .taxonomie import OBERBEGRIFFE, Sammlung, kennung, pfad_normalisieren, pfad_schluessel
from .textwerkzeuge import satz_kontext, woerter

TYP_PRAEFIX = {"diktat": "DIK", "uebungsblatt": "UEB", "minitest": "TST"}

STATUS_OFFEN = "offen"
STATUS_EINGEFUEGT = "eingefuegt"
STATUS_FREIGEGEBEN = "freigegeben"
STATUS_VERWORFEN = "verworfen"


def auftrag_code(typ: str) -> str:
    """Kurze, gut abtippbare Auftragsnummer, z. B. ``RST-DIK-4F7A2B``."""
    praefix = TYP_PRAEFIX.get(typ, "GEN")
    return f"RST-{praefix}-{secrets.token_hex(3).upper()}"


def kategorienblock(nummern: list[str], liste: Kategorienliste,
                    sondierung: list[str] | None = None,
                    sammlung: Sammlung | None = None) -> str:
    """Formatiert die gewählten Kategorien exakt so, wie sie im Prompt stehen.

    Bewusst mit Nummer, Bezeichnung, Kurzbeschreibung und Beispiel: Das Modell
    kennt die OLFA-Nummerierung nicht und rät sonst. Kategorien, die nur zur
    Sondierung mitlaufen, werden als solche ausgewiesen – sonst erzeugt das
    Modell dort ebenso viele Zielwörter wie bei den bekannten Schwerpunkten.
    """
    sondierung = sondierung or []
    zeilen = []
    for nr in nummern:
        rolle = (" _(Sondierung: noch unklar, ob hier Schwierigkeiten bestehen)_"
                 if nr in sondierung else " _(bekannter Schwerpunkt)_")
        k = liste.get(nr)
        if k is not None:
            teil = f"- **{k.nr} – {k.name}**{rolle}: {k.kurzbeschreibung}"
            if k.beispiel and k.beispiel != "-":
                teil += f" Typischer Fehler: {k.beispiel}."
            zeilen.append(teil)
            continue
        art = sammlung.get(nr) if sammlung is not None else None
        if art is not None:
            ergaenzung = f": {art.beschreibung}" if art.beschreibung else ""
            zeilen.append(f"- **{art.label}**{rolle}{ergaenzung}")
            continue
        zeilen.append(f"- **{nr}** – (Kategorie nicht in der Liste gefunden)")
    return "\n".join(zeilen) if zeilen else "- (keine Kategorie gewählt)"


def prompt_bauen(typ: str, parameter: dict[str, Any], liste: Kategorienliste,
                 code: str | None = None,
                 sammlung: Sammlung | None = None) -> tuple[str, str]:
    """Baut den fertigen Prompt. Rückgabe: ``(auftrag_code, prompt_text)``."""
    if typ not in pt.VORLAGEN:
        raise ValueError(f"Unbekannter Auftragstyp: {typ}")
    code = code or auftrag_code(typ)

    schwierigkeit = str(parameter.get("schwierigkeit", "mittel"))
    werte: dict[str, Any] = {
        "rolle": pt.ROLLE,
        "qualitaetsregeln": pt.QUALITAETSREGELN.format(
            rechtschreibhinweis=pt.RECHTSCHREIBHINWEIS
        ),
        "auftrag_code": code,
        "marke_anfang": pt.MARKE_ANFANG,
        "marke_ende": pt.MARKE_ENDE,
        "marke_uebung": pt.MARKE_UEBUNG,
        "marke_test": pt.MARKE_TEST,
        "marke_loesung": pt.MARKE_LOESUNG,
        "kopf_trenner": pt.KOPF_TRENNER,
        "stufe": pt.STUFE.get(schwierigkeit, pt.STUFE["mittel"]),
        "kategorienblock": kategorienblock(
            list(parameter.get("kategorien", [])), liste,
            list(parameter.get("sondierung", [])), sammlung,
        ),
    }
    werte.update({k: v for k, v in parameter.items()
                  if k not in ("kategorien", "sondierung")})

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


# ---------------------------------------------------------------------------
# Fehleranalyse durch das Sprachmodell
# ---------------------------------------------------------------------------
# Der mechanische Abgleich (rstrainer.diffing) sieht, DASS ein Wort abweicht,
# und rät die Kategorie aus dem Buchstabenbild. Das Modell ordnet inhaltlich
# zu und darf für alles, was die OLFA-Liste nicht abdeckt – vor allem
# Grammatik –, eigene Fehlerarten benennen. Beide Wege enden in derselben
# Bestätigungsliste, damit die Freigabe-Disziplin gleich bleibt.

def _olfa_zeilen(liste: Kategorienliste) -> str:
    zeilen = []
    for k in liste.waehlbar:
        zeile = f"{k.nr} = {k.name}. {k.kurzbeschreibung}"
        if k.beispiel and k.beispiel != "-":
            zeile += f" Beispiel: {k.beispiel}"
        zeilen.append(zeile)
    return "\n".join(zeilen)


def _bekannte_arten(sammlung: Sammlung) -> str:
    if not len(sammlung):
        return "(noch keine – du legst die ersten selbst an)"
    return "\n".join(
        f"{a.id} = {a.label}" + (f". {a.beschreibung}" if a.beschreibung else "")
        for a in sammlung
    )


def analyse_prompt_bauen(schuelertext: str, originaltext: str = "",
                         liste: Kategorienliste | None = None,
                         sammlung: Sammlung | None = None) -> str:
    """Baut den Analyse-Prompt – mit Vorlage (Diktat) oder ohne (freier Text).

    Der Unterschied ist nicht kosmetisch: Beim Diktat ist objektiv bestimmt,
    was falsch ist – alles, was von der Vorlage abweicht. Beim freien Text
    muss das Modell selbst urteilen, und die Versuchung, Stil anzustreichen,
    ist gross. Deshalb steht dort die ausdrückliche Warnung davor.
    """
    from . import olfa as olfa_modul
    from . import taxonomie as tax_modul

    liste = liste if liste is not None else olfa_modul.laden()
    sammlung = sammlung if sammlung is not None else tax_modul.laden()

    kopf = pt.ANALYSE_KOPF.format(
        olfa_liste=_olfa_zeilen(liste),
        schweiz_regel=pt.SCHWEIZ_REGEL,
        bekannte_arten=_bekannte_arten(sammlung),
        oberbegriffe=", ".join(f"`{o}`" for o in OBERBEGRIFFE),
    )
    if (originaltext or "").strip():
        return pt.ANALYSE_DIKTAT.format(
            analyse_kopf=kopf, analyse_format=pt.ANALYSE_FORMAT,
            originaltext=originaltext.strip(), schuelertext=(schuelertext or "").strip(),
        )
    return pt.ANALYSE_FREITEXT.format(
        analyse_kopf=kopf, analyse_format=pt.ANALYSE_FORMAT,
        schuelertext=(schuelertext or "").strip(),
    )


@dataclass
class Analysezeile:
    """Ein vom Modell gemeldeter Fehler, bereits auf eine Kennung gebracht."""

    wort_original: str = ""
    wort_schueler: str = ""
    begruendung: str = ""
    kategorie_nr: str = "37"
    #: Gesetzt, wenn diese Zeile eine in diesem Durchlauf neu benannte Art trägt.
    neue_art: str | None = None


@dataclass
class NeueArt:
    """Vorschlag des Modells für eine noch nicht angelegte Fehlerart."""

    id: str
    pfad: tuple[str, ...]
    beschreibung: str = ""
    anzahl: int = 0


@dataclass
class Analyseergebnis:
    zeilen: list[Analysezeile] = field(default_factory=list)
    neue_arten: list[NeueArt] = field(default_factory=list)
    fehler: str | None = None


def _json_ausschneiden(roh: str, auf: str, zu: str) -> str | None:
    """Schneidet Code-Zaun und Begleittext weg. Das Modell hält sich meistens
    an «nur JSON» – aber eben nur meistens."""
    text = str(roh or "").strip()
    zaun = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if zaun:
        text = zaun.group(1).strip()
    von, bis = text.find(auf), text.rfind(zu)
    if von == -1 or bis <= von:
        return None
    return text[von:bis + 1]


def analyse_lesen(roh: Any, liste: Kategorienliste | None = None,
                  sammlung: Sammlung | None = None) -> Analyseergebnis:
    """Wertet die JSON-Antwort des Modells aus.

    Neue Arten werden hier **nicht** gespeichert, sondern nur vorgeschlagen –
    angelegt werden sie erst mit dem Freigeben der Fehlerliste, damit ein
    verworfener Abgleich die Sammlung nicht verschmutzt.
    """
    from . import olfa as olfa_modul
    from . import taxonomie as tax_modul

    liste = liste if liste is not None else olfa_modul.laden()
    sammlung = sammlung if sammlung is not None else tax_modul.laden()

    daten = roh
    if not isinstance(daten, list):
        ausschnitt = _json_ausschneiden(daten, "[", "]")
        if ausschnitt is None:
            return Analyseergebnis(fehler="Die Antwort enthielt keine Fehlerliste.")
        try:
            daten = json.loads(ausschnitt)
        except json.JSONDecodeError:
            return Analyseergebnis(fehler="Die Antwort war kein gültiges JSON.")
    if not isinstance(daten, list):
        return Analyseergebnis(fehler="Unerwartetes Format.")

    ergebnis = Analyseergebnis()
    for eintrag in daten:
        if not isinstance(eintrag, dict):
            continue
        zeile = Analysezeile(
            wort_original=str(eintrag.get("richtig") or "").strip(),
            wort_schueler=str(eintrag.get("geschrieben") or "").strip(),
            begruendung=str(eintrag.get("begruendung") or "").strip(),
        )
        typ = str(eintrag.get("typ") or "").lower()
        pfad = [str(x).strip() for x in (eintrag.get("pfad") or [])
                if str(x).strip()] if isinstance(eintrag.get("pfad"), list) else []

        if typ == "bekannt" and sammlung.get(str(eintrag.get("kategorie") or "")):
            zeile.kategorie_nr = str(eintrag["kategorie"])
        elif typ == "neu" and len(pfad) >= 2:
            # Erst begradigen, dann vergleichen – sonst gilt «grammatik > kasus»
            # als etwas anderes als «Grammatik › Kasus».
            sauber = pfad_normalisieren(pfad)
            vorhanden = sammlung.nach_pfad(sauber)
            if vorhanden is not None:
                zeile.kategorie_nr = vorhanden.id
            else:
                schluessel = pfad_schluessel(sauber)
                vorschlag = next(
                    (n for n in ergebnis.neue_arten
                     if pfad_schluessel(n.pfad) == schluessel), None)
                if vorschlag is None:
                    vorschlag = NeueArt(
                        id=kennung(), pfad=sauber,
                        beschreibung=str(eintrag.get("beschreibung") or "").strip())
                    ergebnis.neue_arten.append(vorschlag)
                vorschlag.anzahl += 1
                zeile.kategorie_nr = vorschlag.id
                zeile.neue_art = vorschlag.id
        else:
            nr = str(eintrag.get("kategorie") or "").strip().rjust(2, "0")[:2]
            treffer = liste.get(nr)
            zeile.kategorie_nr = nr if (treffer is not None and not treffer.gesperrt) else "37"
        ergebnis.zeilen.append(zeile)
    return ergebnis


def analyse_uebernehmen(ergebnis: Analyseergebnis, sammlung: Sammlung) -> list:
    """Legt die vorgeschlagenen neuen Arten in der Sammlung an.

    Die Kennung aus dem Vorschlag bleibt erhalten, damit die bereits
    zugeordneten Zeilen weiterhin passen. Läuft der Pfad inzwischen auf eine
    bestehende Art, gewinnt diese – dann werden die Zeilen umgehängt.
    """
    umgehaengt: dict[str, str] = {}
    angelegt = []
    for vorschlag in ergebnis.neue_arten:
        vorhanden = sammlung.nach_pfad(vorschlag.pfad)
        if vorhanden is not None:
            umgehaengt[vorschlag.id] = vorhanden.id
            continue
        art = sammlung.anlegen(vorschlag.pfad, vorschlag.beschreibung)
        art.id = vorschlag.id
        angelegt.append(art)
    for zeile in ergebnis.zeilen:
        if zeile.kategorie_nr in umgehaengt:
            zeile.kategorie_nr = umgehaengt[zeile.kategorie_nr]
            zeile.neue_art = None
    return angelegt


def analyse_zu_abweichungen(zeilen: list[Analysezeile], bezugstext: str,
                            liste: Kategorienliste | None = None) -> list[dict]:
    """Überführt die Modellzeilen in dieselbe Bestätigungsliste wie der Abgleich."""
    from . import olfa as olfa_modul

    liste = liste if liste is not None else olfa_modul.laden()
    worte = woerter(bezugstext)

    def suche(begriff: str) -> int:
        if not begriff:
            return -1
        erstes = woerter(begriff)
        if not erstes:
            return -1
        wort = erstes[0]
        if wort in worte:
            return worte.index(wort)
        klein = wort.lower()
        return next((i for i, w in enumerate(worte) if w.lower() == klein), -1)

    treffer = []
    for z in zeilen:
        # Beim Diktat ist der Bezugstext die Vorlage (dort steht die richtige
        # Form), beim freien Text der Text des Kindes (dort steht die falsche).
        # Deshalb beide versuchen.
        i = suche(z.wort_schueler)
        if i == -1:
            i = suche(z.wort_original)
        marker: tuple[str, ...] = ()
        if z.wort_original and z.wort_schueler and " " not in z.wort_original:
            marker = marker_bestimmen(z.wort_original, z.wort_schueler)
        treffer.append({
            "art": "ersetzt" if z.wort_schueler else "fehlt",
            "wort_original": z.wort_original,
            "wort_schueler": z.wort_schueler,
            "position": i,
            "kontext": satz_kontext(worte, i) if i >= 0 else "",
            "marker": marker,
            "vorschlaege": kategorie_vorschlaege(marker, liste),
            "vorgabe": z.kategorie_nr,
            "begruendung": z.begruendung,
            "neue_art": z.neue_art,
            "quelle": "modell",
            "darstellung": (f"{z.wort_original} → {z.wort_schueler}"
                            if z.wort_schueler else f"{z.wort_original} → (fehlt)"),
        })
    return treffer


# ---------------------------------------------------------------------------
# Aufräumen der gelernten Fehlerarten
# ---------------------------------------------------------------------------
# Weil die Arten ohne Rückfrage angelegt werden, wächst die Sammlung. Das
# Modell, das sie benannt hat, kann sie auch wieder ordnen. Angewendet wird
# erst nach Bestätigung – anders als beim Anlegen ist ein Fehlgriff hier
# teuer, weil er bestehende Fehlerdaten umhängt.

def aufraeum_prompt_bauen(sammlung: Sammlung) -> str:
    liste = "\n".join(
        f"{a.id} = {a.label}" + (f" — {a.beschreibung}" if a.beschreibung else "")
        for a in sammlung
    )
    return pt.AUFRAEUMEN.format(sammlung=liste, oberbegriffe=", ".join(OBERBEGRIFFE))


@dataclass
class Aufraeumplan:
    zusammenlegen: list[dict] = field(default_factory=list)
    umbenennen: list[dict] = field(default_factory=list)
    fehler: str | None = None

    @property
    def ist_leer(self) -> bool:
        return not self.zusammenlegen and not self.umbenennen


def aufraeum_lesen(roh: Any, sammlung: Sammlung) -> Aufraeumplan:
    """Liest den Aufräumvorschlag und wirft weg, was nicht anwendbar ist."""
    daten = roh
    if not isinstance(daten, dict):
        ausschnitt = _json_ausschneiden(daten, "{", "}")
        if ausschnitt is None:
            return Aufraeumplan(fehler="Keine Antwort erkannt.")
        try:
            daten = json.loads(ausschnitt)
        except json.JSONDecodeError:
            return Aufraeumplan(fehler="Die Antwort war kein gültiges JSON.")
    if not isinstance(daten, dict):
        return Aufraeumplan(fehler="Unerwartetes Format.")

    plan = Aufraeumplan()
    for x in daten.get("zusammenlegen") or []:
        if not isinstance(x, dict):
            continue
        von, nach = str(x.get("von") or ""), str(x.get("nach") or "")
        if von == nach or not sammlung.get(von) or not sammlung.get(nach):
            continue
        plan.zusammenlegen.append({"von": von, "nach": nach,
                                   "warum": str(x.get("warum") or "").strip(),
                                   "anwenden": True})
    for x in daten.get("umbenennen") or []:
        if not isinstance(x, dict):
            continue
        art = sammlung.get(str(x.get("id") or ""))
        pfad = x.get("pfad")
        if art is None or not isinstance(pfad, list) or len(pfad) < 2:
            continue
        sauber = pfad_normalisieren(pfad)
        if pfad_schluessel(sauber) == pfad_schluessel(art.pfad):
            continue
        plan.umbenennen.append({"id": art.id, "pfad": sauber,
                                "warum": str(x.get("warum") or "").strip(),
                                "anwenden": True})
    return plan
