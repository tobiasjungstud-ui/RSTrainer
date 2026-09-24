"""Seite: Fehlererfassung – OLFA-Analyse, freie Analyse oder von Hand.

**OLFA-Analyse** klassifiziert deterministisch (rstrainer.olfa_engine) und hat
zwei wählbare Modi:

* *Diktatmodus* – der Schülertext wird gegen die Vorlage ausgerichtet. Was
  falsch ist, steht objektiv fest; kein Sprachmodell ist beteiligt.
* *Freitextmodus* – ohne Vorlage fehlt dieser Massstab. Das Sprachmodell wird
  deshalb genau eine Frage gefragt: Welches Wort war gemeint? Klassifiziert
  wird auch hier vom Regelwerk. Vorgeschaltet sind Prüfungen, die ohne Modell
  auskommen (ß ist in de-CH immer falsch; frühere Fehlschreibungen dieses
  Kindes), und ein optionaler blinder Zweitdurchgang. Was nur ein Durchgang
  gesehen hat oder worin sich die Durchgänge widersprechen, wird nicht als
  sicher ausgegeben, sondern zur Kontrolle vorgelegt.

**Freie Analyse durch das Sprachmodell** benennt zusätzlich, was die OLFA-Liste
nicht abdeckt – vor allem Grammatik – und legt dafür eigene Fehlerarten an.

**Von Hand** – für alles, was keiner dieser Wege sieht.

Was aus diesen Wegen kommt, ist immer nur ein Vorschlag. Bestätigt und
zugeordnet wird von der Lehrperson; nichts wird ungeprüft übernommen.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from .. import auftraege, config, db, diffing, olfa_engine, taxonomie
from ..kategorien import foerderbereich_von, schwerpunkte
from . import gemeinsam as g


def zeichnen(con, schueler) -> None:
    st.header("Fehlererfassung")

    diktate = db.diktat_liste(con, schueler["id"])
    if not diktate:
        st.info(
            "Für dieses Profil ist noch kein Text erfasst. Einen frei geschriebenen "
            "Schülertext können Sie gleich hier eingeben – er wird sofort zur Analyse "
            "ausgewählt. Ein Diktat mit Vorlage entsteht unter **Texte**."
        )
        _freitext_erfassen(con, schueler, aufklappbar=False)
        return

    # Streamlit kopiert Widget-Werte tief; sqlite3.Row lässt sich nicht picklen.
    # Deshalb immer nur die ID als Option übergeben und den Text nachschlagen.
    beschriftung = {
        d["id"]: f"{g.textart_symbol(d['art'])} {d['datum']} · {d['titel']}"
                 + (" · diktiert" if d["art"] == "diktiert" else "")
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
    _freitext_erfassen(con, schueler, aufklappbar=True)
    if diktat["art"] == "diktiert":
        st.info(
            "🎙️ **Diktierter Text (Sprachsoftware).** Die Rechtschreibung stammt vom Programm, "
            "nicht vom Kind – eine OLFA-Analyse würde das Bild verfälschen und ist hier abgeschaltet. "
            "Analysiert werden Satzbau, Grammatik, Zeichensetzung und Textebene (B–E), getrennt "
            "von den geschriebenen Texten."
        )
    reiter = st.tabs([
        "🔬 OLFA-Analyse",
        "🤖 Freie Analyse durch das Sprachmodell",
        "✍️ Fehler von Hand",
        "📋 Erfasste Fehler & Infoblatt",
    ])
    with reiter[0]:
        _olfa_ablauf(con, schueler, diktat)
    with reiter[1]:
        _analyse_ablauf(con, schueler, diktat)
    with reiter[2]:
        _von_hand(con, schueler, diktat)
    with reiter[3]:
        _fehlerliste(con, schueler, diktat)


# ---------------------------------------------------------------------------
# Freien Text gleich hier erfassen
# ---------------------------------------------------------------------------

def _freitext_erfassen(con, schueler, aufklappbar: bool) -> None:
    """Wer einen Schülertext auswerten will, soll ihn dort eingeben können, wo
    er ihn auswertet – nicht erst auf einer anderen Seite. Dieselbe Erfassung
    steht weiterhin unter «Texte»; sie legt denselben Datensatz an."""
    behaelter = (st.expander("📝 Weiteren freien Text erfassen")
                 if aufklappbar else st.container())
    with behaelter:
        if aufklappbar:
            st.caption(
                "Noch ein Schülertext ohne Vorlage? Hier eingeben, statt dafür auf "
                "die Seite «Texte» zu wechseln. Nach dem Speichern ist er oben "
                "ausgewählt."
            )
        else:
            st.caption(
                "Abtippen oder einfügen, speichern – danach steht der Text oben in "
                "der Auswahl und lässt sich im Freitextmodus auswerten."
            )
        with st.form(f"freitext_hier_{schueler['id']}", clear_on_submit=True):
            spalte_a, spalte_b = st.columns(2)
            with spalte_a:
                titel = st.text_input("Titel *", placeholder="z. B. «Aufsatz Herbstferien»")
            with spalte_b:
                datum = st.date_input("Datum", value=date.today())
            art = g.textart_wahl(f"fehler_art_{schueler['id']}")
            text = st.text_area("Text des Kindes *", height=200,
                                placeholder="Abgetippt oder eingefügt.")
            notiz = st.text_input("Notiz", placeholder="Auftrag, Umstände, Besonderes …")
            if st.form_submit_button("Text speichern und auswerten", type="primary"):
                if not titel.strip() or not text.strip():
                    st.error("Titel und Text sind Pflichtfelder.")
                else:
                    neue_id = db.diktat_anlegen(
                        con, schueler["id"], titel, "", datum=datum.isoformat(),
                        notiz=notiz, quelle=art, freigegeben=True,
                        art=art, schuelertext=text,
                    )
                    # Der neue Text ist der, den man gerade auswerten will.
                    st.session_state["fehler_diktat"] = neue_id
                    g.merken(f"Freier Text «{titel}» gespeichert und ausgewählt.")
                    st.rerun()


# ---------------------------------------------------------------------------
# OLFA-Analyse: Modus wählen
# ---------------------------------------------------------------------------

def hat_vorlage(diktat) -> bool:
    """Nur ein Text mit Vorlage kann im Diktatmodus ausgewertet werden."""
    return diktat["art"] != "freitext" and bool((diktat["text_original"] or "").strip())


def _olfa_ablauf(con, schueler, diktat) -> None:
    if diktat["art"] == "diktiert":
        st.warning(
            "Keine OLFA-Analyse für diktierte Texte: Klassische Rechtschreibfehler entstehen hier "
            "nicht oder kaum, weil die Sprachsoftware schreibt. Bitte den Reiter «Freie Analyse durch "
            "das Sprachmodell» für Satzbau und Grammatik verwenden."
        )
        return
    mit_vorlage = hat_vorlage(diktat)
    beschriftung = {
        "diktat": "📄 Diktatmodus – gegen die Vorlage",
        "freitext": "📝 Freitextmodus – ohne Vorlage",
    }
    modi = (["diktat", "freitext"] if mit_vorlage else ["freitext"])
    modus = st.radio(
        "Modus der Fehleranalyse", modi, format_func=beschriftung.get,
        horizontal=True, key=f"olfa_modus_{diktat['id']}",
        help=("Der Diktatmodus ist genauer, weil objektiv feststeht, was falsch "
              "ist. Er setzt eine Vorlage voraus."),
    )
    if not mit_vorlage:
        st.caption("Zu diesem Text gibt es keine Vorlage – nur der Freitextmodus "
                   "ist möglich.")
    elif modus == "freitext":
        st.warning(
            "Der Diktatmodus wäre hier genauer: Zu diesem Text gibt es eine "
            "Vorlage, gegen die sich jede Abweichung objektiv bestimmen lässt."
        )

    if modus == "diktat":
        _diff_ablauf(con, schueler, diktat)
    else:
        _freitext_ablauf(con, schueler, diktat)


# ---------------------------------------------------------------------------
# Schülertext – Grundlage aller drei Wege
# ---------------------------------------------------------------------------

def _schuelertext_feld(con, diktat, schluessel: str) -> str:
    ist_frei = diktat["art"] in db.OHNE_VORLAGE
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
    ist_frei = diktat["art"] in db.OHNE_VORLAGE
    ist_diktiert = diktat["art"] == "diktiert"
    st.caption(
        "Hier benennt das Sprachmodell die Fehler selbst – auch, was die "
        "OLFA-Liste nicht abdeckt, vor allem Grammatik. Wofür es keine Kategorie "
        "gibt, legt es eine an und ordnet sie hierarchisch ein "
        "(z. B. «Grammatik › Kasus › Dativ statt Akkusativ»). Für die "
        "Rechtschreibung ist die **OLFA-Analyse** genauer: Dort klassifiziert "
        "das Regelwerk, nicht das Modell."
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
                reg.liste, reg.sammlung, ohne_rechtschreibung=ist_diktiert,
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
            if ist_diktiert and not ergebnis.fehler:
                weg = [z for z in ergebnis.zeilen if reg.bereich(z.kategorie_nr) == "A"]
                ergebnis.zeilen = [z for z in ergebnis.zeilen if reg.bereich(z.kategorie_nr) != "A"]
                if weg:
                    st.info(f"{len(weg)} Rechtschreibbefund(e) verworfen – bei einem diktierten Text "
                            "zählt nur Satzbau, Grammatik, Zeichensetzung und Textebene.")
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
        _stufe_vier(ergebnis)
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

    _ereignisse_bestaetigen(con, schueler, diktat, ereignisse, schuelertext, "diff")


# ---------------------------------------------------------------------------
# Gemeinsame Darstellung der Fehlerereignisse
# ---------------------------------------------------------------------------

def _ereignisse_bestaetigen(con, schueler, diktat, ereignisse, schuelertext,
                            schluessel: str) -> None:
    """Dieselbe Liste für beide Modi – der Weg zum Zielwort unterscheidet sich,
    die Klassifikation und damit die Anzeige nicht."""
    st.divider()
    st.markdown(
        f"### {len(ereignisse)} Fehlerereignisse  \n"
        "Eindeutige zuerst, unsichere unten. Jede Zeile lässt sich umstufen – "
        "eine Umstufung wird als Muster gespeichert und beim nächsten gleichen "
        "Fall vorgeschlagen."
    )
    rang = {"resolved": 0, "resolved_by_area": 1, "resolved_by_ki": 2, "manual_review": 3}
    sortiert = sorted(ereignisse, key=lambda e: (rang.get(e["status"], 4), -(e.get("confidence") or 0)))
    saetze = olfa_engine.saetze(schuelertext)
    _bestaetigungsliste(
        con, schueler, diktat,
        [
            {
                "wort_original": e["targetForm"], "wort_schueler": e["studentForm"],
                "kontext": (saetze[e["sentenceIndex"]]
                            if e["sentenceIndex"] < len(saetze) else ""),
                "darstellung": f"{e['studentForm']} → {e['targetForm']}  "
                               f"⟨{e['studentGrapheme'] or '∅'}⟩ für ⟨{e['targetGrapheme'] or '∅'}⟩",
                "vorgabe": e["kategorie"], "vorschlaege": [],
                "begruendung": e["reason"], "neue_art": None,
                "ereignis": e,
            }
            for e in sortiert
        ],
        schluessel=schluessel,
    )


# ---------------------------------------------------------------------------
# Freitextmodus: Stufe 1 per Sprachmodell, Stufe 2 deterministisch
# ---------------------------------------------------------------------------

def _stufe_vier(ergebnis) -> None:
    """Stufe 4 ohne Modell: Konsequenzprüfung, dann bleibt Offenes offen."""
    for e in ergebnis["ereignisse"]:
        if e["status"] == "needs_context":
            olfa_engine.konsequenz_pruefen(e)
            if e["status"] == "needs_context":
                e["status"] = "manual_review"
            olfa_engine.konfidenz(e, {"zielwortSicherheit": e.get("zielwortSicherheit", 1)})


def _freitext_ablauf(con, schueler, diktat) -> None:
    st.caption(
        "Ohne Vorlage muss zuerst feststehen, welches Wort gemeint war. Genau "
        "danach – und nach nichts anderem – wird das Sprachmodell gefragt. Die "
        "Kategorie bestimmt anschliessend dasselbe Regelwerk wie im Diktatmodus. "
        "Ein zweiter, blinder Durchgang ist freiwillig; er entscheidet nur mit "
        "darüber, wie sicher eine Zielform ist."
    )

    schuelertext = _schuelertext_feld(con, diktat, "frei_text")
    if not schuelertext.strip():
        return

    bekannt = auftraege.bekannte_fehlschreibungen(db.fehler_liste(con, schueler["id"]))
    regeln = auftraege.regelfunde(schuelertext, bekannt)
    if regeln:
        st.info(
            f"**{len(regeln)} Fund(e) ohne Sprachmodell** – sie stehen fest, "
            "unabhängig von jeder Antwort:\n"
            + "\n".join(
                f"- «{r['student']}» → «{r['target']}» "
                + ("(in de-CH gibt es kein ß)" if r["herkunft"] == "regel"
                   else "(von diesem Kind schon einmal so geschrieben)")
                for r in regeln)
        )

    st.divider()
    st.subheader("Schritt 1 · Zielwörter bestimmen lassen")
    if st.button("Zielwort-Prompt erzeugen", type="primary",
                 key=f"frei_prompt_{diktat['id']}"):
        db.diktat_aktualisieren(con, diktat["id"], schuelertext=schuelertext)
        st.session_state[f"frei_prompt_1_{diktat['id']}"] = \
            auftraege.zielwort_prompt_bauen(schuelertext, 1)
        st.session_state[f"frei_prompt_2_{diktat['id']}"] = \
            auftraege.zielwort_prompt_bauen(schuelertext, 2)
        st.rerun()

    prompt_1 = st.session_state.get(f"frei_prompt_1_{diktat['id']}")
    if not prompt_1:
        return
    st.code(prompt_1, language="markdown")
    st.caption("In einen Claude-Chat einfügen und das JSON-Array zurückkopieren.")

    st.divider()
    st.subheader("Schritt 2 · Antwort einfügen")
    roh_1 = st.text_area("Antwort Durchgang 1", height=200,
                         key=f"frei_roh_1_{diktat['id']}")

    with st.expander("Zweiter, blinder Durchgang (empfohlen)",
                     expanded=not st.session_state.get(f"frei_roh_2_{diktat['id']}")):
        st.caption(
            "Denselben Text in einem **neuen, leeren** Chat auswerten lassen – "
            "anders formuliert, damit die zweite Antwort nicht die erste "
            "abschreibt. Wo beide Durchgänge dieselbe Zielform nennen, ist sie "
            "belastbar; wo sie sich widersprechen, geht der Fall zur Kontrolle."
        )
        st.code(st.session_state.get(f"frei_prompt_2_{diktat['id']}", ""),
                language="markdown")
        roh_2 = st.text_area("Antwort Durchgang 2", height=200,
                             key=f"frei_roh_2_{diktat['id']}")

    if st.button("Zielwörter auswerten", key=f"frei_lesen_{diktat['id']}"):
        if not (roh_1 or "").strip():
            st.warning("Die Antwort aus Durchgang 1 fehlt noch.")
        else:
            try:
                d1 = auftraege.zielwoerter_lesen(roh_1)
                d2 = auftraege.zielwoerter_lesen(roh_2) if (roh_2 or "").strip() else None
            except ValueError as fehler:
                st.error(f"{fehler} Bitte nur das JSON-Array einfügen.")
            else:
                liste = auftraege.zielwoerter_vereinen(regeln, d1, d2)
                lexikon = dict(olfa_engine.VORGABE_LEXIKON)
                lexikon.update(g.lexikon())
                ergebnis = olfa_engine.analysiere_liste(
                    liste, schuelertext, lexikon, g.muster(schueler["id"]), quelle="ki")
                _stufe_vier(ergebnis)
                ergebnis["durchgaenge"] = 2 if d2 is not None else 1
                st.session_state[f"frei_ergebnis_{diktat['id']}"] = ergebnis
                st.rerun()

    ergebnis = st.session_state.get(f"frei_ergebnis_{diktat['id']}")
    if ergebnis is None:
        return

    ereignisse = ergebnis["ereignisse"]
    offen_woerter = [a for a in ergebnis["abdeckung"] if a["status"] == "offen"]
    spalten = st.columns(4)
    spalten[0].metric("Wörter im Text", len(ergebnis["abdeckung"]))
    spalten[1].metric("Fehlerereignisse", len(ereignisse))
    spalten[2].metric("Manuelle Kontrolle",
                      sum(1 for e in ereignisse if e["status"] == "manual_review"))
    spalten[3].metric("Durchgänge", ergebnis.get("durchgaenge", 1))

    st.caption(
        f"Ohne Vorlage gilt kein Wort als geprüft, nur weil eine Liste vorliegt: "
        f"{len(offen_woerter)} von {len(ergebnis['abdeckung'])} Wörtern sind nicht "
        "als fehlerhaft gemeldet worden – das heisst nicht, dass sie geprüft "
        "wurden."
        + (" Verworfen: " + "; ".join(
            f"«{v.get('student') or v.get('target')}» – {v['grund']}"
            for v in ergebnis["verworfen"]) + "."
           if ergebnis["verworfen"] else "")
    )
    if ergebnis.get("durchgaenge", 1) == 1:
        st.caption(
            "Nur ein Durchgang: Die Sicherheit jeder Zielform, die vom Modell "
            "kommt, ist deshalb auf 0.80 gedeckelt und liegt damit unter der "
            "Schwelle {schwelle} – diese Zeilen kommen zur Kontrolle, statt eine "
            "Genauigkeit zu behaupten, die ein einzelner Durchgang nicht hergibt. "
            "Ein zweiter, blinder Durchgang hebt den Deckel.".format(
                schwelle=olfa_engine.ZIELWORT_SCHWELLE)
        )

    if not ereignisse:
        st.success("Es wurde kein Fehler gemeldet.")
        return

    _ereignisse_bestaetigen(con, schueler, diktat, ereignisse, schuelertext, "frei")


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
                f"analyse_prompt_text_{diktat['id']}", f"analyse_roh_{diktat['id']}",
                f"frei_ergebnis_{diktat['id']}", f"frei_prompt_1_{diktat['id']}",
                f"frei_prompt_2_{diktat['id']}"):
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
    optionen = [nr for nr, _ in reg.waehlbar()
                if diktat["art"] != "diktiert" or reg.bereich(nr) != "A"]
    if diktat["art"] == "diktiert":
        st.caption("Diktierter Text: nur Kategorien der Bereiche B–E wählbar.")
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
    ist_frei = diktat["art"] in db.OHNE_VORLAGE
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
    format_ = g.formatwahl(f"info_format_{diktat['id']}")
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
        endung = g.FORMATE[format_]["endung"]
        pfad = config.EXPORT_DIR / (
            f"Infoblatt_{schueler['id']}_{diktat['datum']}_{diktat['id']}.{endung}"
        )
        anhang = diktat["schuelertext"] if ist_frei else diktat["text_original"]
        g.export_modul(format_).informationsblatt_schreiben(
            pfad, g.anzeigename(con, schueler), diktat["titel"], diktat["datum"],
            [dict(f) for f in fehler], reg, kennzahlen, kommentar,
            anhang if mit_text else "", art=diktat["art"],
        )
        with open(pfad, "rb") as datei:
            st.download_button(
                f"Informationsblatt als {endung.upper()} herunterladen",
                datei.read(), file_name=pfad.name, mime=g.FORMATE[format_]["mime"],
            )
        st.success(f"Erzeugt: `{pfad}`")
