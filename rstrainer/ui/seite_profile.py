"""Seite: Schülerprofile anlegen, wechseln, löschen."""

from __future__ import annotations

import streamlit as st

from .. import db
from . import gemeinsam as g


def zeichnen(con) -> None:
    st.header("Schülerprofile")

    profile = db.schueler_liste(con)

    if profile:
        st.subheader("Übersicht")
        for schueler in profile:
            u = db.schueler_uebersicht(con, schueler["id"])
            aktiv = schueler["id"] == g.aktive_schueler_id()
            with st.container(border=True):
                kopf, knopf = st.columns([5, 1])
                with kopf:
                    titel = f"**{schueler['anzeigename']}**"
                    if aktiv:
                        titel += " · ✅ ausgewählt"
                    st.markdown(titel)

                    schwerpunkt = _schwerpunkt_text(con, schueler["id"])
                    st.caption(
                        f"Texte: **{u['anzahl_diktate']}** · "
                        f"erfasste Fehler: **{u['anzahl_fehler']}** · "
                        f"zuletzt: **{u['letztes_diktat_datum'] or '–'}**"
                    )
                    st.caption(f"Aktueller Förderschwerpunkt: {schwerpunkt}")
                    if u["diktate_ohne_freigabe"]:
                        st.caption(
                            f"⚠️ {u['diktate_ohne_freigabe']} Text(e) noch ohne Freigabe."
                        )
                with knopf:
                    if not aktiv and st.button("Auswählen", key=f"waehle_{schueler['id']}"):
                        st.session_state["schueler_id"] = schueler["id"]
                        st.rerun()
    else:
        st.info("Noch keine Profile vorhanden. Legen Sie unten das erste an.")

    st.divider()
    _anlegen(con)

    if profile:
        st.divider()
        _bearbeiten(con, profile)

    g.datenschutz_fussnote()


def _schwerpunkt_text(con, schueler_id: int) -> str:
    """Kürzeste Fassung der Empfehlung für die Profilübersicht."""
    from .. import analysis

    diktate = db.diktat_liste(con, schueler_id)
    if not diktate:
        return "– (noch keine Texte)"
    punkte = [
        analysis.Diktatpunkt(d["id"], d["datum"], d["titel"], d["wortzahl"],
                             tuple(g.json_liste(d["ziel_kategorien"])))
        for d in diktate
    ]
    fehler = [dict(f) for f in db.fehler_liste(con, schueler_id)]
    vorschlaege = analysis.empfehlungen(punkte, fehler, anzahl=2)
    if not vorschlaege:
        return "– (noch keine Fehler erfasst)"
    reg = g.register()
    return " · ".join(
        f"{reg.kurz(e.kategorie_nr)} {e.trend.symbol}" for e in vorschlaege
    )


def _anlegen(con) -> None:
    st.subheader("Neues Profil anlegen")
    st.caption(
        "Hinweis zum Datenschutz: Es geht um Daten minderjähriger Schüler:innen. "
        "Empfehlung ist ein **Pseudonym oder Kürzel** als Anzeigename – dann steht "
        "auch bei einem verlorenen Laptop kein Klarname in der Datei. Der "
        "Anzeigename ist zugleich das, was auf Ausdrucken erscheint."
    )
    with st.form("profil_anlegen", clear_on_submit=True):
        name = st.text_input("Anzeigename *", placeholder="z. B. «L.B.» oder «Kind 3»")
        notiz = st.text_area("Notiz", placeholder="Förderziele, Besonderheiten …")
        if st.form_submit_button("Profil anlegen", type="primary"):
            if not name.strip():
                st.error("Bitte einen Anzeigenamen eingeben.")
            else:
                neue_id = db.schueler_anlegen(con, name, notiz)
                st.session_state["schueler_id"] = neue_id
                g.merken(f"Profil «{name}» angelegt und ausgewählt.")
                st.rerun()


def _bearbeiten(con, profile) -> None:
    st.subheader("Profil bearbeiten oder löschen")
    # Nur IDs als Optionen – sqlite3.Row ist nicht picklebar (siehe seite_fehler).
    namen = {s["id"]: s["anzeigename"] for s in profile}
    auswahl_id = st.selectbox(
        "Profil", list(namen), format_func=lambda i: namen[i],
        key="profil_bearbeiten",
    )
    auswahl = db.schueler_holen(con, auswahl_id) if auswahl_id else None
    if auswahl is None:
        return

    with st.form("profil_bearbeiten_form"):
        name = st.text_input("Anzeigename", value=auswahl["anzeigename"])
        notiz = st.text_area("Notiz", value=auswahl["notiz"] or "")
        if st.form_submit_button("Änderungen speichern"):
            db.schueler_aktualisieren(con, auswahl["id"], anzeigename=name,
                                      notiz=notiz)
            g.merken("Gespeichert.")
            st.rerun()

    with st.expander("Profil endgültig löschen"):
        u = db.schueler_uebersicht(con, auswahl["id"])
        st.warning(
            f"Löscht **{auswahl['anzeigename']}** mit {u['anzahl_diktate']} "
            f"Text(en) und {u['anzahl_fehler']} Fehlereintrag/-einträgen. "
            "Das lässt sich nicht rückgängig machen."
        )
        bestaetigung = st.text_input(
            "Zum Bestätigen den Anzeigenamen eintippen:", key="loesch_bestaetigung"
        )
        if st.button("Profil löschen", type="primary", disabled=not bestaetigung):
            if bestaetigung.strip() == auswahl["anzeigename"]:
                db.schueler_loeschen(con, auswahl["id"])
                if g.aktive_schueler_id() == auswahl["id"]:
                    st.session_state.pop("schueler_id", None)
                g.merken("Profil gelöscht.")
                st.rerun()
            else:
                st.error("Der eingetippte Name stimmt nicht überein.")
