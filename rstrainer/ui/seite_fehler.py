"""Seite: Fehlererfassung – durch das Sprachmodell, per Abgleich oder von Hand.

Drei Wege, dieselbe Bestätigungsliste:

**Sprachmodell** – ordnet inhaltlich zu und darf für alles, was die OLFA-Liste
nicht abdeckt (vor allem Grammatik), eigene Fehlerarten benennen. Der einzige
Weg, der auch bei freien Texten ohne Vorlage funktioniert.

**Mechanischer Abgleich** – vergleicht Original und Abschrift Wort für Wort
und rät die Kategorie aus dem Buchstabenbild. Braucht zwingend eine Vorlage,
also ein Diktat.

**Von Hand** – für alles, was beide nicht sehen.

Was aus diesen Wegen kommt, ist immer nur ein Vorschlag. Bestätigt und
zugeordnet wird von der Lehrperson; nichts wird ungeprüft übernommen.
"""

from __future__ import annotations

import streamlit as st

from .. import auftraege, config, db, diffing, docx_export, olfa_engine, taxonomie
from ..kategorien import foerderbereich_von, schwerpunkte
from . import gemeinsam as g


def zeichnen(con, schueler) -> None:
    st.header("Fehlererfassung")

    diktate = db.diktat_liste(con, schueler["id"])
    if not diktate:
        st.info("Bitte zuerst unter **Texte** ein Diktat oder einen freien Text erfassen.")
        return

    # Streamlit kopiert Widget-Werte tief; sqlite3.Row lässt sich nicht picklen.
    # Deshalb immer nur die ID als Option übergeben und den Text nachschlagen.
    beschriftung = {
        d["id"]: f"{'📝' if d['art'] == 'freitext' else '📄'} {d['datum']} · {d['titel']}"
        for d in diktate
    }
    diktat_id = st.selectbox(
        "Text", [d["id"] for d in reversed(diktate)],
        format_func=lambda i: beschriftung.get(i, str(i)),
        key="fehler_diktat",
    )
    diktat = db.diktat_holen(con, diktat_id) if diktat_id else None
    if diktat is None:
        return
    ist_frei = diktat["art"] == "freitext"

    namen = ["🤖 Analyse durch das Sprachmodell"]
    if not ist_frei:
        namen.append("🔍 Mechanischer Abgleich")
    namen += ["✍️ Fehler von Hand", "📋 Erfasste Fehler & Infoblatt"]
    reiter = st.tabs(namen)

    with reiter[0]:
        _analyse_ablauf(con, schueler, diktat)
    if ist_frei:
        with reiter[1]:
            _von_hand(con, schueler, diktat)
        with reiter[2]:
            _fehlerliste(con, schueler, diktat)
    else:
        with reiter[1]:
            _diff_ablauf(con, schueler, diktat)
        with reiter[2]:
            _von_hand(con, schueler, diktat)
        with reiter[3]:
            _fehlerliste(con, schueler, diktat)


# ---------------------------------------------------------------------------
# Schülertext – Grundlage aller drei Wege
# ---------------------------------------------------------------------------

def _schuelertext_feld(con, diktat, schluessel: str) -> str:
    ist_frei = diktat["art"] == "freitext"
    text = st.text_area(
        "Text des Kindes" if ist_frei else "Abgetippter Schülertext",
        value=diktat["schuelertext"] or "", height=200,
        key=f"{schluessel}_{diktat['id']}",
    )
    if st.button("Text speichern", key=f"{schluessel}_speichern_{diktat['id']}",
                 disabled=not text.strip()):
        db.diktat_aktualisieren(con, diktat["id"], schuelertext=text)
        g.merken("Text gespeichert.")
        st.rerun()
    return text


# ---------------------------------------------------------------------------
# Weg 1: Analyse durch das Sprachmodell
# ---------------------------------------------------------------------------

def _analyse_ablauf(con, schueler, diktat) -> None:
    reg = g.register()
    ist_frei = diktat["art"] == "freitext"
    st.caption(
        "Das Sprachmodell liest den Text und benennt jeden Fehler – Rechtschreibung "
        "und Grammatik. Wofür die OLFA-Liste keine Kategorie hat, legt es selbst "
        "eine an und ordnet sie hierarchisch ein "
        "(z. B. «Grammatik › Kasus › Dativ statt Akkusativ»)."
        + ("" if ist_frei else
           " Beim Diktat zählt nur, was von der Vorlage abweicht.")
    )

    text = _schuelertext_feld(con, diktat, "analyse_text")

    st.divider()
    st.subheader("Schritt 1 · Prompt erzeugen und in den Chat kopieren")
    if st.button("Analyse-Prompt erzeugen", type="primary",
                 disabled=not text.strip(), key=f"analyse_prompt_{diktat['id']}"):
        db.diktat_aktualisieren(con, diktat["id"], schuelertext=text)
        st.session_state[f"analyse_prompt_text_{diktat['id']}"] = \
            auftraege.analyse_prompt_bauen(
                text, "" if ist_frei else diktat["text_original"],
                reg.liste, reg.sammlung,
            )
        st.rerun()

    prompt_text = st.session_state.get(f"analyse_prompt_text_{diktat['id']}")
    if not prompt_text:
        return
    st.code(prompt_text, language="markdown")
    st.caption(
        "In einen Claude-Chat einfügen und die komplette Antwort – das JSON – "
        "hierher zurückkopieren."
    )

    st.divider()
    st.subheader("Schritt 2 · Antwort einfügen")
    roh = st.text_area("Antwort des Sprachmodells", height=220,
                       key=f"analyse_roh_{diktat['id']}")
    if st.button("Antwort auswerten", key=f"analyse_lesen_{diktat['id']}"):
        if not (roh or "").strip():
            st.warning("Das Eingabefeld ist noch leer. Bitte die Antwort einfügen "
                       "und einmal neben das Feld klicken.")
        else:
            ergebnis = auftraege.analyse_lesen(roh, reg.liste, reg.sammlung)
            if ergebnis.fehler:
                st.error(
                    f"{ergebnis.fehler} Bitte erneut versuchen – oder den "
                    "mechanischen Abgleich nutzen."
                )
            else:
                st.session_state[f"analyse_ergebnis_{diktat['id']}"] = ergebnis
                st.rerun()

    ergebnis = st.session_state.get(f"analyse_ergebnis_{diktat['id']}")
    if ergebnis is None:
        return

    st.divider()
    if not ergebnis.zeilen:
        st.success("Das Sprachmodell hat keinen Fehler gefunden.")
        return

    bezug = text if ist_frei else diktat["text_original"]
    abweichungen = auftraege.analyse_zu_abweichungen(ergebnis.zeilen, bezug, reg.liste)

    if ergebnis.neue_arten:
        st.info(
            f"**{len(ergebnis.neue_arten)} neue Fehlerart(en)** wurden benannt. Sie "
            "werden mit dem Übernehmen angelegt und sind danach unter "
            "**Einstellungen → Gelernte Fehlerarten** zu sehen:\n"
            + "\n".join(f"- **{' › '.join(n.pfad)}** ({n.anzahl}×)"
                        + (f" – {n.beschreibung}" if n.beschreibung else "")
                        for n in ergebnis.neue_arten)
        )

    st.markdown(
        f"### {len(abweichungen)} vorgeschlagene Fehler  \n"
        "Jede Zeile einzeln bestätigen. Nicht angehakte Zeilen werden ignoriert."
    )
    _bestaetigungsliste(con, schueler, diktat, abweichungen,
                        schluessel="analyse", ergebnis=ergebnis)


# ---------------------------------------------------------------------------
# Weg 2: mechanischer Abgleich
# ---------------------------------------------------------------------------

def _diff_ablauf(con, schueler, diktat) -> None:
    """Stufe 1 + 2 des Bau-Prompts: Alignment gegen den Referenztext, danach
    das deterministische Regelwerk (rstrainer.olfa_engine). Kein Sprachmodell.
    Fälle, denen ein Merkmal fehlt, werden nicht geraten, sondern als
    «manuelle Kontrolle» ausgewiesen."""
    st.caption(
        "Der Schülertext wird Wort für Wort gegen den Referenztext ausgerichtet, "
        "graphemorientiert segmentiert und über den OLFA-Entscheidungsbaum "
        "klassifiziert – ohne Sprachmodell, reproduzierbar, mit Begründung und "
        "verworfenen Alternativen je Fehler. Satzzeichen werden nicht verglichen."
    )

    schuelertext = _schuelertext_feld(con, diktat, "diff_text")

    if st.button("Abgleich starten", type="primary",
                 disabled=not schuelertext.strip(), key=f"diff_start_{diktat['id']}"):
        db.diktat_aktualisieren(con, diktat["id"], schuelertext=schuelertext)
        lexikon = dict(olfa_engine.VORGABE_LEXIKON)
        lexikon.update(g.lexikon())
        ergebnis = olfa_engine.analysiere_diktat(
            diktat["text_original"], schuelertext, lexikon, g.muster(schueler["id"])
        )
        # Stufe 4 ohne Modell: Konsequenzprüfung, dann bleibt Offenes offen.
        for e in ergebnis["ereignisse"]:
            if e["status"] == "needs_context":
                olfa_engine.konsequenz_pruefen(e)
                if e["status"] == "needs_context":
                    e["status"] = "manual_review"
                olfa_engine.konfidenz(e, {"zielwortSicherheit": 1})
        st.session_state[f"abweichungen_{diktat['id']}"] = ergebnis
        st.rerun()

    ergebnis = st.session_state.get(f"abweichungen_{diktat['id']}")
    if ergebnis is None:
        return

    kz = ergebnis["kennzahlen"]
    ereignisse = ergebnis["ereignisse"]
    offen = sum(1 for e in ereignisse if e["status"] == "manual_review")
    spalten = st.columns(4)
    spalten[0].metric("Wörter im Original", kz["woerterReferenz"])
    spalten[1].metric("Wörter im Schülertext", kz["woerterSchueler"])
    spalten[2].metric("Fehlerereignisse", len(ereignisse))
    spalten[3].metric("Manuelle Kontrolle", offen)

    ohne_status = [a for a in ergebnis["abdeckung"] if a["status"] == "offen"]
    st.caption(
        f"Vollständigkeitskontrolle im Code: {len(ergebnis['abdeckung'])} Wörter, "
        f"{sum(1 for a in ergebnis['abdeckung'] if a['status'] == 'korrekt')} korrekt, "
        f"{sum(1 for a in ergebnis['abdeckung'] if a['status'] == 'fehler')} mit Fehler"
        + (f", **{len(ohne_status)} ohne Status**" if ohne_status else "") + "."
        + (" Ausgelassen: " + ", ".join(f"«{x['wort']}»" for x in ergebnis["ausgelassen"]) + "."
           if ergebnis["ausgelassen"] else "")
        + (" Zusätzlich: " + ", ".join(f"«{x['wort']}»" for x in ergebnis["zusaetzlich"]) + "."
           if ergebnis["zusaetzlich"] else "")
    )

    if not ereignisse:
        st.success("Keine Abweichungen gefunden.")
        return

    st.divider()
    st.markdown(
        f"### {len(ereignisse)} Fehlerereignisse  \n"
        "Eindeutige zuerst, unsichere unten. Jede Zeile lässt sich umstufen – "
        "eine Umstufung wird als Muster gespeichert und beim nächsten gleichen "
        "Fall vorgeschlagen."
    )
    rang = {"resolved": 0, "resolved_by_area": 1, "resolved_by_ki": 2, "manual_review": 3}
    sortiert = sorted(ereignisse, key=lambda e: (rang.get(e["status"], 4), -(e.get("confidence") or 0)))
    _bestaetigungsliste(
        con, schueler, diktat,
        [
            {
                "wort_original": e["targetForm"], "wort_schueler": e["studentForm"],
                "kontext": (olfa_engine.saetze(schuelertext)[e["sentenceIndex"]]
                            if e["sentenceIndex"] < len(olfa_engine.saetze(schuelertext)) else ""),
                "darstellung": f"{e['studentForm']} → {e['targetForm']}  "
                               f"⟨{e['studentGrapheme'] or '∅'}⟩ für ⟨{e['targetGrapheme'] or '∅'}⟩",
                "vorgabe": e["kategorie"], "vorschlaege": [],
                "begruendung": e["reason"], "neue_art": None,
                "ereignis": e,
            }
            for e in sortiert
        ],
        schluessel="diff",
    )


# ---------------------------------------------------------------------------
# Gemeinsame Bestätigungsliste
# ---------------------------------------------------------------------------

def _bestaetigungsliste(con, schueler, diktat, abweichungen, schluessel: str,
                        ergebnis=None) -> None:
    """Eine Zeile je Vorschlag, jede einzeln abwählbar und umkategorisierbar."""
    reg = g.register()
    bereits_erfasst = {
        (f["wort_original"], f["wort_schueler"])
        for f in db.fehler_liste(con, schueler["id"], diktat["id"])
    }

    # Von diesem Durchlauf vorgeschlagene, noch nicht angelegte Arten gehören
    # in die Auswahl – sonst liesse sich eine Zeile nicht auf ihre eigene neue
    # Art setzen.
    optionen = [nr for nr, _ in reg.waehlbar()]
    zusatz = {}
    if ergebnis is not None:
        for n in ergebnis.neue_arten:
            optionen.append(n.id)
            zusatz[n.id] = "🆕 " + " › ".join(n.pfad)

    def beschriften(nr: str) -> str:
        return zusatz.get(nr) or reg.label(nr)

    with st.form(f"{schluessel}_form_{diktat['id']}"):
        auswahl: list[tuple] = []
        for i, a in enumerate(abweichungen):
            schon_da = (a["wort_original"], a["wort_schueler"]) in bereits_erfasst
            spalte_haken, spalte_wort, spalte_kat = st.columns([1, 3, 4])
            with spalte_haken:
                unsicher = bool(a.get("ereignis")) and a["ereignis"]["status"] == "manual_review"
                uebernehmen = st.checkbox(
                    "übernehmen", value=not schon_da and not unsicher,
                    key=f"{schluessel}_ok_{diktat['id']}_{i}",
                    label_visibility="collapsed",
                )
            with spalte_wort:
                st.markdown(f"**{a['darstellung']}**")
                st.caption(a["kontext"] or "–")
                if a.get("begruendung"):
                    st.caption(f"💬 {a['begruendung']}")
                e = a.get("ereignis")
                if e:
                    stufe = {"resolved": "eindeutig", "resolved_by_area": "Bereich eindeutig",
                             "resolved_by_ki": "KI-geprüft", "manual_review": "manuelle Kontrolle"}
                    zeile = (f"Sicherheit **{e.get('confidence', 0):.2f}** · {stufe.get(e['status'], e['status'])}"
                             + (f" · Förderbereich **{e['foerderbereich']}**" if e.get("foerderbereich") else "")
                             + (" · de-CH" if e.get("definition") == "de-CH" else ""))
                    if e["status"] == "manual_review":
                        st.warning(zeile + (f" · Kandidaten: {', '.join(e['kandidaten'])}" if e.get("kandidaten") else ""))
                    else:
                        st.caption(zeile)
                    with st.expander("Geprüft und verworfen · Herkunft"):
                        for x in e.get("excluded", []):
                            st.markdown(f"- {x['category']}: {x['reason']}")
                        st.markdown(f"- Merkmal: {e.get('featureSource')}"
                                    + (f" – {e['entscheidend']}" if e.get("entscheidend") else ""))
                        for v in e.get("validator", []):
                            st.markdown(f"- Validator: {v['regel']} → {v['ergebnis']}")
                        if e.get("possibleUnderlyingCause"):
                            st.markdown(f"- Vermutete Ursache: {e['possibleUnderlyingCause']}")
                if schon_da:
                    st.caption("⚠️ bereits erfasst")
            with spalte_kat:
                vorgabe = a.get("vorgabe") or "37"
                kand = list(a.get("ereignis", {}).get("kandidaten") or []) if a.get("ereignis") else []
                if kand:
                    optionen = kand + [o for o in optionen if o not in kand]
                kategorie = st.selectbox(
                    "Kategorie", optionen,
                    index=optionen.index(vorgabe) if vorgabe in optionen else 0,
                    format_func=beschriften,
                    key=f"{schluessel}_kat_{diktat['id']}_{i}",
                    label_visibility="collapsed",
                )
                if a.get("vorschlaege"):
                    st.caption("Aus dem Wortbild: "
                               + ", ".join(k.nr for k in a["vorschlaege"][:3]))
            auswahl.append((uebernehmen, a, kategorie))
            st.divider()

        if st.form_submit_button("Ausgewählte Fehler übernehmen", type="primary"):
            _uebernehmen(con, schueler, diktat, auswahl, schluessel, ergebnis)


def _uebernehmen(con, schueler, diktat, auswahl, schluessel: str, ergebnis) -> None:
    genommen = [(a, kat) for nehmen, a, kat in auswahl if nehmen]

    angelegt = []
    if ergebnis is not None and ergebnis.neue_arten:
        # Nur Arten anlegen, die auch wirklich in einer übernommenen Zeile
        # stehen – abgewählte Vorschläge sollen die Sammlung nicht aufblähen.
        gebraucht = {kat for _, kat in genommen}
        ergebnis.neue_arten = [n for n in ergebnis.neue_arten if n.id in gebraucht]
        sammlung = taxonomie.laden()
        angelegt = auftraege.analyse_uebernehmen(ergebnis, sammlung)
        g.sammlung_speichern(sammlung)

    eintraege = []
    muster_neu = 0
    for a, kategorie in genommen:
        e = a.get("ereignis") or {}
        umgestuft = bool(e) and kategorie != e.get("kategorie")
        if umgestuft and e.get("muster"):
            db.muster_speichern(con, schueler["id"], e["muster"], kategorie)
            muster_neu += 1
        eintraege.append({
            "diktat_id": diktat["id"],
            "kategorie_nr": kategorie,
            "wort_original": a["wort_original"],
            "wort_schueler": a["wort_schueler"],
            "kontext": a["kontext"],
            "datum": diktat["datum"],
            "notiz": e.get("reason", "") if e else "",
            "status": "resolved" if umgestuft or not e else e.get("status", "resolved"),
            "konfidenz": 0.95 if umgestuft else (e.get("confidence") if e else None),
            "merkmal": "eigene" if umgestuft else (e.get("featureSource") if e else "eigene"),
            "foerderbereich": foerderbereich_von(kategorie),
        })
    anzahl = db.fehler_mehrere_anlegen(con, schueler["id"], eintraege)
    if muster_neu:
        g.merken(f"{muster_neu} Umstufungsmuster gespeichert.")
    for key in (f"abweichungen_{diktat['id']}", f"analyse_ergebnis_{diktat['id']}",
                f"analyse_prompt_text_{diktat['id']}", f"analyse_roh_{diktat['id']}"):
        st.session_state.pop(key, None)
    meldung = f"{anzahl} Fehler übernommen."
    if angelegt:
        meldung += f" {len(angelegt)} neue Fehlerart(en) angelegt."
    g.merken(meldung)
    st.rerun()


# ---------------------------------------------------------------------------
# Von Hand
# ---------------------------------------------------------------------------

def _von_hand(con, schueler, diktat) -> None:
    reg = g.register()
    st.caption(
        "Für Fehler, die keiner der beiden Wege findet – zum Beispiel Satzzeichen, "
        "Silbentrennung am Zeilenende oder unleserliche Stellen."
    )
    optionen = [nr for nr, _ in reg.waehlbar()]
    with st.form(f"fehler_hand_{diktat['id']}", clear_on_submit=True):
        spalte_a, spalte_b = st.columns(2)
        with spalte_a:
            richtig = st.text_input("Richtige Schreibung")
        with spalte_b:
            falsch = st.text_input("Geschriebene Form")
        kategorie = st.selectbox("Fehlerart", optionen, format_func=reg.label)
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

    reg = g.register()
    ist_frei = diktat["art"] == "freitext"
    fehler = db.fehler_liste(con, schueler["id"], diktat["id"])
    if not fehler:
        st.info("Zu diesem Text sind noch keine Fehler erfasst.")
        return

    punkte = schwerpunkte([dict(f) for f in fehler], hoechstens=8)
    st.markdown("**Schwerpunkte**")
    for nr, anzahl in punkte.liste:
        st.markdown(f"- {reg.label(nr)}: **{anzahl}×**")
    if punkte.rest:
        st.caption(f"Dazu {punkte.rest} weitere Fehlerarten mit einzelnen Vorkommen.")

    tabelle = pd.DataFrame([
        {
            "Nr.": f["id"],
            "Richtig": f["wort_original"],
            "Geschrieben": f["wort_schueler"],
            "Fehlerart": reg.label(f["kategorie_nr"]),
            "Im Text": f["kontext"],
        }
        for f in fehler
    ])
    st.dataframe(tabelle, hide_index=True, width="stretch")

    zu_loeschen = st.selectbox(
        "Einzelnen Fehler löschen", [0] + [f["id"] for f in fehler],
        format_func=lambda i: "– auswählen –" if i == 0 else f"Nr. {i}",
        key=f"loesche_fehler_{diktat['id']}",
    )
    if zu_loeschen and st.button("Löschen", key=f"loeschknopf_{diktat['id']}"):
        db.fehler_loeschen(con, zu_loeschen)
        st.rerun()

    st.divider()
    st.subheader("Informationsblatt zu diesem Text")
    kommentar = st.text_area(
        "Kurzkommentar für das Blatt", key=f"kommentar_{diktat['id']}",
        placeholder="z. B. «Die Kürzemarkierung sitzt deutlich besser als im Vormonat.»",
    )
    mit_text = st.checkbox("Text anhängen", value=True,
                           key=f"mit_text_{diktat['id']}")
    if st.button("Informationsblatt erzeugen", type="primary",
                 key=f"infoblatt_{diktat['id']}"):
        if ist_frei:
            # Ohne Vorlage gibt es keine Abweichungszählung; die Quote ergibt
            # sich direkt aus den erfassten Fehlern.
            kennzahlen = {
                "wortzahl_original": diktat["wortzahl"],
                "fehlerquote_prozent": (
                    round(100.0 * len(fehler) / diktat["wortzahl"], 1)
                    if diktat["wortzahl"] else None
                ),
            }
        elif diktat["schuelertext"]:
            kennzahlen = diffing.kennzahlen(diktat["text_original"],
                                            diktat["schuelertext"])
        else:
            kennzahlen = {"wortzahl_original": diktat["wortzahl"],
                          "fehlerquote_prozent": None}
        pfad = config.EXPORT_DIR / (
            f"Infoblatt_{schueler['id']}_{diktat['datum']}_{diktat['id']}.docx"
        )
        anhang = diktat["schuelertext"] if ist_frei else diktat["text_original"]
        docx_export.informationsblatt_schreiben(
            pfad, g.anzeigename(con, schueler), diktat["titel"], diktat["datum"],
            [dict(f) for f in fehler], reg, kennzahlen, kommentar,
            anhang if mit_text else "", art=diktat["art"],
        )
        with open(pfad, "rb") as datei:
            st.download_button(
                "Informationsblatt herunterladen", datei.read(), file_name=pfad.name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        st.success(f"Erzeugt: `{pfad}`")
