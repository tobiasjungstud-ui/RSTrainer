"""Seite: Fehleranalyse, Verlauf und Export für Elterngespräche."""

from __future__ import annotations

import streamlit as st

from .. import analysis, charts, config, db, olfa_werte
from ..kategorien import (FB_REIHE, FOERDERBEREICHE, fehler_nach_foerderbereich,
                          foerderbereich_label, verteilung_foerderbereiche)
from . import gemeinsam as g


def zeichnen(con, schueler) -> None:
    st.header("Förderprofil und Verlauf")

    # Zwei getrennte Welten: geschriebene Texte (Diktat, freier Text) tragen die
    # Rechtschreibauswertung; diktierte Texte (Sprachsoftware) nur Satzbau und
    # Grammatik. Sie werden nie vermischt.
    diktate = db.diktat_liste(con, schueler["id"], textart="geschrieben")
    fehler = [dict(f) for f in db.fehler_liste(con, schueler["id"], textart="geschrieben")]
    diktierte = db.diktat_liste(con, schueler["id"], textart="diktiert")
    fehler_diktiert = [dict(f) for f in db.fehler_liste(con, schueler["id"], textart="diktiert")]
    reg = g.register()
    if not diktate or not fehler:
        st.info(
            "Für die Rechtschreibauswertung braucht es mindestens einen geschriebenen "
            "Text mit erfassten Fehlern."
        )
        if diktierte:
            st.divider()
            _diktierte_texte(con, schueler, diktierte, fehler_diktiert, reg)
        return

    punkte = [
        analysis.Diktatpunkt(d["id"], d["datum"], d["titel"], d["wortzahl"],
                             tuple(g.json_liste(d["ziel_kategorien"])))
        for d in diktate
    ]
    reihen = analysis.zeitreihe(punkte, fehler)
    trends = analysis.trends_bestimmen(punkte, fehler)

    spalten = st.columns(4)
    spalten[0].metric("Geschriebene Texte", len(punkte))
    spalten[1].metric("Erfasste Fehler", len(fehler))
    spalten[2].metric("Betroffene Fehlerarten", len(reihen))
    spalten[3].metric("Diktierte Texte", len(diktierte), help="Sprachsoftware – nur Satzbau und Grammatik, getrennt unten.")

    if len(punkte) < config.TREND_FENSTER + 1:
        st.info(
            f"Für eine Trendaussage werden mindestens {config.TREND_FENSTER + 1} "
            f"Texte verglichen (die letzten {config.TREND_FENSTER} gegen die "
            f"{config.TREND_FENSTER} davor). Aktuell sind es {len(punkte)}."
        )

    st.divider()
    _olfa_werte(diktate, fehler, reg)

    st.divider()
    _bereichsuebersicht(con, schueler, fehler, reg, fehler_diktiert)

    if diktierte:
        st.divider()
        _diktierte_texte(con, schueler, diktierte, fehler_diktiert, reg)

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


def _olfa_werte(diktate, fehler, reg) -> None:
    """OLFA-Kennwerte nach dem Original (S. 29–37): Gruppen I–III,
    Kompetenzwert, Fehler auf 100 Wörter, tolerierte Fehlerzahl, Leistungswert.
    Klasse und Schulform werden nicht gespeichert – nur für die Rechnung
    gewählt (Datensparsamkeit)."""
    import pandas as pd

    st.subheader("OLFA-Kennwerte (Original S. 29–37)")
    ids = {d["id"]: d for d in diktate}
    auswahl = st.multiselect(
        "Texte, die in die Rechnung eingehen (mehrere Texte aus kurzem Zeitraum dürfen zusammengefasst werden, S. 15)",
        options=[d["id"] for d in diktate], default=[d["id"] for d in diktate],
        format_func=lambda i: f"{ids[i]['datum']} · {ids[i]['titel']} ({ids[i]['wortzahl']} Wörter)",
        key="werte_texte")
    if not auswahl:
        st.info("Bitte mindestens einen Text wählen.")
        return
    spalte_a, spalte_b = st.columns(2)
    zeitpunkt = spalte_a.selectbox("Klassenstufe und Zeitpunkt (Tabelle 5, S. 30)",
                                   ["– ohne –"] + olfa_werte.ZEITPUNKTE, index=9, key="werte_zeitpunkt")
    schulform = spalte_b.selectbox("Schulform", list(olfa_werte.SCHULFORMEN),
                                   format_func=olfa_werte.SCHULFORMEN.get, key="werte_schulform")
    kats = [f["kategorie_nr"] for f in fehler if f["diktat_id"] in auswahl and reg.bereich(f["kategorie_nr"]) == "A"]
    woerter = sum(ids[i]["wortzahl"] for i in auswahl)
    w = olfa_werte.berechnen(kats, woerter, None if zeitpunkt == "– ohne –" else zeitpunkt, schulform)

    k = st.columns(5)
    k[0].metric("Wörter", w.woerter)
    k[1].metric("Gesamtfehler (1–37)", w.gesamt)
    k[2].metric("Fehler auf 100 Wörter", "–" if w.f100 is None else f"{w.f100}")
    k[3].metric("Kompetenzwert KW", "–" if w.kw is None else f"{w.kw:g}")
    k[4].metric("Leistungswert LW", "–" if w.lw is None else f"{w.lw:g}")
    g1, g2, g3 = st.columns(3)
    g1.metric("Gruppe I · protoalphabetisch", f"{w.gruppen['I']} · {w.prozent['I']} %")
    g2.metric("Gruppe II · alphabetisch", f"{w.gruppen['II']} · {w.prozent['II']} %")
    g3.metric("Gruppe III · orthographisch", f"{w.gruppen['III']} · {w.prozent['III']} %")
    st.caption(f"Ohne Gruppe (zählen nur zur Gesamtfehlerzahl): 36 Umlaut {w.ohne_gruppe['36']}, 37 Sonstige {w.ohne_gruppe['37']}.")
    if w.tf is not None:
        st.caption(f"Tolerierte Fehlerzahl TF = {w.tf} auf 100 Wörter; relativer Fehlerwert RF = {w.rf}.")
    for warnung in w.warnungen:
        st.warning(warnung)
    st.markdown(f"**Deutung des Kompetenzwerts (S. 36):** {olfa_werte.deutung_kw(w.kw)}")
    if w.lw is not None:
        st.markdown(olfa_werte.deutung_lw(w.kw, w.lw))
    with st.expander("Rechenweg und OLFA-Liste (Kopiervorlage S. 59, Version CH)"):
        for zeile in w.rechenweg:
            st.markdown(f"- {zeile}")
        zeilen = olfa_werte.tabelle_zeilen(kats, {nr: reg.name(nr) for nr in reg.waehlbar_nummern()} if hasattr(reg, "waehlbar_nummern") else {})
        tabelle = pd.DataFrame([{
            "Nr": z["nr"], "Kategorie": z["name"] or reg.name(z["nr"]),
            "Anzahl": z["anzahl"], "Gruppe": z["gruppe"],
            "Hinweis": "entfällt CH → 37" if z["gesperrt_ch"] else "",
        } for z in zeilen])
        st.dataframe(tabelle, hide_index=True, width="stretch")


def _diktierte_texte(con, schueler, diktierte, fehler_diktiert, reg) -> None:
    """Eigene Ausgabe für diktierte Texte: Satzbau, Grammatik, Zeichensetzung,
    Textebene – ohne jede Rechtschreibzahl."""
    from .. import grammatik
    import pandas as pd

    st.subheader("🎙️ Diktierte Texte (Sprachsoftware): Satzbau und Grammatik")
    st.caption(
        "Hier schreibt das Programm, nicht das Kind. Rechtschreibung wird deshalb nicht gezählt; "
        "diese Befunde fliessen weder in die OLFA-Kennwerte noch in Förderplan und Übungsblätter ein."
    )
    k = st.columns(3)
    k[0].metric("Diktierte Texte", len(diktierte))
    k[1].metric("Wörter", sum(int(d["wortzahl"] or 0) for d in diktierte))
    k[2].metric("Befunde B–E", len(fehler_diktiert))
    if not fehler_diktiert:
        st.info("Noch keine Befunde zu diktierten Texten – Analyse unter «Fehleranalyse» im Reiter "
                "«Freie Analyse durch das Sprachmodell».")
        return
    titel = {d["id"]: d["titel"] for d in diktierte}
    zaehler: dict[str, int] = {}
    for f in fehler_diktiert:
        zaehler[f["kategorie_nr"]] = zaehler.get(f["kategorie_nr"], 0) + 1
    maximum = max(zaehler.values())
    for nr, n in sorted(zaehler.items(), key=lambda x: (-x[1], x[0])):
        spalte_a, spalte_b = st.columns([3, 1])
        spalte_a.progress(n / maximum, text=reg.label(nr))
        spalte_b.markdown(f"**{n}** · {round(100 * n / len(fehler_diktiert))} %")
        gk = grammatik.get(nr)
        if gk is not None and gk.foerdern:
            spalte_a.caption(f"Fördern: {gk.foerdern}")
    st.dataframe(pd.DataFrame([{
        "Datum": f["datum"], "Text": titel.get(f["diktat_id"], "–"),
        "Diktiert": f["wort_schueler"], "Richtig": f["wort_original"],
        "Kategorie": reg.label(f["kategorie_nr"]), "Im Satz": f["kontext"],
    } for f in fehler_diktiert]), hide_index=True, width="stretch")


def _bereichsuebersicht(con, schueler, fehler, reg, fehler_diktiert=None) -> None:
    """Eine Übersicht je Bereich – Rechtschreibung, Grammatik, Syntax,
    Zeichensetzung, Textebene – mit den konkreten Fehlern des Kindes.

    Die Förderbereiche F1–F10 beantworten «Was üben wir?» für die
    Rechtschreibung. Diese Ansicht beantwortet die Frage davor: «Wo liegt das
    Problem überhaupt – in der Schreibung oder im Satzbau?» Und sie zeigt es
    nicht als Zahl, sondern am Beispiel: jeder Fehler mit seinem Satz."""
    from .. import grammatik
    import pandas as pd

    st.subheader("Übersicht je Bereich")
    titel = {d["id"]: d["titel"] for d in db.diktat_liste(con, schueler["id"])}
    quelle = "geschrieben"
    if fehler_diktiert:
        quelle = st.radio("Textquelle", ["geschrieben", "diktiert", "alle"], horizontal=True,
                          format_func={"geschrieben": "geschriebene Texte", "diktiert": "diktierte Texte (B–E)",
                                       "alle": "beide (Rechtschreibung nur aus geschriebenen)"}.get,
                          key="uebersicht_quelle")
    grundlage = {"geschrieben": fehler, "diktiert": fehler_diktiert or [],
                 "alle": list(fehler) + list(fehler_diktiert or [])}[quelle]
    nach_bereich: dict[str, list[dict]] = {b: [] for b in grammatik.BEREICH_REIHE}
    for f in grundlage:
        nach_bereich.setdefault(reg.bereich(f["kategorie_nr"]), []).append(f)

    beschriftung = {b: f"{grammatik.bereich_name(b)} ({len(nach_bereich.get(b, []))})"
                    for b in grammatik.BEREICH_REIHE}
    bereich = st.radio("Bereich", grammatik.BEREICH_REIHE, horizontal=True,
                       format_func=beschriftung.get, key="uebersicht_bereich")
    liste = nach_bereich.get(bereich, [])
    if not liste:
        st.info("In diesem Bereich sind keine Fehler erfasst.")
        return

    st.caption(grammatik.BEREICHE[bereich]["foerdern"])

    # Verteilung innerhalb des Bereichs: welche Kategorien tragen die Last?
    zaehler: dict[str, int] = {}
    for f in liste:
        zaehler[f["kategorie_nr"]] = zaehler.get(f["kategorie_nr"], 0) + 1
    maximum = max(zaehler.values())
    for nr, n in sorted(zaehler.items(), key=lambda x: (-x[1], x[0])):
        spalte_a, spalte_b = st.columns([3, 1])
        spalte_a.progress(n / maximum, text=reg.label(nr))
        spalte_b.markdown(f"**{n}** · {round(100 * n / len(liste))} %")
        g = grammatik.get(nr)
        if g is not None and g.foerdern:
            spalte_a.caption(f"Fördern: {g.foerdern}")

    st.markdown(f"**Alle {len(liste)} Fehler in diesem Bereich**")
    tabelle = pd.DataFrame([{
        "Datum": f["datum"],
        "Text": titel.get(f["diktat_id"], "–"),
        "Geschrieben": f["wort_schueler"],
        "Richtig": f["wort_original"],
        "Kategorie": reg.label(f["kategorie_nr"]),
        "Im Satz": f["kontext"],
        "Sicherheit": f.get("konfidenz") if f.get("konfidenz") is not None else "",
    } for f in liste])
    st.dataframe(tabelle, hide_index=True, width="stretch")


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
        format_ = g.formatwahl("verlauf_format")
        if st.button("Verlaufsbericht erzeugen", type="primary"):
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
            endung = g.FORMATE[format_]["endung"]
            pfad = config.EXPORT_DIR / f"Verlaufsbericht_{schueler['id']}.{endung}"
            g.export_modul(format_).verlaufsbericht_schreiben(
                pfad, g.anzeigename(con, schueler), zeitraum, zeilen, reg,
                bild, kommentar,
            )
            with open(pfad, "rb") as datei:
                st.download_button(
                    f"Bericht als {endung.upper()} herunterladen", datei.read(),
                    file_name=pfad.name, mime=g.FORMATE[format_]["mime"],
                )
            st.success(f"Erzeugt: `{pfad}`")
    g.datenschutz_fussnote()
