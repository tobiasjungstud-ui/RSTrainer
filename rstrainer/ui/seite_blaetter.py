"""Seite: Übungsblätter und Mini-Tests.

Ablauf: Förderschwerpunkte und drei Regler (Niveau, Umfang, Übungsebene) →
Förderplan aus Kompetenzwert und Lernwörtern des Kindes → Prompt → Antwort
als Aufgabenliste → jede Aufgabe einzeln ansehen, prüfen, von Hand ändern
oder mit einem Chip-Prompt überarbeiten/austauschen → Freigabe mit zwei
ausdrücklichen Rückfragen → Export.
"""

from __future__ import annotations

import json
from datetime import date

import streamlit as st

from .. import analysis, auftraege, blatt, config, db, validation
from ..olfa_engine import FOERDERBEREICHE
from . import gemeinsam as g

SCHWIERIGKEITEN = {
    "leicht": "leicht — 7. Klasse",
    "mittel": "mittel — 8. Klasse",
    "anspruchsvoll": "anspruchsvoll — 9. Klasse",
}


def zeichnen(con, schueler) -> None:
    st.header("Übungsblätter und Mini-Tests")
    reiter_neu, reiter_archiv = st.tabs(["🪄 Neues Blatt", "📚 Archiv & Export"])
    with reiter_neu:
        _neues_blatt(con, schueler)
    with reiter_archiv:
        _archiv(con, schueler)


# ---------------------------------------------------------------------------
# Empfehlung + Prompt
# ---------------------------------------------------------------------------

def _empfehlungen_holen(con, schueler) -> list[analysis.Empfehlung]:
    diktate = db.diktat_liste(con, schueler["id"])
    punkte = [
        analysis.Diktatpunkt(d["id"], d["datum"], d["titel"], d["wortzahl"],
                             tuple(g.json_liste(d["ziel_kategorien"])))
        for d in diktate
    ]
    fehler = [dict(f) for f in db.fehler_liste(con, schueler["id"])]
    return analysis.empfehlungen(punkte, fehler)


def _fehler_und_woerter(con, schueler) -> tuple[list[dict], int]:
    fehler = [dict(f) for f in db.fehler_liste(con, schueler["id"])]
    woerter = sum(int(d["wortzahl"] or 0) for d in db.diktat_liste(con, schueler["id"]))
    return fehler, woerter


def _plan_aus_state(con, schueler) -> blatt.Foerderplan | None:
    roh = st.session_state.get("blatt_plan")
    if not roh:
        return None
    fehler, woerter = _fehler_und_woerter(con, schueler)
    return blatt.foerderplan(roh["bereiche"], fehler, woerter, anspruch=roh["anspruch"],
                             umfang=roh["umfang"], ebene=roh["ebene"])


def _foerderplan_anzeigen(plan: blatt.Foerderplan, reg) -> None:
    ebene = blatt.EBENEN[plan.ebene]
    kw = "–" if plan.kw is None else f"{plan.kw:g}"
    st.markdown(f"**Übungsebene: {ebene['name']}** (Kompetenzwert {kw}) – {plan.ebene_grund}")
    st.caption("Erlaubte Formate: " + ", ".join(blatt.FORMATE[f]["name"] for f in plan.formate)
               + (" · nicht vorgesehen: " + ", ".join(blatt.FORMATE[f]["name"] for f in plan.verboten) if plan.verboten else ""))
    for bereich in plan.bereiche:
        ws = plan.lernwoerter.get(bereich, [])
        fb = FOERDERBEREICHE.get(bereich, {})
        text = ", ".join(f"{w.ziel} ({w.anzahl}×)" for w in ws) or "noch keine Fehlwörter erfasst"
        st.markdown(f"- **{bereich} · {fb.get('name', '')}** – Strategie: {fb.get('foerdern', '')}. Lernwörter: {text}")


def _neues_blatt(con, schueler) -> None:
    reg = g.register()

    st.subheader("Schritt 1 · Förderschwerpunkte und drei Regler")
    vorschlaege = _empfehlungen_holen(con, schueler)
    if vorschlaege:
        st.markdown("**Vorschlag des Tools**")
        for e in vorschlaege:
            with st.container(border=True):
                st.markdown(
                    f"**{reg.label(e.kategorie_nr)}** {e.trend.symbol} "
                    f"*{e.trend.text}* · Priorität {e.punktzahl}"
                )
                st.caption(e.begruendung)
        vorauswahl = [e.kategorie_nr for e in vorschlaege]
    else:
        st.info(
            "Noch keine Empfehlung möglich – dafür braucht es erfasste Fehler. "
            "Sie können die Themen unten trotzdem selbst wählen."
        )
        vorauswahl = []

    fehler, woerter = _fehler_und_woerter(con, schueler)
    with st.form("blatt_prompt"):
        kategorien = g.kategorien_auswahl(
            reg, "Förderschwerpunkte (1–3)", vorauswahl=vorauswahl,
            schluessel="blatt_kategorien", hoechstens=3,
        )
        sp = st.columns(3)
        schwierigkeit = sp[0].selectbox(
            "Niveau", list(SCHWIERIGKEITEN), index=1, format_func=lambda x: SCHWIERIGKEITEN[x],
            help="Was die Aufgabe verlangt: Wortmaterial, Stützung, Leistungsart.")
        umfang = sp[1].selectbox(
            "Umfang", list(blatt.UMFANG), index=1,
            format_func=lambda u: {"kurz": "kurz – 2 je Bereich, Test 4", "normal": "normal – 3 je Bereich, Test 6",
                                   "lang": "lang – 4 je Bereich, Test 8"}[u])
        ebene = sp[2].selectbox(
            "Übungsebene", ["auto", "lautebene", "gemischt", "regelebene"], index=0,
            format_func=lambda e: "automatisch nach Kompetenzwert (S. 36)" if e == "auto" else blatt.EBENEN[e]["name"],
            help="Lautebene: Gliedern, Hören, Lernwörter – keine Fehlschreibungen vorzeigen. Regelebene: Fehlersuche, Begründen, Produktion.")
        if st.form_submit_button("Förderplan und Prompt erzeugen", type="primary"):
            if not kategorien:
                st.error("Bitte mindestens einen Förderschwerpunkt wählen.")
            else:
                bereiche = []
                for nr in kategorien:
                    fb = blatt.bereich_von(nr)
                    if fb and fb not in bereiche:
                        bereiche.append(fb)
                if not bereiche:
                    st.error("Die gewählten Kategorien liegen ausserhalb der Rechtschreibung (Bereich A) – für sie gibt es kein OLFA-Übungsblatt.")
                    return
                plan = blatt.foerderplan(bereiche, fehler, woerter, anspruch=schwierigkeit, umfang=umfang,
                                         ebene=None if ebene == "auto" else ebene)
                st.session_state["blatt_plan"] = {"bereiche": bereiche, "anspruch": schwierigkeit, "umfang": umfang,
                                                  "ebene": None if ebene == "auto" else ebene}
                zeit = {"kurz": "15 Minuten", "normal": "20 Minuten", "lang": "30 Minuten"}[umfang]
                parameter = {
                    "kategorien": kategorien, "schwierigkeit": schwierigkeit, "bearbeitungszeit": zeit,
                    "aufgaben_pro_kategorie": plan.aufgaben_je_bereich, "test_aufgaben": plan.test_aufgaben,
                    "foerderplan": plan.als_dict(), "foerderplan_text": blatt.foerderplan_block(plan),
                }
                try:
                    code, prompt = auftraege.prompt_bauen(
                        "uebungsblatt", parameter, reg.liste, sammlung=reg.sammlung,
                    )
                except KeyError as fehler_:
                    st.error(str(fehler_))
                    return
                db.auftrag_anlegen(con, schueler["id"], code, "uebungsblatt", parameter, prompt)
                st.session_state["blatt_auftrag"] = code
                for k in ("blatt_ergebnis", "blatt_aufgaben", "blatt_eingefuegt"):
                    st.session_state.pop(k, None)
                st.rerun()

    code = st.session_state.get("blatt_auftrag")
    if not code:
        return
    auftrag = db.auftrag_holen(con, code)
    if auftrag is None or auftrag["schueler_id"] != schueler["id"]:
        st.session_state.pop("blatt_auftrag", None)
        return
    plan = _plan_aus_state(con, schueler)

    st.divider()
    st.subheader("Förderplan (geht so in den Prompt)")
    if plan:
        _foerderplan_anzeigen(plan, reg)

    st.divider()
    st.subheader("Schritt 2 · Prompt in den Chat kopieren")
    g.prompt_anzeigen(auftrag["prompt_text"], code)

    st.divider()
    st.subheader("Schritt 3 · Ergebnis einfügen")
    eingefuegt = st.text_area(
        "Antwort aus dem Chat", height=220, key="blatt_eingefuegt",
        placeholder="Komplette Antwort hierher kopieren.",
    )
    if st.button("Ergebnis auswerten"):
        if not (eingefuegt or "").strip():
            st.warning(
                "Das Eingabefeld ist noch leer. Bitte die Antwort einfügen und "
                "einmal neben das Feld klicken."
            )
        else:
            ergebnis = auftraege.ergebnis_lesen(eingefuegt, erwarteter_code=code, erwarteter_typ="uebungsblatt")
            st.session_state["blatt_ergebnis"] = ergebnis
            st.session_state["blatt_aufgaben"] = ergebnis.aufgaben
            st.rerun()

    ergebnis = st.session_state.get("blatt_ergebnis")
    if ergebnis is not None:
        _vorschau_und_freigabe(con, schueler, auftrag, ergebnis, plan)


# ---------------------------------------------------------------------------
# Aufgabenvorschau mit Bearbeiten, Chips und Austausch
# ---------------------------------------------------------------------------

def _aufgabe_karte(a: dict, plan: blatt.Foerderplan, befunde: list[dict], anforderung: str) -> None:
    """Eine Aufgabe als Karte: Inhalt, darunter aufklappbar Bearbeiten, Chips
    und der Teilprompt zum Überarbeiten oder Austauschen."""
    schluessel = f"{a['teil']}_{a['nr']}"
    fmt = blatt.FORMATE.get(a["format"], {}).get("name", a["format"])
    with st.container(border=True):
        kopf, werkzeuge = st.columns([5, 2])
        kopf.markdown(f"**{a['nr']} · {a['bereich']} · {fmt}**"
                      + (f" — Strategie: *{a['strategie']}*" if a["strategie"] else "")
                      + (f" · {a['punkte']} P." if a["teil"] == "test" and a["punkte"] > 1 else ""))
        for b in befunde:
            (st.warning if b["stufe"] == "warnung" else st.info)(b["text"])
        if a["merksatz"] and a["teil"] == "uebung":
            st.markdown(f"> **Merke:** {a['merksatz']}")
        st.markdown(a["aufgabe"])
        if a["material"]:
            st.text(a["material"])
        k = werkzeuge.columns(3)
        if k[0].button("↑", key=f"auf_{schluessel}", help="nach oben"):
            st.session_state["blatt_aufgaben"] = blatt.aufgabe_verschieben(st.session_state["blatt_aufgaben"], a["teil"], a["nr"], -1)
            st.rerun()
        if k[1].button("↓", key=f"ab_{schluessel}", help="nach unten"):
            st.session_state["blatt_aufgaben"] = blatt.aufgabe_verschieben(st.session_state["blatt_aufgaben"], a["teil"], a["nr"], 1)
            st.rerun()
        if k[2].button("✕", key=f"weg_{schluessel}", help="Aufgabe entfernen"):
            st.session_state["blatt_aufgaben"] = blatt.aufgabe_entfernen(st.session_state["blatt_aufgaben"], a["teil"], a["nr"])
            st.rerun()

        with st.expander("Bearbeiten · Chips · Austauschen"):
            st.caption("Von Hand ändern:")
            aufgabe = st.text_input("Aufgabenstellung", value=a["aufgabe"], key=f"e_auf_{schluessel}")
            material = st.text_area("Material", value=a["material"], key=f"e_mat_{schluessel}", height=90)
            loesung = st.text_area("Lösung (nur auf dem Lösungsblatt)", value=a["loesung"], key=f"e_loe_{schluessel}", height=60)
            merksatz = st.text_input("Merksatz (nur Übungsteil)", value=a["merksatz"], key=f"e_mer_{schluessel}") if a["teil"] == "uebung" else a["merksatz"]
            if st.button("Änderung übernehmen", key=f"e_ok_{schluessel}"):
                neu = {**a, "aufgabe": aufgabe, "material": material, "loesung": loesung, "merksatz": merksatz}
                st.session_state["blatt_aufgaben"] = blatt.aufgabe_ersetzen(st.session_state["blatt_aufgaben"], a["teil"], a["nr"], neu)
                st.rerun()

            st.caption("Vom Sprachmodell überarbeiten lassen – einen Chip wählen (oder keinen) und einen Wunsch eintragen:")
            chip_spalten = st.columns(len(blatt.CHIPS))
            gewaehlt = st.session_state.get(f"chip_{schluessel}")
            for i, (cid, c) in enumerate(blatt.CHIPS.items()):
                if chip_spalten[i].button(("✓ " if gewaehlt == cid else "") + c["name"], key=f"chip_{schluessel}_{cid}"):
                    st.session_state[f"chip_{schluessel}"] = None if gewaehlt == cid else cid
                    st.rerun()
            wunsch = st.text_input("Wunsch (frei)", key=f"wunsch_{schluessel}", placeholder="z. B. mit Wörtern aus dem Thema Wald")
            p1, p2 = st.columns(2)
            if p1.button("Prompt: Überarbeiten", key=f"tp_ue_{schluessel}"):
                st.session_state[f"tp_{schluessel}"] = blatt.teilprompt_bauen(a, plan, "ueberarbeiten", gewaehlt, wunsch, anforderung)
            if p2.button("Prompt: Austauschen", key=f"tp_at_{schluessel}"):
                st.session_state[f"tp_{schluessel}"] = blatt.teilprompt_bauen(a, plan, "austauschen", gewaehlt, wunsch, anforderung)
            tp = st.session_state.get(f"tp_{schluessel}")
            if tp:
                tcode, ttext = tp
                st.code(ttext, language="markdown")
                antwort = st.text_area("Antwort des Chats hier einfügen", key=f"tpa_{schluessel}", height=120)
                if st.button("Aufgabe ersetzen", key=f"tpr_{schluessel}", type="primary"):
                    neu, hinweise = blatt.aufgabe_lesen(antwort)
                    if neu is None:
                        st.error(" ".join(hinweise))
                    else:
                        st.session_state["blatt_aufgaben"] = blatt.aufgabe_ersetzen(st.session_state["blatt_aufgaben"], a["teil"], a["nr"], neu)
                        st.session_state.pop(f"tp_{schluessel}", None)
                        st.rerun()


def _vorschau_und_freigabe(con, schueler, auftrag, ergebnis, plan) -> None:
    reg = g.register()
    parameter = json.loads(auftrag["parameter"] or "{}")
    kategorien = [str(k) for k in parameter.get("kategorien", [])]
    anforderung = auftraege._anforderung("uebungsblatt", parameter.get("schwierigkeit", "mittel"))

    st.divider()
    st.subheader("Schritt 4 · Blatt ansehen, prüfen, anpassen")
    st.info("**Noch nichts gespeichert.** Erst die Freigabe unten speichert das Blatt.")
    for hinweis in ergebnis.hinweise:
        st.warning(hinweis)

    aufgaben = st.session_state.get("blatt_aufgaben") or []
    if aufgaben and plan:
        befunde = blatt.aufgaben_pruefen(aufgaben, plan)
        allgemein = [b for b in befunde if b["nr"] == 0]
        for b in allgemein:
            (st.warning if b["stufe"] == "warnung" else st.info)(b["text"])
        tab_u, tab_t, tab_l = st.tabs(["Vorderseite · Übungsteil", "Rückseite · Mini-Test", "Lösungsblatt"])
        with tab_u:
            for a in [x for x in aufgaben if x["teil"] == "uebung"]:
                _aufgabe_karte(a, plan, [b for b in befunde if b["teil"] == "uebung" and b["nr"] == a["nr"]], anforderung)
        with tab_t:
            for a in [x for x in aufgaben if x["teil"] == "test"]:
                _aufgabe_karte(a, plan, [b for b in befunde if b["teil"] == "test" and b["nr"] == a["nr"]], anforderung)
        uebung, test, loesungen = blatt.aufgaben_zu_text(aufgaben)
        with tab_l:
            st.text(loesungen)
        with st.expander("Drucktext (so kommt es aufs Blatt)"):
            st.text(uebung)
            st.text(test)
    else:
        uebung = st.text_area("Übungsteil (Vorderseite)", value=ergebnis.uebungsteil, height=240, key="blatt_uebung")
        test = st.text_area("Mini-Test (Rückseite)", value=ergebnis.testteil, height=200, key="blatt_test")
        loesungen = st.text_area("Lösungen (separates Blatt)", value=ergebnis.loesungen, height=140, key="blatt_loesungen")

    titel = st.text_input("Titel des Blattes", value=ergebnis.titel or "Übungsblatt")
    st.markdown("**Automatische Plausibilitätsprüfung**")
    g.befunde_anzeigen(validation.blatt_pruefen(uebung, test, loesungen, kategorien, reg))

    st.divider()
    st.markdown("### Freigabe")
    st.markdown(
        "Bitte beide Rückfragen bewusst beantworten – die App kann das nicht "
        "für Sie beurteilen."
    )
    pruef_loesungen = st.checkbox(
        "**Keine Lösungen auf den Aufgabenseiten** – ich habe Vorder- und "
        "Rückseite durchgesehen; es sind keine Lösungen sichtbar.",
        key="blatt_pruef_loesungen",
    )
    pruef_niveau = st.checkbox(
        "**Schwierigkeitsgrad passt zur Altersstufe** – ich habe die Aufgaben "
        "gelesen und halte sie für angemessen.",
        key="blatt_pruef_niveau",
    )
    freigabe = st.checkbox(
        "**Geprüft und freigegeben** – das Blatt kann so in den Unterricht.",
        key="blatt_freigabe",
    )
    datum = st.date_input("Datum", value=date.today(), key="blatt_datum")

    alles_bestaetigt = pruef_loesungen and pruef_niveau and freigabe
    if not alles_bestaetigt:
        st.caption("Zum Speichern müssen alle drei Häkchen gesetzt sein.")

    if st.button("Blatt speichern", type="primary", disabled=not alles_bestaetigt):
        blatt_id = db.blatt_anlegen(
            con, schueler["id"], titel, kategorien, uebung, test, loesungen,
            datum=datum.isoformat(), aufgaben=aufgaben or None,
        )
        db.blatt_freigeben(con, blatt_id, pruef_loesungen, pruef_niveau)
        db.auftrag_status_setzen(con, auftrag["code"], auftraege.STATUS_FREIGEGEBEN,
                                 ergebnis_roh=uebung)
        for schluessel in list(st.session_state):
            if schluessel.startswith(("blatt_", "tp_", "tpa_", "chip_", "wunsch_", "e_")):
                st.session_state.pop(schluessel, None)
        g.merken(f"Blatt «{titel}» gespeichert (Nr. {blatt_id}).")
        st.rerun()

    if st.button("Verwerfen", key="blatt_verwerfen"):
        db.auftrag_status_setzen(con, auftrag["code"], auftraege.STATUS_VERWORFEN)
        for schluessel in ("blatt_auftrag", "blatt_ergebnis", "blatt_eingefuegt", "blatt_aufgaben", "blatt_plan"):
            st.session_state.pop(schluessel, None)
        st.rerun()


# ---------------------------------------------------------------------------
# Archiv + Docx
# ---------------------------------------------------------------------------

def _archiv(con, schueler) -> None:
    reg = g.register()
    blaetter = db.blatt_liste(con, schueler["id"])
    if not blaetter:
        st.info("Noch keine Übungsblätter gespeichert.")
        return

    for blatt in blaetter:
        kategorien = g.json_liste(blatt["kategorien"])
        with st.expander(f"{blatt['datum']} · {blatt['titel']}"):
            st.caption("Förderschwerpunkte: "
                       + ", ".join(reg.label(nr) for nr in kategorien))
            st.caption(
                f"Freigegeben am {blatt['freigegeben_am'] or '–'} · "
                f"Lösungen geprüft: {'ja' if blatt['pruef_loesungen'] else 'nein'} · "
                f"Niveau geprüft: {'ja' if blatt['pruef_niveau'] else 'nein'}"
            )
            st.text_area("Übungsteil", value=blatt["inhalt_uebung"], height=140,
                         key=f"arch_ueb_{blatt['id']}", disabled=True)
            st.text_area("Mini-Test", value=blatt["inhalt_test"], height=120,
                         key=f"arch_test_{blatt['id']}", disabled=True)

            mit_loesungen = st.checkbox(
                "Lösungsblatt anhängen (Seite 3, deutlich als «nicht austeilen» markiert)",
                key=f"arch_loes_{blatt['id']}",
            )
            format_ = g.formatwahl(f"arch_format_{blatt['id']}")
            if st.button("Datei erzeugen", type="primary",
                         key=f"arch_datei_{blatt['id']}"):
                endung = g.FORMATE[format_]["endung"]
                pfad = config.EXPORT_DIR / (
                    f"Uebungsblatt_{schueler['id']}_{blatt['datum']}_"
                    f"{blatt['id']}.{endung}"
                )
                g.export_modul(format_).uebungsblatt_schreiben(
                    pfad, g.anzeigename(con, schueler), blatt["titel"], kategorien,
                    reg, blatt["inhalt_uebung"], blatt["inhalt_test"],
                    blatt["loesungen"], datum=_datum_deutsch(blatt["datum"]),
                    loesungen_anhaengen=mit_loesungen,
                )
                with open(pfad, "rb") as datei:
                    st.download_button(
                        f"{endung.upper()} herunterladen", datei.read(),
                        file_name=pfad.name, mime=g.FORMATE[format_]["mime"],
                        key=f"arch_dl_{blatt['id']}",
                    )
                g.merken(f"Erzeugt: `{pfad}`")

            if st.button("Blatt löschen", key=f"arch_del_{blatt['id']}"):
                db.blatt_loeschen(con, blatt["id"])
                st.rerun()


def _datum_deutsch(iso: str) -> str:
    try:
        return date.fromisoformat(iso).strftime("%d.%m.%Y")
    except (TypeError, ValueError):
        return iso
