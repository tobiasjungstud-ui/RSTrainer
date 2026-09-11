"""Seite: Einstellungen, OLFA-Liste, Testmodus und Datenexport."""

from __future__ import annotations

import streamlit as st

from .. import config, db, demo_data, export, olfa
from . import gemeinsam as g


def zeichnen(con) -> None:
    st.header("Einstellungen")
    reiter_allg, reiter_olfa, reiter_demo, reiter_export = st.tabs(
        ["⚙️ Allgemein", "📖 OLFA-Kategorien", "🧪 Testmodus", "💾 Datenexport"]
    )
    with reiter_allg:
        _allgemein(con)
    with reiter_olfa:
        _olfa(con)
    with reiter_demo:
        _testmodus(con)
    with reiter_export:
        _export(con)


def _allgemein(con) -> None:
    st.subheader("Namen auf Ausdrucken")
    st.markdown(
        "**Empfehlung: Kürzel/Pseudonym.** Es geht um Daten minderjähriger "
        "Schüler:innen. Ein Übungsblatt landet schnell im Lehrerzimmer, im "
        "Drucker oder im Papierkorb. Mit einem Kürzel ist der Bezug zur Person "
        "nur für Sie selbst herstellbar. Für ein Elterngespräch lässt sich der "
        "Klarname jederzeit kurz einschalten."
    )
    aktuell = g.namensmodus(con)
    modus = st.radio(
        "Was erscheint auf Übungsblättern, Informationsblättern und Berichten?",
        ["kuerzel", "klarname"],
        index=0 if aktuell == "kuerzel" else 1,
        format_func=lambda m: ("Kürzel / Pseudonym (empfohlen)"
                               if m == "kuerzel" else "Klarname"),
    )
    if modus != aktuell:
        db.einstellung_setzen(con, g.NAMENSMODUS_SCHLUESSEL, modus)
        g.merken("Gespeichert.")

    st.divider()
    st.subheader("Rechtschreibvariante")
    st.caption(
        "Bestimmt, welche Vorgabe in den Chat-Prompts steht. Die Voreinstellung "
        "ist die Schweizer Variante ohne ß."
    )
    aktuelle_variante = g.rechtschreibvariante(con)
    variante = st.radio(
        "Variante", ["schweiz", "deutschland_oesterreich"],
        index=0 if aktuelle_variante == "schweiz" else 1,
        format_func=lambda v: ("Schweiz (immer ss, kein ß)" if v == "schweiz"
                               else "Deutschland / Österreich (mit ß)"),
    )
    if variante != aktuelle_variante:
        db.einstellung_setzen(con, g.VARIANTE_SCHLUESSEL, variante)
        st.success("Gespeichert.")

    st.divider()
    st.subheader("Speicherorte")
    st.code(
        f"Datenbank:        {config.DB_PFAD}\n"
        f"Exporte:          {config.EXPORT_DIR}\n"
        f"Kategorienliste:  {g.kategorienliste().quelle}",
        language="text",
    )
    g.datenschutz_fussnote()


def _olfa(con) -> None:
    import pandas as pd

    liste = g.kategorienliste()

    ohne_gruppe = sum(1 for k in liste if k.gruppe is None)
    if ohne_gruppe:
        st.info(
            f"Bei {ohne_gruppe} von {len(liste)} Kategorien fehlt noch die "
            "Entwicklungsgruppe **I / II / III**. Diese Angabe lag nicht vor "
            "und wurde bewusst nicht geraten. Sie steht auf dem "
            "Auswertungsbogen als Farbe der Kategorienummer (rot = I, "
            "gelb = II, grün = III) und lässt sich unten in der Spalte "
            "«Gruppe» nachtragen. Die App funktioniert auch ohne."
        )

    if liste.anzahl_ungeprueft:
        st.error(
            f"**{liste.anzahl_ungeprueft} von {len(liste)} Kategorien sind noch "
            "nicht als geprüft markiert.** Die mitgelieferte Liste ist ein "
            "Platzhalter und nicht die offizielle OLFA-Liste – bitte gegen Ihr "
            "Fachmaterial abgleichen und danach die Spalte «geprueft» anhaken."
        )
    else:
        st.success("Alle Kategorien sind als geprüft markiert.")

    with st.expander("Herkunft dieser Liste – bitte einmal lesen", expanded=False):
        for zeile in liste.meta.get("herkunft", []):
            st.markdown(f"- {zeile}")
        if liste.meta.get("lesehilfe"):
            st.markdown(f"**Lesehilfe:** {liste.meta['lesehilfe']}")
        if liste.meta.get("offene_punkte"):
            st.markdown("**Offene Punkte**")
            for zeile in liste.meta["offene_punkte"]:
                st.markdown(f"- {zeile}")

    st.divider()
    st.subheader("Kategorien bearbeiten")
    st.caption(
        "Nummern, Namen, Beschreibungen und Beispiele lassen sich direkt "
        "ändern. Die Spalte **heuristik** steuert die automatischen "
        "Kategorie-Vorschläge beim Abgleich – beim Umbenennen bitte stehen "
        "lassen."
    )

    tabelle = pd.DataFrame([k.as_dict() for k in liste])
    tabelle["heuristik"] = tabelle["heuristik"].apply(lambda x: ", ".join(x))
    # Leere Gruppen als leere Zelle zeigen, nicht als "None".
    tabelle["gruppe"] = tabelle["gruppe"].fillna("")
    bearbeitet = st.data_editor(
        tabelle, hide_index=True, width="stretch", num_rows="dynamic",
        key="olfa_editor",
        column_config={
            "nr": st.column_config.TextColumn("Nr.", width="small"),
            "name": st.column_config.TextColumn("Bezeichnung", width="medium"),
            "kurzbeschreibung": st.column_config.TextColumn("Kurzbeschreibung",
                                                            width="large"),
            "beispiel": st.column_config.TextColumn("Beispiel"),
            "gruppe": st.column_config.SelectboxColumn(
                "Gruppe", options=["", "I", "II", "III"],
                help="Entwicklungsgruppe laut Auswertungsbogen (rot = I, "
                     "gelb = II, grün = III). Noch nicht hinterlegt."),
            "bereich": st.column_config.TextColumn("Bereich"),
            "heuristik": st.column_config.TextColumn("heuristik (technisch)"),
            "geprueft": st.column_config.CheckboxColumn("geprüft"),
        },
    )

    spalte_a, spalte_b = st.columns(2)
    with spalte_a:
        if st.button("Änderungen speichern", type="primary"):
            neue = []
            for _, zeile in bearbeitet.iterrows():
                nr = str(zeile["nr"]).strip()
                if not nr:
                    continue
                neue.append(olfa.Kategorie(
                    nr=nr,
                    name=str(zeile["name"] or "").strip(),
                    kurzbeschreibung=str(zeile["kurzbeschreibung"] or ""),
                    beispiel=str(zeile["beispiel"] or ""),
                    gruppe=(str(zeile["gruppe"]).strip() or None
                            if zeile["gruppe"] else None),
                    bereich=str(zeile["bereich"] or "Sonstiges"),
                    heuristik=tuple(
                        t.strip() for t in str(zeile["heuristik"] or "").split(",")
                        if t.strip()
                    ),
                    geprueft=bool(zeile["geprueft"]),
                ))
            nummern = [k.nr for k in neue]
            if len(set(nummern)) != len(nummern):
                st.error("Es gibt doppelte Kategorienummern. Bitte korrigieren.")
            elif not neue:
                st.error("Die Liste darf nicht leer sein.")
            else:
                meta = dict(liste.meta)
                meta["status"] = (
                    "Von der Lehrperson bearbeitet."
                    if all(k.geprueft for k in neue)
                    else "Teilweise noch ungeprüft."
                )
                pfad = olfa.speichern(
                    olfa.Kategorienliste(kategorien=neue, meta=meta)
                )
                g.kategorien_neu_laden()
                g.merken(f"Gespeichert unter `{pfad}`.")
                st.rerun()
    with spalte_b:
        if st.button("Auf mitgelieferte Vorlage zurücksetzen"):
            if config.OLFA_DATEI_LOKAL.exists():
                config.OLFA_DATEI_LOKAL.unlink()
            g.kategorien_neu_laden()
            g.merken("Zurückgesetzt.")
            st.rerun()


def _testmodus(con) -> None:
    st.subheader("Testmodus mit Beispieldaten")
    st.markdown(
        "Legt drei **frei erfundene** Demoprofile mit Diktaten und Fehlern an. "
        "Damit lassen sich Abgleich, Empfehlungslogik, Trendanalyse und "
        "Docx-Export ausprobieren, ohne echte Schülerdaten anzufassen."
    )
    st.caption(
        "Die Demodaten sind mit einem festen Zufallsstartwert erzeugt und daher "
        "reproduzierbar. Die eingebauten Entwicklungen (abnehmend / stagnierend "
        "/ zunehmend) sollen genau so in der Auswertung erscheinen – wenn nicht, "
        "stimmt etwas mit der Trendberechnung nicht."
    )

    vorhanden = demo_data.demodaten_vorhanden(con)
    if vorhanden:
        st.info("Demodaten sind vorhanden (erkennbar am Präfix «DEMO – »).")

    spalte_a, spalte_b = st.columns(2)
    with spalte_a:
        if st.button("Demodaten anlegen", type="primary", disabled=vorhanden):
            ids = demo_data.demodaten_anlegen(con)
            g.merken(f"{len(ids)} Demoprofile angelegt.")
            st.rerun()
    with spalte_b:
        if st.button("Demodaten entfernen", disabled=not vorhanden):
            anzahl = demo_data.demodaten_entfernen(con)
            if st.session_state.get("schueler_id"):
                schueler = db.schueler_holen(con, st.session_state["schueler_id"])
                if schueler is None:
                    st.session_state.pop("schueler_id", None)
            g.merken(f"{anzahl} Demoprofile entfernt.")
            st.rerun()


def _export(con) -> None:
    st.subheader("Rohdaten exportieren")
    st.warning(
        "Exportdateien enthalten personenbezogene Daten. Sie landen in "
        f"`{config.EXPORT_DIR}` und gehören nicht in ein Repository, keinen "
        "Cloud-Ordner und keinen E-Mail-Anhang ohne Verschlüsselung."
    )

    profile = db.schueler_liste(con)
    if not profile:
        st.info("Keine Profile vorhanden.")
        return

    namen = {s["id"]: s["anzeigename"] for s in profile}
    schueler_id = st.selectbox("Profil", list(namen),
                               format_func=lambda i: namen[i],
                               key="export_profil")
    schueler = db.schueler_holen(con, schueler_id) if schueler_id else None
    if schueler is None:
        return

    liste = g.kategorienliste()
    basis = f"{schueler['kuerzel'] or schueler['id']}"

    spalte_a, spalte_b, spalte_c = st.columns(3)
    with spalte_a:
        st.download_button(
            "Fehler als CSV", export.fehler_csv(con, schueler["id"], liste),
            file_name=f"fehler_{basis}.csv", mime="text/csv",
        )
    with spalte_b:
        st.download_button(
            "Diktate als CSV", export.diktate_csv(con, schueler["id"]),
            file_name=f"diktate_{basis}.csv", mime="text/csv",
        )
    with spalte_c:
        st.download_button(
            "Alles als JSON", export.gesamt_json(con, schueler["id"], liste),
            file_name=f"gesamt_{basis}.json", mime="application/json",
        )
    st.caption("CSV mit Semikolon als Trennzeichen – Excel öffnet das direkt richtig.")
