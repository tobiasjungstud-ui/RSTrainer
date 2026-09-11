"""Seite: Diktate erzeugen, prüfen, freigeben und verwalten.

Der Ablauf ist bewusst vierstufig und lässt sich nicht abkürzen:

1. Parameter wählen → **Prompt generieren**
2. Prompt im Chat verwenden → **Ergebnis einfügen**
3. App zeigt Vorschau + Plausibilitätsprüfungen (noch nichts gespeichert)
4. **Freigabe** durch die Lehrperson → erst jetzt Speichern

Das Korrekturlesen des Originaltexts ist ein **eigener** Prüfschritt, weil
dieser Text später die Referenzwahrheit für den maschinellen Abgleich ist.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from .. import auftraege, db, validation
from . import gemeinsam as g

TEXTSORTEN = ["Erzählung", "Bericht", "Beschreibung", "Brief", "Sachtext", "Dialog"]
SCHWIERIGKEITEN = ["leicht", "mittel", "anspruchsvoll"]


def zeichnen(con, schueler) -> None:
    st.header("Diktate")
    reiter_neu, reiter_manuell, reiter_archiv = st.tabs(
        ["🪄 Neues Diktat über Chat-Prompt", "✍️ Diktat von Hand erfassen", "📚 Archiv"]
    )
    with reiter_neu:
        _prompt_ablauf(con, schueler)
    with reiter_manuell:
        _manuell(con, schueler)
    with reiter_archiv:
        _archiv(con, schueler)


# ---------------------------------------------------------------------------
# Schritt 1 + 2: Prompt erzeugen und Ergebnis einfügen
# ---------------------------------------------------------------------------

def _prompt_ablauf(con, schueler) -> None:
    liste = g.kategorienliste()

    st.subheader("Schritt 1 · Parameter wählen und Prompt erzeugen")
    with st.form("diktat_prompt"):
        spalte_a, spalte_b = st.columns(2)
        with spalte_a:
            klassenstufe = st.text_input(
                "Klassenstufe / Alter",
                value=f"Klasse {schueler['klasse']}" if schueler["klasse"] else "5. Klasse",
            )
            wortzahl = st.number_input("Umfang in Wörtern", 30, 400, 90, step=10)
            textsorte = st.selectbox("Textsorte", TEXTSORTEN)
        with spalte_b:
            schwierigkeit = st.selectbox("Schwierigkeitsgrad", SCHWIERIGKEITEN, index=1)
            treffer = st.number_input(
                "Zielwörter je Kategorie", 2, 12, 4,
                help="So viele Wörter je Kategorie soll der Text mindestens enthalten.",
            )
            thema = st.text_input("Thema", placeholder="z. B. Ein Tag im Wald")

        kategorien = g.kategorien_auswahl(
            liste, "Zielkategorien (OLFA)", schluessel="diktat_kategorien"
        )
        if st.form_submit_button("Prompt generieren", type="primary"):
            if not kategorien:
                st.error("Bitte mindestens eine Zielkategorie wählen.")
            elif not thema.strip():
                st.error("Bitte ein Thema angeben.")
            else:
                parameter = {
                    "kategorien": kategorien,
                    "klassenstufe": klassenstufe,
                    "wortzahl": int(wortzahl),
                    "textsorte": textsorte,
                    "schwierigkeit": schwierigkeit,
                    "thema": thema,
                    "treffer_pro_kategorie": int(treffer),
                }
                try:
                    code, prompt = auftraege.prompt_bauen(
                        "diktat", parameter, liste,
                        rechtschreibvariante=g.rechtschreibvariante(con),
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
# Schritt 3 + 4: Vorschau, Prüfungen, Freigabe
# ---------------------------------------------------------------------------

def _vorschau_und_freigabe(con, schueler, auftrag, ergebnis) -> None:
    import json

    liste = g.kategorienliste()
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
        validation.diktat_pruefen(text, soll_wortzahl, kategorien, liste)
    )

    st.divider()
    st.markdown("### Freigabe")
    freigabe = st.checkbox(
        "**Geprüft und freigegeben** – ich habe den Text gelesen und er ist "
        "als Diktatgrundlage geeignet.",
        key="diktat_freigabe",
    )
    st.markdown(
        "> ⚠️ **Eigener Prüfschritt – Korrekturlesen des Originaltexts**  \n"
        "> Dieser Text ist später die **Referenzwahrheit** für den automatischen "
        "Abgleich mit dem Schülertext. Jeder Tippfehler darin wird dann der "
        "Schülerin oder dem Schüler als Fehler angerechnet."
    )
    korrektur = st.checkbox(
        "**Wort für Wort korrekturgelesen** – Rechtschreibung und Grammatik "
        "des Originaltexts stimmen.",
        key="diktat_korrektur",
    )

    spalte_a, spalte_b = st.columns(2)
    with spalte_a:
        datum = st.date_input("Datum des Diktats", value=date.today())
    with spalte_b:
        notiz = st.text_input("Notiz", key="diktat_notiz")

    if not freigabe:
        st.caption("Zum Speichern fehlt die Freigabe oben.")
    if freigabe and not korrektur:
        st.warning(
            "Sie können jetzt speichern, aber das Korrekturlesen ist noch offen. "
            "Der diff-gestützte Fehlerabgleich bleibt gesperrt, bis Sie diesen "
            "Schritt im Archiv nachholen."
        )

    if st.button("Als Diktat speichern", type="primary", disabled=not freigabe):
        diktat_id = db.diktat_anlegen(
            con, schueler["id"], titel, text, datum=datum.isoformat(),
            ziel_kategorien=kategorien, notiz=notiz, quelle=f"chat:{auftrag['code']}",
            freigegeben=True, korrektur_gelesen=korrektur,
        )
        db.auftrag_status_setzen(con, auftrag["code"], auftraege.STATUS_FREIGEGEBEN,
                                 ergebnis_roh=text)
        for schluessel in ("diktat_auftrag", "diktat_ergebnis", "diktat_eingefuegt",
                           "diktat_freigabe", "diktat_korrektur", "diktat_notiz"):
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
        "Für Diktate aus dem Lehrmittel oder aus einer anderen Quelle. Auch hier "
        "gilt: Der Text ist später die Referenz für den Abgleich."
    )
    liste = g.kategorienliste()
    with st.form("diktat_manuell", clear_on_submit=True):
        titel = st.text_input("Titel *")
        text = st.text_area("Diktattext *", height=220)
        spalte_a, spalte_b = st.columns(2)
        with spalte_a:
            datum = st.date_input("Datum", value=date.today())
        with spalte_b:
            notiz = st.text_input("Notiz")
        kategorien = g.kategorien_auswahl(
            liste, "Zielkategorien (optional)", schluessel="manuell_kategorien"
        )
        korrektur = st.checkbox(
            "**Wort für Wort korrekturgelesen** – der Text ist fehlerfrei."
        )
        if st.form_submit_button("Diktat speichern", type="primary"):
            if not titel.strip() or not text.strip():
                st.error("Titel und Diktattext sind Pflichtfelder.")
            else:
                db.diktat_anlegen(
                    con, schueler["id"], titel, text, datum=datum.isoformat(),
                    ziel_kategorien=kategorien, notiz=notiz, quelle="manuell",
                    freigegeben=True, korrektur_gelesen=korrektur,
                )
                g.merken(f"Diktat «{titel}» gespeichert.")
                st.rerun()


# ---------------------------------------------------------------------------
# Archiv
# ---------------------------------------------------------------------------

def _archiv(con, schueler) -> None:
    st.subheader("Archiv")
    diktate = db.diktat_liste(con, schueler["id"])
    if not diktate:
        st.info("Noch keine Diktate erfasst.")
        return

    liste = g.kategorienliste()
    for diktat in reversed(diktate):
        kategorien = g.json_liste(diktat["ziel_kategorien"])
        marke = "✅" if diktat["korrektur_gelesen"] else "⚠️"
        with st.expander(
            f"{marke} {diktat['datum']} · {diktat['titel']} "
            f"({diktat['wortzahl']} Wörter)"
        ):
            if kategorien:
                st.caption("Zielkategorien: "
                           + ", ".join(liste.label(nr) for nr in kategorien))
            if diktat["notiz"]:
                st.caption(f"Notiz: {diktat['notiz']}")
            st.caption(
                f"Quelle: {diktat['quelle']} · "
                f"Freigegeben: {diktat['freigegeben_am'] or 'nein'} · "
                f"Korrekturgelesen: {diktat['korrektur_gelesen_am'] or 'nein'}"
            )
            st.text_area("Originaltext", value=diktat["text_original"], height=160,
                         key=f"archiv_text_{diktat['id']}", disabled=True)

            if not diktat["korrektur_gelesen"]:
                st.warning(
                    "Das Korrekturlesen steht noch aus. Solange bleibt der "
                    "diff-gestützte Abgleich für dieses Diktat gesperrt."
                )
                if st.button("Jetzt als korrekturgelesen bestätigen",
                             key=f"korrektur_{diktat['id']}"):
                    db.diktat_korrektur_bestaetigen(con, diktat["id"])
                    st.rerun()

            anzahl = len(db.fehler_liste(con, schueler["id"], diktat["id"]))
            st.caption(f"Erfasste Fehler zu diesem Diktat: {anzahl}")
            if st.button("Diktat löschen", key=f"loesche_diktat_{diktat['id']}"):
                db.diktat_loeschen(con, diktat["id"])
                st.rerun()
