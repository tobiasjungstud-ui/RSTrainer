"""Seite: Übungsblätter und Mini-Tests.

Ablauf wie beim Diktat: Empfehlung ansehen → Themen festlegen → Prompt →
Ergebnis einfügen → Prüfungen → Freigabe mit zwei ausdrücklichen
Rückfragen (Lösungen sichtbar? Niveau passend?) → Docx-Export.
"""

from __future__ import annotations

import json
from datetime import date

import streamlit as st

from .. import analysis, auftraege, config, db, docx_export, validation
from . import gemeinsam as g


def zeichnen(con, schueler) -> None:
    st.header("Übungsblätter und Mini-Tests")
    reiter_neu, reiter_archiv = st.tabs(["🪄 Neues Blatt", "📚 Archiv & Export"])
    with reiter_neu:
        _neues_blatt(con, schueler)
    with reiter_archiv:
        _archiv(con, schueler)


# ---------------------------------------------------------------------------
# Empfehlung + Prompt
# ---------------------------------------------------------------------------

def _empfehlungen_holen(con, schueler) -> list[analysis.Empfehlung]:
    diktate = db.diktat_liste(con, schueler["id"])
    punkte = [
        analysis.Diktatpunkt(d["id"], d["datum"], d["titel"], d["wortzahl"])
        for d in diktate
    ]
    fehler = [dict(f) for f in db.fehler_liste(con, schueler["id"])]
    return analysis.empfehlungen(punkte, fehler)


def _neues_blatt(con, schueler) -> None:
    liste = g.kategorienliste()

    st.subheader("Schritt 1 · Förderschwerpunkte festlegen")
    vorschlaege = _empfehlungen_holen(con, schueler)
    if vorschlaege:
        st.markdown("**Vorschlag des Tools**")
        for e in vorschlaege:
            with st.container(border=True):
                st.markdown(
                    f"**{liste.label(e.kategorie_nr)}** {e.trend.symbol} "
                    f"*{e.trend.text}* · Priorität {e.punktzahl}"
                )
                st.caption(e.begruendung)
                st.caption(
                    f"Zeitgewichtete Rate {e.details['gewichtete_rate']} Fehler/100 "
                    f"Wörter · Trendfaktor {e.details['trendfaktor']} · "
                    f"Verbreitung {e.details['verbreitung']}"
                )
        vorauswahl = [e.kategorie_nr for e in vorschlaege]
    else:
        st.info(
            "Noch keine Empfehlung möglich – dafür braucht es erfasste Fehler. "
            "Sie können die Themen unten trotzdem selbst wählen."
        )
        vorauswahl = []

    st.caption("Der Vorschlag lässt sich jederzeit übersteuern.")

    with st.form("blatt_prompt"):
        kategorien = g.kategorien_auswahl(
            liste, "Förderschwerpunkte (1–3)", vorauswahl=vorauswahl,
            schluessel="blatt_kategorien", hoechstens=3,
        )
        spalte_a, spalte_b = st.columns(2)
        with spalte_a:
            klassenstufe = st.text_input(
                "Klassenstufe / Alter",
                value=f"Klasse {schueler['klasse']}" if schueler["klasse"] else "5. Klasse",
            )
            aufgaben = st.number_input("Aufgaben je Schwerpunkt", 2, 8, 3)
        with spalte_b:
            bearbeitungszeit = st.text_input("Bearbeitungszeit", value="20 Minuten")
            test_aufgaben = st.number_input("Aufgaben im Mini-Test", 3, 15, 6)

        if st.form_submit_button("Prompt generieren", type="primary"):
            if not kategorien:
                st.error("Bitte mindestens einen Förderschwerpunkt wählen.")
            else:
                parameter = {
                    "kategorien": kategorien,
                    "klassenstufe": klassenstufe,
                    "bearbeitungszeit": bearbeitungszeit,
                    "aufgaben_pro_kategorie": int(aufgaben),
                    "test_aufgaben": int(test_aufgaben),
                }
                try:
                    code, prompt = auftraege.prompt_bauen(
                        "uebungsblatt", parameter, liste,
                        rechtschreibvariante=g.rechtschreibvariante(con),
                    )
                except KeyError as fehler:
                    st.error(str(fehler))
                    return
                db.auftrag_anlegen(con, schueler["id"], code, "uebungsblatt",
                                   parameter, prompt)
                st.session_state["blatt_auftrag"] = code
                st.rerun()

    code = st.session_state.get("blatt_auftrag")
    if not code:
        return
    auftrag = db.auftrag_holen(con, code)
    if auftrag is None or auftrag["schueler_id"] != schueler["id"]:
        st.session_state.pop("blatt_auftrag", None)
        return

    st.divider()
    st.subheader("Schritt 2 · Prompt in den Chat kopieren")
    g.prompt_anzeigen(auftrag["prompt_text"], code)

    st.divider()
    st.subheader("Schritt 3 · Ergebnis einfügen")
    eingefuegt = st.text_area(
        "Antwort aus dem Chat", height=220, key="blatt_eingefuegt",
        placeholder="Komplette Antwort hierher kopieren.",
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
            st.session_state["blatt_ergebnis"] = auftraege.ergebnis_lesen(
                eingefuegt, erwarteter_code=code, erwarteter_typ="uebungsblatt"
            )
            st.rerun()

    ergebnis = st.session_state.get("blatt_ergebnis")
    if ergebnis is not None:
        _vorschau_und_freigabe(con, schueler, auftrag, ergebnis)


# ---------------------------------------------------------------------------
# Prüfung + Freigabe
# ---------------------------------------------------------------------------

def _vorschau_und_freigabe(con, schueler, auftrag, ergebnis) -> None:
    liste = g.kategorienliste()
    parameter = json.loads(auftrag["parameter"] or "{}")
    kategorien = [str(k) for k in parameter.get("kategorien", [])]

    st.divider()
    st.subheader("Schritt 4 · Kontrolle vor der Freigabe")
    st.info("**Noch nichts gespeichert.** Erst die Freigabe unten speichert das Blatt.")

    for hinweis in ergebnis.hinweise:
        st.warning(hinweis)

    titel = st.text_input("Titel des Blattes", value=ergebnis.titel or "Übungsblatt")
    uebung = st.text_area("Übungsteil (Vorderseite)", value=ergebnis.uebungsteil,
                          height=240, key="blatt_uebung")
    test = st.text_area("Mini-Test (Rückseite)", value=ergebnis.testteil,
                        height=200, key="blatt_test")
    loesungen = st.text_area("Lösungen (separates Blatt)", value=ergebnis.loesungen,
                             height=140, key="blatt_loesungen")

    st.markdown("**Automatische Plausibilitätsprüfung**")
    g.befunde_anzeigen(
        validation.blatt_pruefen(uebung, test, loesungen, kategorien, liste)
    )

    st.divider()
    st.markdown("### Freigabe")
    st.markdown(
        "Bitte beide Rückfragen bewusst beantworten – die App kann das nicht "
        "für Sie beurteilen."
    )
    pruef_loesungen = st.checkbox(
        "**Keine Lösungen auf den Aufgabenseiten** – ich habe Vorder- und "
        "Rückseite durchgesehen; es sind keine Lösungen sichtbar.",
        key="blatt_pruef_loesungen",
    )
    pruef_niveau = st.checkbox(
        "**Schwierigkeitsgrad passt zur Altersstufe** – ich habe die Aufgaben "
        "gelesen und halte sie für angemessen.",
        key="blatt_pruef_niveau",
    )
    freigabe = st.checkbox(
        "**Geprüft und freigegeben** – das Blatt kann so in den Unterricht.",
        key="blatt_freigabe",
    )
    datum = st.date_input("Datum", value=date.today(), key="blatt_datum")

    alles_bestaetigt = pruef_loesungen and pruef_niveau and freigabe
    if not alles_bestaetigt:
        st.caption("Zum Speichern müssen alle drei Häkchen gesetzt sein.")

    if st.button("Blatt speichern", type="primary", disabled=not alles_bestaetigt):
        blatt_id = db.blatt_anlegen(
            con, schueler["id"], titel, kategorien, uebung, test, loesungen,
            datum=datum.isoformat(),
        )
        db.blatt_freigeben(con, blatt_id, pruef_loesungen, pruef_niveau)
        db.auftrag_status_setzen(con, auftrag["code"], auftraege.STATUS_FREIGEGEBEN,
                                 ergebnis_roh=uebung)
        for schluessel in ("blatt_auftrag", "blatt_ergebnis", "blatt_eingefuegt",
                           "blatt_freigabe", "blatt_pruef_loesungen",
                           "blatt_pruef_niveau"):
            st.session_state.pop(schluessel, None)
        g.merken(f"Blatt «{titel}» gespeichert (Nr. {blatt_id}).")
        st.rerun()

    if st.button("Verwerfen", key="blatt_verwerfen"):
        db.auftrag_status_setzen(con, auftrag["code"], auftraege.STATUS_VERWORFEN)
        for schluessel in ("blatt_auftrag", "blatt_ergebnis", "blatt_eingefuegt"):
            st.session_state.pop(schluessel, None)
        st.rerun()


# ---------------------------------------------------------------------------
# Archiv + Docx
# ---------------------------------------------------------------------------

def _archiv(con, schueler) -> None:
    liste = g.kategorienliste()
    blaetter = db.blatt_liste(con, schueler["id"])
    if not blaetter:
        st.info("Noch keine Übungsblätter gespeichert.")
        return

    for blatt in blaetter:
        kategorien = g.json_liste(blatt["kategorien"])
        with st.expander(f"{blatt['datum']} · {blatt['titel']}"):
            st.caption("Förderschwerpunkte: "
                       + ", ".join(liste.label(nr) for nr in kategorien))
            st.caption(
                f"Freigegeben am {blatt['freigegeben_am'] or '–'} · "
                f"Lösungen geprüft: {'ja' if blatt['pruef_loesungen'] else 'nein'} · "
                f"Niveau geprüft: {'ja' if blatt['pruef_niveau'] else 'nein'}"
            )
            st.text_area("Übungsteil", value=blatt["inhalt_uebung"], height=140,
                         key=f"arch_ueb_{blatt['id']}", disabled=True)
            st.text_area("Mini-Test", value=blatt["inhalt_test"], height=120,
                         key=f"arch_test_{blatt['id']}", disabled=True)

            mit_loesungen = st.checkbox(
                "Lösungsblatt anhängen (Seite 3, deutlich als «nicht austeilen» markiert)",
                key=f"arch_loes_{blatt['id']}",
            )
            if st.button("Word-Datei erzeugen", type="primary",
                         key=f"arch_docx_{blatt['id']}"):
                pfad = config.EXPORT_DIR / (
                    f"Uebungsblatt_{schueler['id']}_{blatt['datum']}_{blatt['id']}.docx"
                )
                docx_export.uebungsblatt_schreiben(
                    pfad, g.anzeigename(con, schueler), blatt["titel"], kategorien,
                    liste, blatt["inhalt_uebung"], blatt["inhalt_test"],
                    blatt["loesungen"], datum=_datum_deutsch(blatt["datum"]),
                    loesungen_anhaengen=mit_loesungen,
                )
                with open(pfad, "rb") as datei:
                    st.download_button(
                        "Word-Datei herunterladen", datei.read(), file_name=pfad.name,
                        mime="application/vnd.openxmlformats-officedocument."
                             "wordprocessingml.document",
                        key=f"arch_dl_{blatt['id']}",
                    )
                g.merken(f"Erzeugt: `{pfad}`")

            if st.button("Blatt löschen", key=f"arch_del_{blatt['id']}"):
                db.blatt_loeschen(con, blatt["id"])
                st.rerun()


def _datum_deutsch(iso: str) -> str:
    try:
        return date.fromisoformat(iso).strftime("%d.%m.%Y")
    except (TypeError, ValueError):
        return iso
