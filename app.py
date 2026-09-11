"""RSTrainer – Einstiegspunkt der Streamlit-App.

Starten mit:  streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from rstrainer import db
from rstrainer.ui import gemeinsam as g
from rstrainer.ui import (
    seite_auswertung,
    seite_blaetter,
    seite_diktate,
    seite_einstellungen,
    seite_fehler,
    seite_profile,
)

SEITEN = {
    "👤 Profile": "profile",
    "📝 Diktate": "diktate",
    "🔍 Fehlererfassung": "fehler",
    "📄 Übungsblätter": "blaetter",
    "📊 Auswertung": "auswertung",
    "⚙️ Einstellungen": "einstellungen",
}


def main() -> None:
    st.set_page_config(page_title="RSTrainer", page_icon="✏️", layout="wide")
    con = g.verbindung()

    with st.sidebar:
        st.title("✏️ RSTrainer")
        st.caption("Rechtschreibförderung nach OLFA-Systematik")

        profile = db.schueler_liste(con)
        if profile:
            namen = {s["id"]: s["anzeigename"] for s in profile}
            aktuell = g.aktive_schueler_id()
            if aktuell not in namen:
                aktuell = profile[0]["id"]
                st.session_state["schueler_id"] = aktuell
            gewaehlt = st.selectbox(
                "Aktives Profil", list(namen), index=list(namen).index(aktuell),
                format_func=lambda i: namen[i],
            )
            if gewaehlt != aktuell:
                st.session_state["schueler_id"] = gewaehlt
                st.rerun()
        else:
            st.info("Noch kein Profil angelegt.")

        st.divider()
        auswahl = st.radio("Bereich", list(SEITEN), label_visibility="collapsed")

        liste = g.kategorienliste()
        if liste.anzahl_ungeprueft:
            st.divider()
            st.warning(
                f"⚠️ {liste.anzahl_ungeprueft} von {len(liste)} OLFA-Kategorien "
                "sind noch ungeprüft. Die mitgelieferte Liste ist ein "
                "Platzhalter – bitte unter **Einstellungen** gegen Ihr "
                "Fachmaterial abgleichen."
            )

    g.meldungen_anzeigen()

    seite = SEITEN[auswahl]
    schueler_id = g.aktive_schueler_id()
    schueler = db.schueler_holen(con, schueler_id) if schueler_id else None

    if seite == "profile":
        seite_profile.zeichnen(con)
    elif seite == "einstellungen":
        seite_einstellungen.zeichnen(con)
    elif schueler is None:
        g.kein_profil_hinweis()
    elif seite == "diktate":
        seite_diktate.zeichnen(con, schueler)
    elif seite == "fehler":
        seite_fehler.zeichnen(con, schueler)
    elif seite == "blaetter":
        seite_blaetter.zeichnen(con, schueler)
    elif seite == "auswertung":
        seite_auswertung.zeichnen(con, schueler)


if __name__ == "__main__":
    main()
