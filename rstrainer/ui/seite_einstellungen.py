"""Seite: Einstellungen, OLFA-Liste, Testmodus und Datenexport."""

from __future__ import annotations

import streamlit as st

from .. import auftraege, config, db, demo_data, export, olfa, olfa_engine, taxonomie
from . import gemeinsam as g


def zeichnen(con) -> None:
    st.header("Einstellungen")
    (reiter_allg, reiter_olfa, reiter_lex, reiter_test, reiter_arten,
     reiter_demo, reiter_export) = st.tabs(
        ["⚙️ Allgemein", "📖 OLFA-Kategorien", "📚 Zielwort-Lexikon", "✅ Testlauf",
         "🌱 Gelernte Fehlerarten", "🧪 Testmodus", "💾 Datenexport"]
    )
    with reiter_allg:
        _allgemein(con)
    with reiter_olfa:
        _olfa(con)
    with reiter_lex:
        _lexikon(con)
    with reiter_test:
        _testlauf(con)
    with reiter_arten:
        _fehlerarten(con)
    with reiter_demo:
        _testmodus(con)
    with reiter_export:
        _export(con)


def _allgemein(con) -> None:
    st.subheader("Namen auf Ausdrucken")
    st.markdown(
        "Was als **Anzeigename** im Profil steht, erscheint auch auf "
        "Übungsblättern, Informationsblättern und Berichten. Es gibt bewusst "
        "kein zweites Kürzelfeld: Ein Blatt landet schnell im Lehrerzimmer, im "
        "Drucker oder im Papierkorb. Wer den Klarnamen dort nicht haben will, "
        "trägt schon im Profil ein Pseudonym ein – dann gibt es gar keine Datei "
        "mit dem Klarnamen darin."
    )

    st.divider()
    st.subheader("Rechtschreibung")
    st.markdown(
        "Zielnorm ist die **Schweizer Standardorthografie (de-CH)**: kein ß, "
        "durchgehend ss. Eine Umschaltung gibt es nicht. Nach der Ergänzung zum "
        "technischen Manual (A.3) sind **13 = s für ss** und **15 = ss für s** neu "
        "belegt – jeweils nach langem Vokal oder Diphthong (Fuss, Strasse, Preise), "
        "Förderbereich F3. Entscheidend ist die Vokallänge vor der s-Stelle: kurz "
        "heisst Schärfung (07/08). **14, 16, 21, 22** werden nie vergeben; ein "
        "fälschlich gesetztes ß ist ein Konsonantenersatz (33)."
    )
    gesperrt = [k for k in g.kategorienliste() if k.gesperrt]
    if gesperrt:
        for k in gesperrt:
            st.caption(f"🔒 **{k.nr} – {k.name}** — {k.grund}")

    st.divider()
    st.subheader("Speicherorte")
    st.code(
        f"Datenbank:        {config.DB_PFAD}\n"
        f"Exporte:          {config.EXPORT_DIR}\n"
        f"Kategorienliste:  {g.kategorienliste().quelle}\n"
        f"Gelernte Arten:   {taxonomie.dateipfad()}",
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
            "gesperrt": st.column_config.CheckboxColumn(
                "gesperrt",
                help="Nicht wählbar und für das Sprachmodell verboten. Die "
                     "Nummer bleibt erhalten, damit die Zählung stimmt."),
            "grund": st.column_config.TextColumn("Grund der Sperre"),
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
                    gesperrt=bool(zeile.get("gesperrt", False)),
                    grund=str(zeile.get("grund") or ""),
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


def _lexikon(con) -> None:
    """Zielwort-Lexikon: Merkmale, die sich nicht aus der Schreibung ableiten
    lassen (Manual §3, Ergänzung A.4). Ab dem Eintrag ist die Klassifikation
    für dieses Wort rein deterministisch."""
    st.subheader("Zielwort-Lexikon")
    st.caption(
        "Vokallänge bei unmarkierten Wörtern (Tal lang, Bus kurz), Morphemgrenzen "
        "(Fahr|rad), Lautwert eines v (Vogel /f/, Vase /v/), Umlautwort ja/nein. "
        f"{len(olfa_engine.VORGABE_LEXIKON)} Wörter sind als Vorgabe mitgeliefert; "
        "eigene Einträge gelten für alle Profile."
    )
    with st.form("lexikon_form", clear_on_submit=True):
        spalten = st.columns(2)
        wort = spalten[0].text_input("Wort *", placeholder="z. B. Nuss")
        vokale = spalten[1].text_input("Vokale (je Vokal kurz / lang / ?)", placeholder="kurz  oder  lang,kurz")
        spalten = st.columns(3)
        morpheme = spalten[0].text_input("Morpheme (Grenze als |)", placeholder="Fahr|rad")
        v = spalten[1].selectbox("v gesprochen als", ["–", "f", "v"])
        umlaut = spalten[2].selectbox("Umlautwort", ["–", "ja", "nein"])
        if st.form_submit_button("Eintrag speichern", type="primary"):
            if not wort.strip():
                st.error("Bitte ein Wort angeben.")
            else:
                vok = [x.strip().lower() for x in vokale.replace("/", ",").split(",") if x.strip()]
                vok = [x if x in ("kurz", "lang") else "?" for x in vok] or None
                eintrag = {"vokale": vok, "morpheme": morpheme.strip() or None,
                           "v": None if v == "–" else v,
                           "umlaut": None if umlaut == "–" else umlaut == "ja"}
                if not any(x is not None for x in eintrag.values()):
                    st.error("Bitte mindestens ein Merkmal angeben.")
                else:
                    db.lexikon_speichern(con, wort, eintrag)
                    g.merken(f"Lexikoneintrag «{wort}» gespeichert.")
                    st.rerun()

    eintraege = db.lexikon_laden(con)
    if not eintraege:
        st.info("Noch keine eigenen Einträge.")
        return
    import pandas as pd
    st.dataframe(pd.DataFrame([{
        "Wort": w, "Vokale": ", ".join(e["vokale"]) if e.get("vokale") else "",
        "Morpheme": e.get("morpheme") or "", "v": e.get("v") or "",
        "Umlaut": "" if e.get("umlaut") is None else ("ja" if e["umlaut"] else "nein"),
        "Quelle": e.get("quelle", ""),
    } for w, e in sorted(eintraege.items())]), hide_index=True, width="stretch")
    weg = st.selectbox("Eintrag löschen", ["–"] + sorted(eintraege), key="lexikon_loeschen")
    if weg != "–" and st.button("Löschen", key="lexikon_loeschen_knopf"):
        db.lexikon_loeschen(con, weg)
        g.merken(f"«{weg}» gelöscht.")
        st.rerun()


def _testlauf(con) -> None:
    """Manual §19: Die Minimalpaare als ausführbarer Test in der Oberfläche."""
    st.subheader("Goldstandard-Minimalpaare")
    st.caption(
        "Die Minimalpaare aus Manual §19, die CH-Fälle aus Ergänzung A.1/A.4 und "
        "die Beispiele aus Manual §1–§9 laufen gegen das Regelwerk. Kein späterer "
        "Umbau darf diese Tests verschlechtern – dieselbe Liste läuft auch in pytest."
    )
    if st.button("Testlauf starten", type="primary"):
        lexikon = dict(olfa_engine.VORGABE_LEXIKON)
        lexikon.update(g.lexikon())
        st.session_state["testlauf"] = (olfa_engine.testlauf(lexikon), olfa_engine.testlauf_text(lexikon))
    lauf = st.session_state.get("testlauf")
    if not lauf:
        return
    woerter, texte = lauf
    alle = woerter + texte
    ok = sum(1 for x in alle if x["ok"])
    (st.success if ok == len(alle) else st.error)(f"{ok} von {len(alle)} bestanden.")
    import pandas as pd
    st.dataframe(pd.DataFrame(
        [{"Fall": f"{x['s']} → {x['t']}", "Erwartet": " + ".join(x["erwartet"]),
          "Erhalten": " + ".join(x["erhalten"]) or "–", "Quelle": x["quelle"], "OK": "✓" if x["ok"] else "✗"}
         for x in woerter]
        + [{"Fall": x["schueler"], "Erwartet": " + ".join(x["erwartet"]),
            "Erhalten": " + ".join(x["erhalten"]) or "–", "Quelle": x["quelle"], "OK": "✓" if x["ok"] else "✗"}
           for x in texte]), hide_index=True, width="stretch")


def _fehlerarten(con) -> None:
    """Verwaltung der Arten, die das Sprachmodell selbst benannt hat.

    Angelegt werden sie ohne Rückfrage – das war ausdrücklich so gewollt. Der
    Preis dafür ist eine Sammlung, die wächst. Hier lässt sie sich wieder
    ordnen: umbenennen, zusammenlegen, löschen.
    """
    sammlung = g.sammlung()
    st.subheader("Vom Sprachmodell gelernte Fehlerarten")
    st.caption(
        "Alles, wofür die OLFA-Liste keine Kategorie hat – vor allem Grammatik. "
        "Die Arten entstehen bei der Analyse und werden ohne Rückfrage angelegt."
    )

    if not len(sammlung):
        st.info(
            "Noch keine gelernten Fehlerarten. Sie entstehen, sobald das "
            "Sprachmodell unter **Fehlererfassung** einen Text auswertet."
        )
        return

    ungesehen = sammlung.ungesehen
    if ungesehen:
        st.info(f"**{len(ungesehen)} Art(en)** sind neu und noch nicht angesehen.")

    for oberbegriff, arten in sorted(sammlung.nach_oberbegriff().items()):
        st.markdown(f"**{oberbegriff}**")
        for art in arten:
            with st.container(border=True):
                kopf, knopf = st.columns([5, 1])
                with kopf:
                    st.markdown(
                        ("🆕 " if art.neu else "") + f"**{art.label}**"
                        + f"  \n`{art.id}`"
                    )
                    if art.beschreibung:
                        st.caption(art.beschreibung)
                    anzahl = con.execute(
                        "SELECT COUNT(*) FROM fehler WHERE kategorie_nr = ?",
                        (art.id,),
                    ).fetchone()[0]
                    st.caption(f"{anzahl} zugeordnete Fehler · angelegt {art.angelegt}")
                with knopf:
                    if art.neu and st.button("Gesehen", key=f"gesehen_{art.id}"):
                        art.neu = False
                        g.sammlung_speichern(sammlung)
                        st.rerun()

    st.divider()
    _arten_umbenennen(con, sammlung)
    st.divider()
    _arten_zusammenlegen(con, sammlung)
    st.divider()
    _arten_aufraeumen(con, sammlung)


def _arten_umbenennen(con, sammlung) -> None:
    st.subheader("Umbenennen")
    namen = {a.id: a.label for a in sammlung}
    art_id = st.selectbox("Fehlerart", list(namen),
                          format_func=lambda i: namen[i], key="tax_umbenennen")
    art = sammlung.get(art_id)
    if art is None:
        return
    with st.form("tax_umbenennen_form"):
        spalten = st.columns(3)
        oberbegriff = spalten[0].selectbox(
            "Oberbegriff", taxonomie.OBERBEGRIFFE,
            index=taxonomie.OBERBEGRIFFE.index(art.oberbegriff)
            if art.oberbegriff in taxonomie.OBERBEGRIFFE else 0,
        )
        mitte = spalten[1].text_input(
            "Untergruppe", value=art.pfad[1] if len(art.pfad) > 1 else "")
        unten = spalten[2].text_input(
            "Genaue Art", value=art.pfad[2] if len(art.pfad) > 2 else "")
        beschreibung = st.text_input("Beschreibung", value=art.beschreibung)
        if st.form_submit_button("Umbenennen", type="primary"):
            pfad = [oberbegriff, mitte, unten]
            if not mitte.strip():
                st.error("Die Untergruppe darf nicht leer sein.")
            else:
                sammlung.umbenennen(art.id, pfad)
                art.beschreibung = beschreibung.strip()
                g.sammlung_speichern(sammlung)
                g.merken("Umbenannt.")
                st.rerun()


def _arten_zusammenlegen(con, sammlung) -> None:
    st.subheader("Zusammenlegen")
    st.caption(
        "Hängt alle Fehler der einen Art auf die andere um – **über alle "
        "Profile hinweg**, sonst zeigten die Einträge fremder Kinder ins Leere. "
        "Das lässt sich nicht rückgängig machen."
    )

    paare = sammlung.aehnliche_paare()
    if paare:
        st.markdown("**Möglicherweise doppelt**")
        for a, b, wert in paare[:10]:
            st.caption(f"{wert} % gemeinsame Wörter: «{a.label}» ↔ «{b.label}»")
        st.caption(
            "⚠️ Das ist nur ein Wortvergleich. «Dativ statt Akkusativ» und "
            "«Akkusativ statt Dativ» teilen alle Wörter und meinen das "
            "Gegenteil – deshalb wird hier nie automatisch zusammengelegt."
        )

    namen = {a.id: a.label for a in sammlung}
    with st.form("tax_zusammenlegen_form"):
        spalte_a, spalte_b = st.columns(2)
        von = spalte_a.selectbox("Verschwindet", list(namen),
                                 format_func=lambda i: namen[i], key="tax_von")
        nach = spalte_b.selectbox("Bleibt", list(namen),
                                  format_func=lambda i: namen[i], key="tax_nach")
        if st.form_submit_button("Zusammenlegen", type="primary"):
            if von == nach:
                st.error("Bitte zwei verschiedene Fehlerarten wählen.")
            else:
                anzahl = db.fehler_umhaengen(con, von, nach)
                sammlung.loeschen(von)
                g.sammlung_speichern(sammlung)
                g.merken(f"Zusammengelegt, {anzahl} Fehlereinträge umgehängt.")
                st.rerun()

    st.markdown("**Löschen**")
    st.caption(
        "Fehler dieser Art fallen auf die Auffangkategorie **37** zurück. "
        "Löschen Sie nur, was wirklich unbrauchbar ist – zusammenlegen erhält "
        "die Information."
    )
    weg = st.selectbox("Fehlerart löschen", list(namen),
                       format_func=lambda i: namen[i], key="tax_loeschen")
    if st.button("Endgültig löschen"):
        anzahl = db.fehler_umhaengen(con, weg, "37")
        sammlung.loeschen(weg)
        g.sammlung_speichern(sammlung)
        g.merken(f"Gelöscht, {anzahl} Fehlereinträge auf Kategorie 37 gesetzt.")
        st.rerun()


def _arten_aufraeumen(con, sammlung) -> None:
    st.subheader("Vom Sprachmodell aufräumen lassen")
    st.caption(
        "Das Modell, das die Arten benannt hat, kann sie auch wieder ordnen. "
        "Angewendet wird erst nach Ihrer Bestätigung: Anders als beim Anlegen "
        "ist ein Fehlgriff hier teuer, weil er bestehende Fehlerdaten umhängt."
    )

    if st.button("Aufräum-Prompt erzeugen"):
        st.session_state["tax_aufraeum_prompt"] = \
            auftraege.aufraeum_prompt_bauen(sammlung)
        st.rerun()

    prompt_text = st.session_state.get("tax_aufraeum_prompt")
    if not prompt_text:
        return
    st.code(prompt_text, language="markdown")

    roh = st.text_area("Antwort des Sprachmodells", height=180, key="tax_aufraeum_roh")
    if st.button("Vorschlag auswerten"):
        plan = auftraege.aufraeum_lesen(roh, sammlung)
        if plan.fehler:
            st.error(plan.fehler)
        elif plan.ist_leer:
            st.success("Das Modell sieht nichts, was zusammengehört oder anders heissen müsste.")
        else:
            st.session_state["tax_aufraeum_plan"] = plan
            st.rerun()

    plan = st.session_state.get("tax_aufraeum_plan")
    if plan is None:
        return

    with st.form("tax_aufraeum_form"):
        entscheidungen = []
        for i, x in enumerate(plan.zusammenlegen):
            haken = st.checkbox(
                f"Zusammenlegen: «{sammlung.label(x['von'])}» → "
                f"«{sammlung.label(x['nach'])}»"
                + (f" — {x['warum']}" if x["warum"] else ""),
                value=False, key=f"tax_plan_z_{i}",
            )
            entscheidungen.append(("zusammen", haken, x))
        for i, x in enumerate(plan.umbenennen):
            haken = st.checkbox(
                f"Umbenennen: «{sammlung.label(x['id'])}» → "
                f"«{' › '.join(x['pfad'])}»"
                + (f" — {x['warum']}" if x["warum"] else ""),
                value=False, key=f"tax_plan_u_{i}",
            )
            entscheidungen.append(("umbenennen", haken, x))

        st.caption(
            "Nichts ist vorausgewählt. Jede Zeile bewusst anhaken – "
            "eine zu Unrecht zusammengelegte Art zerstört die Statistik."
        )
        if st.form_submit_button("Angehakte anwenden", type="primary"):
            umgehaengt = 0
            geaendert = 0
            for art, haken, x in entscheidungen:
                if not haken:
                    continue
                if art == "zusammen":
                    umgehaengt += db.fehler_umhaengen(con, x["von"], x["nach"])
                    sammlung.loeschen(x["von"])
                else:
                    sammlung.umbenennen(x["id"], x["pfad"])
                geaendert += 1
            g.sammlung_speichern(sammlung)
            for key in ("tax_aufraeum_plan", "tax_aufraeum_prompt", "tax_aufraeum_roh"):
                st.session_state.pop(key, None)
            g.merken(f"{geaendert} Änderung(en) angewendet, "
                     f"{umgehaengt} Fehlereinträge umgehängt.")
            st.rerun()


def _testmodus(con) -> None:
    st.subheader("Testmodus mit Beispieldaten")
    st.markdown(
        "Legt drei **frei erfundene** Demoprofile mit Diktaten, freien Texten "
        "und Fehlern an. Damit lassen sich Abgleich, Empfehlungslogik, "
        "Trendanalyse und Docx-Export ausprobieren, ohne echte Schülerdaten "
        "anzufassen."
    )
    st.caption(
        "Die Demodaten sind mit einem festen Zufallsstartwert erzeugt und daher "
        "reproduzierbar. Die eingebauten Entwicklungen (abnehmend / stagnierend "
        "/ zunehmend) sollen genau so in der Auswertung erscheinen – wenn nicht, "
        "stimmt etwas mit der Trendberechnung nicht. Gelernte Fehlerarten legt "
        "der Testmodus keine an: Die stehen ausserhalb der Profile und blieben "
        "nach dem Entfernen der Demodaten stehen."
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

    reg = g.register()
    basis = str(schueler["id"])

    spalte_a, spalte_b, spalte_c = st.columns(3)
    with spalte_a:
        st.download_button(
            "Fehler als CSV", export.fehler_csv(con, schueler["id"], reg),
            file_name=f"fehler_{basis}.csv", mime="text/csv",
        )
    with spalte_b:
        st.download_button(
            "Texte als CSV", export.diktate_csv(con, schueler["id"]),
            file_name=f"texte_{basis}.csv", mime="text/csv",
        )
    with spalte_c:
        st.download_button(
            "Alles als JSON", export.gesamt_json(con, schueler["id"], reg),
            file_name=f"gesamt_{basis}.json", mime="application/json",
        )
    st.caption("CSV mit Semikolon als Trennzeichen – Excel öffnet das direkt richtig.")
