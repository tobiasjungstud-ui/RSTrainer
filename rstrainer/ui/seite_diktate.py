"""Seite: Texte erzeugen, prüfen, freigeben und verwalten.

Zwei Wege führen zu einem auswertbaren Text:

**Diktat** – die Lehrperson gibt eine fehlerfreie Vorlage vor, das Kind
schreibt sie ab. Was von der Vorlage abweicht, ist objektiv ein Fehler.

**Freier Text** – alles, was im Unterricht sonst entsteht. Es gibt keine
Vorlage; die Beurteilung übernimmt das Sprachmodell.

Der Ablauf beim generierten Diktat ist bewusst vierstufig und lässt sich
nicht abkürzen:

1. Parameter wählen → **Prompt generieren**
2. Prompt im Chat verwenden → **Ergebnis einfügen**
3. App zeigt Vorschau + Plausibilitätsprüfungen (noch nichts gespeichert)
4. **Freigabe** durch die Lehrperson → erst jetzt Speichern
"""

from __future__ import annotations

import json
from datetime import date

import streamlit as st

from .. import analysis, auftraege, db, validation
from ..kategorien import schwerpunkte
from . import gemeinsam as g

TEXTSORTEN = ["Erzählung", "Bericht", "Beschreibung", "Brief", "Sachtext", "Dialog"]
SCHWIERIGKEITEN = {
    "leicht": "leicht — 7. Klasse",
    "mittel": "mittel — 8. Klasse",
    "anspruchsvoll": "anspruchsvoll — 9. Klasse",
}


def zeichnen(con, schueler) -> None:
    st.header("Texte")
    reiter_neu, reiter_manuell, reiter_frei, reiter_archiv = st.tabs(
        ["🪄 Diktat über Chat-Prompt", "✍️ Diktat von Hand",
         "📝 Freier Text", "📚 Archiv"]
    )
    with reiter_neu:
        _prompt_ablauf(con, schueler)
    with reiter_manuell:
        _manuell(con, schueler)
    with reiter_frei:
        _freier_text(con, schueler)
    with reiter_archiv:
        _archiv(con, schueler)


# ---------------------------------------------------------------------------
# Kategorienvorschlag: Regler zwischen Klassikern und Sondierung
# ---------------------------------------------------------------------------

def _mischung(con, schueler, anzahl: int, anteil: float) -> analysis.Mischung:
    """Vorschlag aus bekannten Schwerpunkten und unerforschten Kategorien."""
    diktate = db.diktat_liste(con, schueler["id"], textart="geschrieben")
    punkte = [
        analysis.Diktatpunkt(d["id"], d["datum"], d["titel"], d["wortzahl"],
                             g.json_liste(d["ziel_kategorien"]))
        for d in diktate
    ]
    fehler = [dict(f) for f in db.fehler_liste(con, schueler["id"], textart="geschrieben")]
    return analysis.kategorien_mischen(punkte, fehler, g.register(), anzahl, anteil)


def _regler(con, schueler) -> tuple[list[str], list[str]]:
    """Regler und Anzahl – zusammen ergeben sie den Kategorienvorschlag.

    Bewusst ausserhalb des Formulars: Ein ``st.form`` überträgt seine Werte
    erst beim Absenden, der Vorschlag würde also erst nach dem Abschicken
    umspringen. Genau dann ist es zu spät, ihn noch von Hand anzupassen.
    """
    st.markdown("**Ausrichtung des Diktats**")
    spalte_a, spalte_b = st.columns([3, 1])
    with spalte_a:
        anteil = st.slider(
            "Alte Klassiker  ←→  Neues prüfen", 0, 100, 25, step=25,
            format="%d %% Sondierung", key="diktat_mix",
            help="Links: gezielt üben, was nicht sitzt. Rechts: schauen, wo es "
                 "sonst noch hakt.",
        )
    with spalte_b:
        anzahl = st.number_input("Zielkategorien", 1, 8, 4, key="diktat_anzahl")

    mischung = _mischung(con, schueler, int(anzahl), anteil / 100.0)
    st.caption(
        f"{len(mischung.klassiker)}× bekannter Schwerpunkt, "
        f"{len(mischung.sondierung)}× Sondierung. "
        "Der Regler setzt die Auswahl – anpassen können Sie sie unten jederzeit."
    )
    return mischung.alle, mischung.sondierung


def _prompt_ablauf(con, schueler) -> None:
    reg = g.register()

    st.subheader("Schritt 1 · Parameter wählen und Prompt erzeugen")
    vorschlag, sondierung = _regler(con, schueler)

    with st.form("diktat_prompt"):
        spalte_a, spalte_b = st.columns(2)
        with spalte_a:
            schwierigkeit = st.selectbox(
                "Schwierigkeitsgrad", list(SCHWIERIGKEITEN), index=1,
                format_func=lambda s: SCHWIERIGKEITEN[s],
                help="Bestimmt zugleich die Zielstufe im Prompt.",
            )
            wortzahl = st.number_input("Umfang in Wörtern", 30, 400, 90, step=10)
            textsorte = st.selectbox("Textsorte", TEXTSORTEN)
        with spalte_b:
            treffer = st.number_input(
                "Zielwörter je Kategorie", 2, 12, 4,
                help="So viele Wörter je Kategorie soll der Text mindestens enthalten.",
            )
            thema = st.text_input("Thema", placeholder="z. B. Ein Tag im Wald")

        kategorien = g.kategorien_auswahl(
            reg, "Zielkategorien", vorauswahl=vorschlag,
            schluessel="diktat_kategorien",
        )
        if st.form_submit_button("Prompt generieren", type="primary"):
            if not kategorien:
                st.error("Bitte mindestens eine Zielkategorie wählen.")
            elif not thema.strip():
                st.error("Bitte ein Thema angeben.")
            else:
                parameter = {
                    "kategorien": kategorien,
                    "sondierung": [nr for nr in sondierung if nr in kategorien],
                    "wortzahl": int(wortzahl),
                    "textsorte": textsorte,
                    "schwierigkeit": schwierigkeit,
                    "thema": thema,
                    "treffer_pro_kategorie": int(treffer),
                }
                try:
                    code, prompt = auftraege.prompt_bauen(
                        "diktat", parameter, reg.liste, sammlung=reg.sammlung,
                    )
                except KeyError as fehler:
                    st.error(str(fehler))
                    return
                db.auftrag_anlegen(con, schueler["id"], code, "diktat", parameter, prompt)
                st.session_state["diktat_auftrag"] = code
                st.rerun()

    code = st.session_state.get("diktat_auftrag")
    if not code:
        return
    auftrag = db.auftrag_holen(con, code)
    if auftrag is None or auftrag["schueler_id"] != schueler["id"]:
        st.session_state.pop("diktat_auftrag", None)
        return

    st.divider()
    st.subheader("Schritt 2 · Prompt in den Chat kopieren")
    g.prompt_anzeigen(auftrag["prompt_text"], code)

    st.divider()
    st.subheader("Schritt 3 · Ergebnis aus dem Chat einfügen")
    eingefuegt = st.text_area(
        "Antwort aus dem Chat", height=220, key="diktat_eingefuegt",
        placeholder="Die komplette Antwort hierher kopieren – "
                    "inklusive der ===RSTRAINER-…===-Zeilen.",
    )
    # Bewusst NICHT über "disabled" gesperrt: Streamlit übermittelt den Inhalt
    # eines Textfeldes erst, wenn es den Fokus verliert. Ein gesperrter Knopf
    # wirkt dann wie ein Fehler, obwohl nur noch ein Klick daneben fehlt.
    if st.button("Ergebnis auswerten"):
        if not (eingefuegt or "").strip():
            st.warning(
                "Das Eingabefeld ist noch leer. Bitte die Antwort einfügen und "
                "einmal neben das Feld klicken."
            )
        else:
            st.session_state["diktat_ergebnis"] = auftraege.ergebnis_lesen(
                eingefuegt, erwarteter_code=code, erwarteter_typ="diktat"
            )
            st.rerun()

    ergebnis = st.session_state.get("diktat_ergebnis")
    if ergebnis is not None:
        _vorschau_und_freigabe(con, schueler, auftrag, ergebnis)


# ---------------------------------------------------------------------------
# Schritt 4: Vorschau, Prüfungen, Freigabe
# ---------------------------------------------------------------------------

def _vorschau_und_freigabe(con, schueler, auftrag, ergebnis) -> None:
    reg = g.register()
    parameter = json.loads(auftrag["parameter"] or "{}")
    kategorien = [str(k) for k in parameter.get("kategorien", [])]
    soll_wortzahl = int(parameter.get("wortzahl", 0) or 0)

    st.divider()
    st.subheader("Schritt 4 · Kontrolle vor der Freigabe")
    st.info(
        "**Noch nichts gespeichert.** Der Text steht nur zur Ansicht hier. "
        "Erst mit der Freigabe unten wandert er in die Datenbank."
    )

    for hinweis in ergebnis.hinweise:
        st.warning(hinweis)

    titel = st.text_input("Titel des Diktats", value=ergebnis.titel or "Diktat")
    text = st.text_area(
        "Diktattext (hier direkt korrigierbar)", value=ergebnis.haupttext,
        height=260, key="diktat_text_pruefung",
    )
    if ergebnis.kopf.get("ZIELWOERTER"):
        st.caption(f"Vom Chat genannte Zielwörter: {ergebnis.kopf['ZIELWOERTER']}")

    st.markdown("**Automatische Plausibilitätsprüfung**")
    g.befunde_anzeigen(
        validation.diktat_pruefen(text, soll_wortzahl, kategorien, reg)
    )

    st.divider()
    st.markdown("### Freigabe")
    freigabe = st.checkbox(
        "**Geprüft und freigegeben** – ich habe den Text gelesen und er ist "
        "als Diktatgrundlage geeignet.",
        key="diktat_freigabe",
    )

    spalte_a, spalte_b = st.columns(2)
    with spalte_a:
        datum = st.date_input("Datum des Diktats", value=date.today())
    with spalte_b:
        notiz = st.text_input("Notiz", key="diktat_notiz")

    if not freigabe:
        st.caption("Zum Speichern fehlt die Freigabe oben.")

    if st.button("Als Diktat speichern", type="primary", disabled=not freigabe):
        diktat_id = db.diktat_anlegen(
            con, schueler["id"], titel, text, datum=datum.isoformat(),
            ziel_kategorien=kategorien, notiz=notiz, quelle=f"chat:{auftrag['code']}",
            freigegeben=True,
        )
        db.auftrag_status_setzen(con, auftrag["code"], auftraege.STATUS_FREIGEGEBEN,
                                 ergebnis_roh=text)
        for schluessel in ("diktat_auftrag", "diktat_ergebnis", "diktat_eingefuegt",
                           "diktat_freigabe", "diktat_notiz"):
            st.session_state.pop(schluessel, None)
        g.merken(f"Diktat «{titel}» gespeichert (Nr. {diktat_id}).")
        st.rerun()

    if st.button("Verwerfen"):
        db.auftrag_status_setzen(con, auftrag["code"], auftraege.STATUS_VERWORFEN)
        for schluessel in ("diktat_auftrag", "diktat_ergebnis", "diktat_eingefuegt"):
            st.session_state.pop(schluessel, None)
        st.rerun()


# ---------------------------------------------------------------------------
# Diktat von Hand
# ---------------------------------------------------------------------------

def _manuell(con, schueler) -> None:
    st.subheader("Diktat von Hand erfassen")
    st.caption(
        "Für Diktate aus dem Lehrmittel oder aus einer anderen Quelle. Der Text "
        "ist später die Referenz für den maschinellen Abgleich – jeder Tippfehler "
        "darin zählt dort als Schülerfehler."
    )
    reg = g.register()
    with st.form("diktat_manuell", clear_on_submit=True):
        titel = st.text_input("Titel *")
        text = st.text_area("Diktattext *", height=220)
        spalte_a, spalte_b = st.columns(2)
        with spalte_a:
            datum = st.date_input("Datum", value=date.today())
        with spalte_b:
            notiz = st.text_input("Notiz")
        kategorien = g.kategorien_auswahl(
            reg, "Zielkategorien (optional)", schluessel="manuell_kategorien"
        )
        if st.form_submit_button("Diktat speichern", type="primary"):
            if not titel.strip() or not text.strip():
                st.error("Titel und Diktattext sind Pflichtfelder.")
            else:
                db.diktat_anlegen(
                    con, schueler["id"], titel, text, datum=datum.isoformat(),
                    ziel_kategorien=kategorien, notiz=notiz, quelle="manuell",
                    freigegeben=True,
                )
                g.merken(f"Diktat «{titel}» gespeichert.")
                st.rerun()


# ---------------------------------------------------------------------------
# Freier Text
# ---------------------------------------------------------------------------

def _freier_text(con, schueler) -> None:
    st.subheader("Freien Text erfassen")
    st.caption(
        "Für alles, was im Unterricht sonst entsteht – Aufsatz, Bericht, Antwort "
        "auf eine Frage. Hier gibt es keine Vorlage: Das Sprachmodell beurteilt "
        "selbst, was falsch ist. Der mechanische Abgleich entfällt, die Fehler "
        "landen aber in derselben Auswertung wie die aus Diktaten."
    )
    with st.form("freitext", clear_on_submit=True):
        spalte_a, spalte_b = st.columns(2)
        with spalte_a:
            titel = st.text_input("Titel *", placeholder="z. B. «Aufsatz Herbstferien»")
        with spalte_b:
            datum = st.date_input("Datum", value=date.today())
        art = g.textart_wahl("texte_art")
        text = st.text_area("Text des Kindes *", height=240,
                            placeholder="Abgetippt oder eingefügt.")
        notiz = st.text_input("Notiz", placeholder="Auftrag, Umstände, Besonderes …")
        if st.form_submit_button("Text speichern", type="primary"):
            if not titel.strip() or not text.strip():
                st.error("Titel und Text sind Pflichtfelder.")
            else:
                neue_id = db.diktat_anlegen(
                    con, schueler["id"], titel, "", datum=datum.isoformat(),
                    notiz=notiz, quelle=art, freigegeben=True,
                    art=art, schuelertext=text,
                )
                g.merken(
                    f"Freier Text «{titel}» gespeichert (Nr. {neue_id}). "
                    "Unter «Fehlererfassung» kann er jetzt ausgewertet werden."
                )
                st.rerun()


# ---------------------------------------------------------------------------
# Archiv
# ---------------------------------------------------------------------------

def _schwerpunkt_zeile(fehler: list[dict]) -> str:
    """Was in diesem Text auffiel – nicht, was vorher geplant war.

    Die Zielkategorien standen vor dem Schreiben fest und sagen nichts darüber
    aus, was das Kind tatsächlich falsch gemacht hat.
    """
    if not fehler:
        return "Noch keine Fehler erfasst."
    reg = g.register()
    punkte = schwerpunkte(fehler)
    teile = [f"{reg.kurz(nr)} ({anzahl}×)" for nr, anzahl in punkte.liste]
    text = "Schwerpunkte: " + ", ".join(teile)
    if punkte.rest:
        text += f" · {punkte.rest} weitere"
    return text + f" · {punkte.gesamt} Fehler gesamt"


def _archiv(con, schueler) -> None:
    st.subheader("Archiv")
    diktate = db.diktat_liste(con, schueler["id"])
    if not diktate:
        st.info("Noch keine Texte erfasst.")
        return

    reg = g.register()
    for diktat in reversed(diktate):
        ist_frei = diktat["art"] in db.OHNE_VORLAGE
        kategorien = g.json_liste(diktat["ziel_kategorien"])
        fehler = [dict(f) for f in db.fehler_liste(con, schueler["id"], diktat["id"])]
        with st.expander(
            f"{g.textart_symbol(diktat['art'])} {diktat['datum']} · {diktat['titel']} "
            f"({diktat['wortzahl']} Wörter)"
            + (" · diktiert (Sprachsoftware)" if diktat["art"] == "diktiert" else " · freier Text" if ist_frei else "")
        ):
            st.caption(_schwerpunkt_zeile(fehler))
            if kategorien:
                st.caption("Zielkategorien: "
                           + ", ".join(reg.label(nr) for nr in kategorien))
            if diktat["notiz"]:
                st.caption(f"Notiz: {diktat['notiz']}")
            st.caption(
                f"Quelle: {diktat['quelle']} · "
                f"Freigegeben: {diktat['freigegeben_am'] or 'nein'}"
            )
            st.text_area(
                "Text des Kindes" if ist_frei else "Originaltext",
                value=diktat["schuelertext"] if ist_frei else diktat["text_original"],
                height=160, key=f"archiv_text_{diktat['id']}", disabled=True,
            )
            if st.button("Text löschen", key=f"loesche_diktat_{diktat['id']}"):
                db.diktat_loeschen(con, diktat["id"])
                g.merken(f"«{diktat['titel']}» gelöscht.")
                st.rerun()
