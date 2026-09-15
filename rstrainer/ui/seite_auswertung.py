"""Seite: Fehleranalyse, Verlauf und Export für Elterngespräche."""

from __future__ import annotations

import streamlit as st

from .. import analysis, charts, config, db, docx_export
from ..kategorien import (FB_REIHE, FOERDERBEREICHE, fehler_nach_foerderbereich,
                          foerderbereich_label, verteilung_foerderbereiche)
from . import gemeinsam as g


def zeichnen(con, schueler) -> None:
    st.header("Förderprofil und Verlauf")

    diktate = db.diktat_liste(con, schueler["id"])
    fehler = [dict(f) for f in db.fehler_liste(con, schueler["id"])]
    if not diktate or not fehler:
        st.info(
            "Für die Auswertung braucht es mindestens einen Text mit erfassten "
            "Fehlern."
        )
        return

    reg = g.register()
    punkte = [
        analysis.Diktatpunkt(d["id"], d["datum"], d["titel"], d["wortzahl"],
                             tuple(g.json_liste(d["ziel_kategorien"])))
        for d in diktate
    ]
    reihen = analysis.zeitreihe(punkte, fehler)
    trends = analysis.trends_bestimmen(punkte, fehler)

    spalten = st.columns(3)
    spalten[0].metric("Texte", len(punkte))
    spalten[1].metric("Erfasste Fehler", len(fehler))
    spalten[2].metric("Betroffene Fehlerarten", len(reihen))

    if len(punkte) < config.TREND_FENSTER + 1:
        st.info(
            f"Für eine Trendaussage werden mindestens {config.TREND_FENSTER + 1} "
            f"Texte verglichen (die letzten {config.TREND_FENSTER} gegen die "
            f"{config.TREND_FENSTER} davor). Aktuell sind es {len(punkte)}."
        )

    st.divider()
    _foerderbereiche(punkte, fehler, reg)

    st.divider()
    st.subheader("Häufigkeit nach Fehlerart")
    haeufigkeit = {nr: sum(reihe) for nr, reihe in reihen.items()}
    balken = charts.balken_kategorien(haeufigkeit, reg)
    st.pyplot(balken, width="stretch")

    st.divider()
    st.subheader("Entwicklung über die Zeit")
    st.caption(
        "Dargestellt sind Fehler **pro 100 Wörter** – sonst wäre ein langer "
        "Text automatisch «schlechter» als ein kurzer. Es werden höchstens "
        f"{charts.MAX_SERIEN} Fehlerarten gezeichnet; alle übrigen stehen in der "
        "Tabelle darunter."
    )
    linien, gezeigt = charts.verlauf_linien(punkte, reihen, reg)
    st.pyplot(linien, width="stretch")

    st.divider()
    st.subheader("Einstufung je Fehlerart")
    _trendtabelle(trends, reg, gezeigt)

    st.divider()
    _export(con, schueler, punkte, trends, reg, balken, linien)


def _foerderbereiche(punkte, fehler, reg) -> None:
    """Ergänzung B: Die Förderbereiche sind die eigentliche Ausgabe. Aus
    dieser Ansicht leitet die Lehrperson ab, was als Nächstes geübt wird."""
    st.subheader("Förderbereiche F1–F10")
    verteilung = verteilung_foerderbereiche(fehler)
    gesamt = sum(verteilung.values())
    if not gesamt:
        st.info("Noch keine Rechtschreibfehler (Bereich A) erfasst.")
        return
    nach_nr: dict[str, int] = {}
    for f in fehler:
        nach_nr[f["kategorie_nr"]] = nach_nr.get(f["kategorie_nr"], 0) + 1

    f9 = verteilung.get("F9", 0)
    f10 = verteilung.get("F10", 0)
    f1_8 = sum(verteilung.get(f, 0) for f in FB_REIHE[:8])
    if f9 > f1_8 and f9 >= 3:
        st.info(
            "**F9 überwiegt.** Hohe Last bei Durchgliederung und Sorgfalt bei geringer "
            "Last in F1–F8 spricht für Kontrollstrategien (Abhören, Kontrolllesen), nicht "
            "für Regelvermittlung (Ergänzung B.3)."
        )
    if gesamt >= 10 and f10 / gesamt > 0.15:
        st.warning(
            f"**F10 ist gross** ({round(100 * f10 / gesamt)} %). Wächst der Restbereich, "
            "deutet das eher auf ein Problem im Classifier als auf eine Schülerschwäche – "
            "bitte die 33/34/37-Zuordnungen durchsehen."
        )
    maximum = max(verteilung.values())
    for f in FB_REIHE:
        n = verteilung.get(f, 0)
        b = FOERDERBEREICHE[f]
        with st.expander(f"{f} · {b['name']} — {n} ({round(100 * n / gesamt)} %)", expanded=False):
            st.progress(n / maximum if maximum else 0.0)
            st.caption(b["foerdern"])
            for nr in b["olfa"]:
                st.markdown(f"- {reg.label(nr)}: **{nach_nr.get(nr, 0)}**")

    st.markdown("**Entwicklung je Förderbereich** (Fehler pro 100 Wörter)")
    fehler_f = fehler_nach_foerderbereich(fehler)
    trends_f = analysis.trends_bestimmen(punkte, fehler_f)
    import pandas as pd
    zeilen = [{
        "Förderbereich": foerderbereich_label(f),
        "Fehler gesamt": t.summe_gesamt,
        "In Texten": f"{t.diktate_mit_fehler} von {t.diktate_gesamt}",
        "Entwicklung": f"{t.symbol} {t.text}",
        "Vorher": t.rate_vorher, "Aktuell": t.rate_aktuell,
    } for f, t in sorted(trends_f.items(), key=lambda x: (-x[1].summe_gesamt, x[0]))]
    st.dataframe(pd.DataFrame(zeilen), hide_index=True, width="stretch")


def _trendtabelle(trends, reg, gezeigt: list[str]) -> None:
    import pandas as pd

    zeilen = []
    for nr, t in sorted(trends.items(), key=lambda x: (-x[1].summe_gesamt, x[0])):
        zeilen.append({
            "Fehlerart": reg.label(nr),
            "Fehler gesamt": t.summe_gesamt,
            "In Texten": f"{t.diktate_mit_fehler} von {t.diktate_gesamt}",
            "Entwicklung": f"{t.symbol} {t.text}",
            "Vorher": t.rate_vorher,
            "Aktuell": t.rate_aktuell,
            "Im Diagramm": "✓" if nr in gezeigt else "",
        })
    st.dataframe(pd.DataFrame(zeilen), hide_index=True, width="stretch")
    st.caption(
        "«Vorher» und «Aktuell» sind Fehler pro 100 Wörter, gemittelt über die "
        f"jeweils {config.TREND_FENSTER} Texte. Eine Veränderung gilt erst ab "
        f"{config.TREND_SCHWELLE:.0%} und mindestens "
        f"{config.TREND_MINDESTDIFFERENZ} Fehlern/100 Wörtern als Trend – "
        "darunter ist es Rauschen."
    )


def _export(con, schueler, punkte, trends, reg, balken, linien) -> None:
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
                        f"({len(punkte)} Texte)")
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
                pfad, g.anzeigename(con, schueler), zeitraum, zeilen, reg,
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
