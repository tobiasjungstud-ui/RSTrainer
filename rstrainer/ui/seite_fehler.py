"""Seite: Fehlererfassung – diff-gestützt oder von Hand.

Der Diff schlägt Abweichungen und passende Kategorien vor; bestätigt und
zugeordnet wird von der Lehrperson. Vorschläge werden nie automatisch
übernommen.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from .. import db, diffing, docx_export
from .. import config
from . import gemeinsam as g


def zeichnen(con, schueler) -> None:
    st.header("Fehlererfassung")

    diktate = db.diktat_liste(con, schueler["id"])
    if not diktate:
        st.info("Bitte zuerst unter **Diktate** ein Diktat erfassen.")
        return

    # Streamlit kopiert Widget-Werte tief; sqlite3.Row lässt sich nicht picklen.
    # Deshalb immer nur die ID als Option übergeben und den Text nachschlagen.
    beschriftung = {d["id"]: f"{d['datum']} · {d['titel']}" for d in diktate}
    diktat_id = st.selectbox(
        "Diktat", [d["id"] for d in reversed(diktate)],
        format_func=lambda i: beschriftung.get(i, str(i)),
        key="fehler_diktat",
    )
    diktat = db.diktat_holen(con, diktat_id) if diktat_id else None
    if diktat is None:
        return

    reiter_diff, reiter_hand, reiter_liste = st.tabs(
        ["🔍 Abgleich mit Schülertext", "✍️ Fehler von Hand", "📋 Erfasste Fehler & Infoblatt"]
    )
    with reiter_diff:
        _diff_ablauf(con, schueler, diktat)
    with reiter_hand:
        _von_hand(con, schueler, diktat)
    with reiter_liste:
        _fehlerliste(con, schueler, diktat)


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------

def _diff_ablauf(con, schueler, diktat) -> None:
    if not diktat["korrektur_gelesen"]:
        st.error(
            "**Abgleich gesperrt.** Der Originaltext dieses Diktats ist noch nicht "
            "als korrekturgelesen bestätigt. Da er die Referenzwahrheit für den "
            "Abgleich ist, würde jeder Tippfehler darin als Schülerfehler gezählt. "
            "Bitte unter **Diktate → Archiv** bestätigen."
        )
        return

    liste = g.kategorienliste()
    st.caption(
        "Den abgetippten Schülertext einfügen. Die App richtet ihn wortweise am "
        "Original aus und schlägt Abweichungen vor. Satzzeichen werden dabei "
        "nicht verglichen."
    )

    schuelertext = st.text_area(
        "Schülertext", value=diktat["schuelertext"] or "", height=200,
        key=f"schuelertext_{diktat['id']}",
    )

    spalte_a, spalte_b = st.columns([1, 3])
    with spalte_a:
        if st.button("Text speichern", disabled=not schuelertext.strip()):
            db.diktat_aktualisieren(con, diktat["id"], schuelertext=schuelertext)
            g.merken("Schülertext gespeichert.")
    with spalte_b:
        if st.button("Abgleich starten", type="primary",
                     disabled=not schuelertext.strip()):
            db.diktat_aktualisieren(con, diktat["id"], schuelertext=schuelertext)
            st.session_state[f"abweichungen_{diktat['id']}"] = diffing.vergleiche(
                diktat["text_original"], schuelertext, liste
            )
            st.rerun()

    abweichungen = st.session_state.get(f"abweichungen_{diktat['id']}")
    if abweichungen is None:
        return

    kennzahlen = diffing.kennzahlen(diktat["text_original"], schuelertext)
    spalten = st.columns(4)
    spalten[0].metric("Wörter im Original", kennzahlen["wortzahl_original"])
    spalten[1].metric("Wörter im Schülertext", kennzahlen["wortzahl_schueler"])
    spalten[2].metric("Abweichungen", kennzahlen["abweichungen"])
    spalten[3].metric("Fehlerquote", f"{kennzahlen['fehlerquote_prozent']} %")

    if not abweichungen:
        g.merken("Keine Abweichungen gefunden.")
        return

    st.divider()
    st.markdown(
        f"### {len(abweichungen)} vorgeschlagene Abweichungen  \n"
        "Jede Zeile einzeln bestätigen und die Kategorie zuordnen. "
        "Nicht angehakte Zeilen werden ignoriert."
    )

    bereits_erfasst = {
        (f["wort_original"], f["wort_schueler"])
        for f in db.fehler_liste(con, schueler["id"], diktat["id"])
    }

    optionen = [k.nr for k in liste]
    with st.form(f"diff_form_{diktat['id']}"):
        auswahl: list[tuple] = []
        for i, a in enumerate(abweichungen):
            schon_da = (a.wort_original, a.wort_schueler) in bereits_erfasst
            spalte_haken, spalte_wort, spalte_kat = st.columns([1, 3, 4])
            with spalte_haken:
                uebernehmen = st.checkbox(
                    "übernehmen", value=not schon_da, key=f"diff_ok_{diktat['id']}_{i}",
                    label_visibility="collapsed",
                )
            with spalte_wort:
                st.markdown(f"**{a.darstellung}**")
                st.caption(a.kontext or "–")
                if schon_da:
                    st.caption("⚠️ bereits erfasst")
            with spalte_kat:
                vorgabe = a.vorschlaege[0].nr if a.vorschlaege else optionen[-1]
                kategorie = st.selectbox(
                    "Kategorie", optionen,
                    index=optionen.index(vorgabe) if vorgabe in optionen else 0,
                    format_func=liste.label, key=f"diff_kat_{diktat['id']}_{i}",
                    label_visibility="collapsed",
                )
                if a.vorschlaege:
                    st.caption("Vorschlag: "
                               + ", ".join(k.nr for k in a.vorschlaege[:3]))
            auswahl.append((uebernehmen, a, kategorie))
            st.divider()

        if st.form_submit_button("Ausgewählte Fehler übernehmen", type="primary"):
            eintraege = [
                {
                    "diktat_id": diktat["id"],
                    "kategorie_nr": kategorie,
                    "wort_original": a.wort_original,
                    "wort_schueler": a.wort_schueler,
                    "kontext": a.kontext,
                    "datum": diktat["datum"],
                }
                for uebernehmen, a, kategorie in auswahl if uebernehmen
            ]
            anzahl = db.fehler_mehrere_anlegen(con, schueler["id"], eintraege)
            st.session_state.pop(f"abweichungen_{diktat['id']}", None)
            g.merken(f"{anzahl} Fehler übernommen.")
            st.rerun()


# ---------------------------------------------------------------------------
# Von Hand
# ---------------------------------------------------------------------------

def _von_hand(con, schueler, diktat) -> None:
    liste = g.kategorienliste()
    st.caption(
        "Für Fehler, die der Abgleich nicht findet – zum Beispiel Satzzeichen, "
        "Silbentrennung am Zeilenende oder unleserliche Stellen."
    )
    optionen = [k.nr for k in liste]
    with st.form(f"fehler_hand_{diktat['id']}", clear_on_submit=True):
        spalte_a, spalte_b = st.columns(2)
        with spalte_a:
            richtig = st.text_input("Richtige Schreibung")
        with spalte_b:
            falsch = st.text_input("Geschriebene Form")
        kategorie = st.selectbox("OLFA-Kategorie", optionen, format_func=liste.label)
        kontext = st.text_input("Kontext / Satzausschnitt")
        notiz = st.text_input("Notiz")
        if st.form_submit_button("Fehler erfassen", type="primary"):
            if not (richtig.strip() or falsch.strip()):
                st.error("Bitte mindestens eine der beiden Schreibungen angeben.")
            else:
                db.fehler_anlegen(
                    con, schueler["id"], kategorie, diktat["id"], richtig, falsch,
                    kontext, diktat["datum"], notiz,
                )
                g.merken("Fehler erfasst.")
                st.rerun()


# ---------------------------------------------------------------------------
# Liste + Informationsblatt
# ---------------------------------------------------------------------------

def _fehlerliste(con, schueler, diktat) -> None:
    import pandas as pd

    liste = g.kategorienliste()
    fehler = db.fehler_liste(con, schueler["id"], diktat["id"])
    if not fehler:
        st.info("Zu diesem Diktat sind noch keine Fehler erfasst.")
        return

    tabelle = pd.DataFrame([
        {
            "Nr.": f["id"],
            "Richtig": f["wort_original"],
            "Geschrieben": f["wort_schueler"],
            "Kategorie": liste.label(f["kategorie_nr"]),
            "Kontext": f["kontext"],
        }
        for f in fehler
    ])
    st.dataframe(tabelle, hide_index=True, width="stretch")

    haeufigkeit: dict[str, int] = {}
    for f in fehler:
        haeufigkeit[f["kategorie_nr"]] = haeufigkeit.get(f["kategorie_nr"], 0) + 1
    st.markdown("**Verteilung**")
    for nr, anzahl in sorted(haeufigkeit.items(), key=lambda x: (-x[1], x[0])):
        st.markdown(f"- {liste.label(nr)}: **{anzahl}×**")

    zu_loeschen = st.selectbox(
        "Einzelnen Fehler löschen", [0] + [f["id"] for f in fehler],
        format_func=lambda i: "– auswählen –" if i == 0 else f"Nr. {i}",
        key=f"loesche_fehler_{diktat['id']}",
    )
    if zu_loeschen and st.button("Löschen", key=f"loeschknopf_{diktat['id']}"):
        db.fehler_loeschen(con, zu_loeschen)
        st.rerun()

    st.divider()
    st.subheader("Informationsblatt zum Diktat")
    kommentar = st.text_area(
        "Kurzkommentar für das Blatt", key=f"kommentar_{diktat['id']}",
        placeholder="z. B. «Die Kürzemarkierung sitzt deutlich besser als im Vormonat.»",
    )
    mit_text = st.checkbox("Diktattext anhängen", value=True,
                           key=f"mit_text_{diktat['id']}")
    if st.button("Informationsblatt erzeugen", type="primary",
                 key=f"infoblatt_{diktat['id']}"):
        kennzahlen = (
            diffing.kennzahlen(diktat["text_original"], diktat["schuelertext"])
            if diktat["schuelertext"]
            else {"wortzahl_original": diktat["wortzahl"], "fehlerquote_prozent": None}
        )
        pfad = config.EXPORT_DIR / (
            f"Infoblatt_{schueler['id']}_{diktat['datum']}_{diktat['id']}.docx"
        )
        docx_export.informationsblatt_schreiben(
            pfad, g.anzeigename(con, schueler), diktat["titel"], diktat["datum"],
            [dict(f) for f in fehler], liste, kennzahlen, kommentar,
            diktat["text_original"] if mit_text else "",
        )
        with open(pfad, "rb") as datei:
            st.download_button(
                "Informationsblatt herunterladen", datei.read(), file_name=pfad.name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        st.success(f"Erzeugt: `{pfad}`")
