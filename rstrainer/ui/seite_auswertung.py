"""Seite: Fehleranalyse, Verlauf und Export für Elterngespräche."""

from __future__ import annotations

import streamlit as st

from .. import analysis, charts, config, db, docx_export
from . import gemeinsam as g


def zeichnen(con, schueler) -> None:
    st.header("Fehleranalyse und Verlauf")

    diktate = db.diktat_liste(con, schueler["id"])
    fehler = [dict(f) for f in db.fehler_liste(con, schueler["id"])]
    if not diktate or not fehler:
        st.info(
            "Für die Auswertung braucht es mindestens ein Diktat mit erfassten "
            "Fehlern."
        )
        return

    liste = g.kategorienliste()
    punkte = [
        analysis.Diktatpunkt(d["id"], d["datum"], d["titel"], d["wortzahl"])
        for d in diktate
    ]
    reihen = analysis.zeitreihe(punkte, fehler)
    trends = analysis.trends_bestimmen(punkte, fehler)

    spalten = st.columns(3)
    spalten[0].metric("Diktate", len(punkte))
    spalten[1].metric("Erfasste Fehler", len(fehler))
    spalten[2].metric("Betroffene Kategorien", len(reihen))

    if len(punkte) < config.TREND_FENSTER + 1:
        st.info(
            f"Für eine Trendaussage werden mindestens {config.TREND_FENSTER + 1} "
            f"Diktate verglichen (die letzten {config.TREND_FENSTER} gegen die "
            f"{config.TREND_FENSTER} davor). Aktuell sind es {len(punkte)}."
        )

    st.divider()
    st.subheader("Häufigkeit nach Kategorie")
    haeufigkeit = {nr: sum(reihe) for nr, reihe in reihen.items()}
    balken = charts.balken_kategorien(haeufigkeit, liste)
    st.pyplot(balken, width="stretch")

    st.divider()
    st.subheader("Entwicklung über die Zeit")
    st.caption(
        "Dargestellt sind Fehler **pro 100 Wörter** – sonst wäre ein langes "
        "Diktat automatisch «schlechter» als ein kurzes. Es werden höchstens "
        f"{charts.MAX_SERIEN} Kategorien gezeichnet; alle übrigen stehen in der "
        "Tabelle darunter."
    )
    linien, gezeigt = charts.verlauf_linien(punkte, reihen, liste)
    st.pyplot(linien, width="stretch")

    st.divider()
    st.subheader("Einstufung je Kategorie")
    _trendtabelle(trends, liste, gezeigt)

    st.divider()
    _export(con, schueler, punkte, trends, liste, balken, linien)


def _trendtabelle(trends, liste, gezeigt: list[str]) -> None:
    import pandas as pd

    zeilen = []
    for nr, t in sorted(trends.items(), key=lambda x: (-x[1].summe_gesamt, x[0])):
        zeilen.append({
            "Kategorie": liste.label(nr),
            "Fehler gesamt": t.summe_gesamt,
            "In Diktaten": f"{t.diktate_mit_fehler} von {t.diktate_gesamt}",
            "Entwicklung": f"{t.symbol} {t.text}",
            "Vorher": t.rate_vorher,
            "Aktuell": t.rate_aktuell,
            "Im Diagramm": "✓" if nr in gezeigt else "",
        })
    st.dataframe(pd.DataFrame(zeilen), hide_index=True, width="stretch")
    st.caption(
        "«Vorher» und «Aktuell» sind Fehler pro 100 Wörter, gemittelt über die "
        f"jeweils {config.TREND_FENSTER} Diktate. Eine Veränderung gilt erst ab "
        f"{config.TREND_SCHWELLE:.0%} und mindestens "
        f"{config.TREND_MINDESTDIFFERENZ} Fehlern/100 Wörtern als Trend – "
        "darunter ist es Rauschen."
    )


def _export(con, schueler, punkte, trends, liste, balken, linien) -> None:
    st.subheader("Export für das Elterngespräch")
    kommentar = st.text_area(
        "Einschätzung der Lehrperson (erscheint im Bericht)",
        key="verlauf_kommentar",
    )

    spalte_a, spalte_b = st.columns(2)
    with spalte_a:
        if st.button("Diagramme als Bild speichern"):
            p1 = charts.speichern(
                balken, config.EXPORT_DIR / f"Haeufigkeit_{schueler['id']}.png")
            p2 = charts.speichern(
                linien, config.EXPORT_DIR / f"Verlauf_{schueler['id']}.png")
            for pfad in (p1, p2):
                with open(pfad, "rb") as datei:
                    st.download_button(f"{pfad.name} herunterladen", datei.read(),
                                       file_name=pfad.name, mime="image/png",
                                       key=f"dl_{pfad.name}")
            st.success("Bilder erzeugt.")

    with spalte_b:
        if st.button("Verlaufsbericht als Word-Datei", type="primary"):
            bild = charts.speichern(
                linien, config.EXPORT_DIR / f"Verlauf_{schueler['id']}.png")
            zeitraum = (f"{punkte[0].datum} bis {punkte[-1].datum} "
                        f"({len(punkte)} Diktate)")
            zeilen = [
                {
                    "kategorie_nr": nr,
                    "summe_gesamt": t.summe_gesamt,
                    "text": f"{t.symbol} {t.text}",
                    "rate_vorher": t.rate_vorher,
                    "rate_aktuell": t.rate_aktuell,
                }
                for nr, t in sorted(trends.items(),
                                    key=lambda x: (-x[1].summe_gesamt, x[0]))
            ]
            pfad = config.EXPORT_DIR / f"Verlaufsbericht_{schueler['id']}.docx"
            docx_export.verlaufsbericht_schreiben(
                pfad, g.anzeigename(con, schueler), zeitraum, zeilen, liste,
                bild, kommentar,
            )
            with open(pfad, "rb") as datei:
                st.download_button(
                    "Bericht herunterladen", datei.read(), file_name=pfad.name,
                    mime="application/vnd.openxmlformats-officedocument."
                         "wordprocessingml.document",
                )
            st.success(f"Erzeugt: `{pfad}`")
    g.datenschutz_fussnote()
