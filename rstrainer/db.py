"""SQLite-Datenhaltung.

Alle Inhalte hängen an einer ``schueler_id``; jede Abfrage filtert danach.
Dadurch sind die Datenbestände der einzelnen Profile strikt voneinander
getrennt, obwohl sie in gemeinsamen Tabellen liegen (ein Schema pro Profil
wäre gleichwertig, aber deutlich umständlicher bei Auswertungen).

Freigaben: Generierte Inhalte werden IMMER mit ``freigegeben = 0`` angelegt.
Erst ``diktat_freigeben`` bzw. ``blatt_freigeben`` setzt das Häkchen samt
Zeitstempel. Nichts gelangt ungeprüft in den Verlauf.

Ein Profil trägt nur Anzeigename und Notiz. Kürzel und Klasse hat die
Lehrperson bewusst nicht gewollt: Sie kennt die wenigen Kinder, die sie
einzeln fördert, und jedes zusätzliche Feld wäre ein weiteres
personenbezogenes Datum ohne Nutzen.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator

from . import config

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schueler (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    anzeigename   TEXT    NOT NULL,
    notiz         TEXT    DEFAULT '',
    angelegt_am   TEXT    NOT NULL,
    aktiv         INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS diktate (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    schueler_id          INTEGER NOT NULL REFERENCES schueler(id) ON DELETE CASCADE,
    titel                TEXT    NOT NULL,
    text_original        TEXT    NOT NULL,
    wortzahl             INTEGER NOT NULL DEFAULT 0,
    datum                TEXT    NOT NULL,
    ziel_kategorien      TEXT    NOT NULL DEFAULT '[]',
    notiz                TEXT    DEFAULT '',
    quelle               TEXT    DEFAULT 'manuell',
    art                  TEXT    NOT NULL DEFAULT 'diktat',
    erstellt_am          TEXT    NOT NULL,
    freigegeben          INTEGER NOT NULL DEFAULT 0,
    freigegeben_am       TEXT,
    schuelertext         TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS fehler (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    schueler_id    INTEGER NOT NULL REFERENCES schueler(id) ON DELETE CASCADE,
    diktat_id      INTEGER REFERENCES diktate(id) ON DELETE CASCADE,
    kategorie_nr   TEXT    NOT NULL,
    wort_original  TEXT    NOT NULL DEFAULT '',
    wort_schueler  TEXT    NOT NULL DEFAULT '',
    kontext        TEXT    DEFAULT '',
    datum          TEXT    NOT NULL,
    notiz          TEXT    DEFAULT '',
    erstellt_am    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS blaetter (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    schueler_id       INTEGER NOT NULL REFERENCES schueler(id) ON DELETE CASCADE,
    titel             TEXT    NOT NULL,
    kategorien        TEXT    NOT NULL DEFAULT '[]',
    inhalt_uebung     TEXT    NOT NULL DEFAULT '',
    inhalt_test       TEXT    NOT NULL DEFAULT '',
    loesungen         TEXT    NOT NULL DEFAULT '',
    datum             TEXT    NOT NULL,
    erstellt_am       TEXT    NOT NULL,
    freigegeben       INTEGER NOT NULL DEFAULT 0,
    freigegeben_am    TEXT,
    pruef_loesungen   INTEGER NOT NULL DEFAULT 0,
    pruef_niveau      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS auftraege (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    schueler_id   INTEGER NOT NULL REFERENCES schueler(id) ON DELETE CASCADE,
    code          TEXT    NOT NULL UNIQUE,
    typ           TEXT    NOT NULL,
    parameter     TEXT    NOT NULL DEFAULT '{}',
    prompt_text   TEXT    NOT NULL DEFAULT '',
    ergebnis_roh  TEXT    DEFAULT '',
    status        TEXT    NOT NULL DEFAULT 'offen',
    erstellt_am   TEXT    NOT NULL,
    eingefuegt_am TEXT
);

CREATE TABLE IF NOT EXISTS einstellungen (
    schluessel TEXT PRIMARY KEY,
    wert       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_diktate_schueler ON diktate(schueler_id, datum);
CREATE INDEX IF NOT EXISTS idx_diktate_art      ON diktate(schueler_id, art);
CREATE INDEX IF NOT EXISTS idx_fehler_schueler  ON fehler(schueler_id, datum);
CREATE INDEX IF NOT EXISTS idx_fehler_diktat    ON fehler(diktat_id);
CREATE INDEX IF NOT EXISTS idx_blaetter_schueler ON blaetter(schueler_id, datum);
"""


def _jetzt() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _heute() -> str:
    return date.today().isoformat()


def verbinden(pfad: Path | str | None = None) -> sqlite3.Connection:
    """Öffnet eine Verbindung und stellt sicher, dass das Schema existiert."""
    pfad = Path(pfad) if pfad is not None else config.DB_PFAD
    if str(pfad) != ":memory:":
        pfad.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(pfad, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    con.commit()
    return con


@contextmanager
def transaktion(con: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise


# --------------------------------------------------------------------------
# Schülerprofile
# --------------------------------------------------------------------------

def schueler_anlegen(con, anzeigename: str, notiz: str = "") -> int:
    anzeigename = anzeigename.strip()
    if not anzeigename:
        raise ValueError("Der Anzeigename darf nicht leer sein.")
    with transaktion(con):
        cur = con.execute(
            "INSERT INTO schueler (anzeigename, notiz, angelegt_am) VALUES (?,?,?)",
            (anzeigename, notiz, _jetzt()),
        )
    return int(cur.lastrowid)


def schueler_liste(con, nur_aktive: bool = True) -> list[sqlite3.Row]:
    sql = "SELECT * FROM schueler"
    if nur_aktive:
        sql += " WHERE aktiv = 1"
    sql += " ORDER BY anzeigename COLLATE NOCASE"
    return con.execute(sql).fetchall()


def schueler_holen(con, schueler_id: int) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM schueler WHERE id = ?", (schueler_id,)).fetchone()


def schueler_aktualisieren(con, schueler_id: int, **felder) -> None:
    erlaubt = {"anzeigename", "notiz", "aktiv"}
    felder = {k: v for k, v in felder.items() if k in erlaubt}
    if not felder:
        return
    setzen = ", ".join(f"{k} = ?" for k in felder)
    with transaktion(con):
        con.execute(f"UPDATE schueler SET {setzen} WHERE id = ?",
                    (*felder.values(), schueler_id))


def schueler_loeschen(con, schueler_id: int) -> None:
    """Löscht das Profil samt aller Diktate, Fehler und Blätter."""
    with transaktion(con):
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("DELETE FROM fehler    WHERE schueler_id = ?", (schueler_id,))
        con.execute("DELETE FROM diktate   WHERE schueler_id = ?", (schueler_id,))
        con.execute("DELETE FROM blaetter  WHERE schueler_id = ?", (schueler_id,))
        con.execute("DELETE FROM auftraege WHERE schueler_id = ?", (schueler_id,))
        con.execute("DELETE FROM schueler  WHERE id = ?", (schueler_id,))


def schueler_uebersicht(con, schueler_id: int) -> dict[str, Any]:
    """Kennzahlen für die Profilübersicht."""
    anzahl = con.execute(
        "SELECT COUNT(*) FROM diktate WHERE schueler_id = ?", (schueler_id,)
    ).fetchone()[0]
    letztes = con.execute(
        "SELECT datum, titel FROM diktate WHERE schueler_id = ?"
        " ORDER BY date(datum) DESC, id DESC LIMIT 1",
        (schueler_id,),
    ).fetchone()
    fehler = con.execute(
        "SELECT COUNT(*) FROM fehler WHERE schueler_id = ?", (schueler_id,)
    ).fetchone()[0]
    offen = con.execute(
        "SELECT COUNT(*) FROM diktate WHERE schueler_id = ? AND freigegeben = 0",
        (schueler_id,),
    ).fetchone()[0]
    return {
        "anzahl_diktate": anzahl,
        "anzahl_fehler": fehler,
        "letztes_diktat_datum": letztes["datum"] if letztes else None,
        "letztes_diktat_titel": letztes["titel"] if letztes else None,
        "diktate_ohne_freigabe": offen,
    }


# --------------------------------------------------------------------------
# Diktate
# --------------------------------------------------------------------------

def diktat_anlegen(con, schueler_id: int, titel: str, text_original: str,
                   datum: str | None = None, ziel_kategorien: list[str] | None = None,
                   notiz: str = "", quelle: str = "manuell",
                   freigegeben: bool = False, art: str = "diktat",
                   schuelertext: str = "") -> int:
    """Legt einen Text an – standardmäßig OHNE Freigabe.

    ``art='diktat'``: ``text_original`` ist die fehlerfreie Vorlage, die
    Wortzahl richtet sich nach ihr.
    ``art='freitext'``: es gibt keine Vorlage; der Text des Kindes steht in
    ``schuelertext`` und bestimmt die Wortzahl.
    """
    from .textwerkzeuge import woerter_zaehlen

    bezug = schuelertext if art == "freitext" else text_original
    with transaktion(con):
        cur = con.execute(
            "INSERT INTO diktate (schueler_id, titel, text_original, wortzahl, datum,"
            " ziel_kategorien, notiz, quelle, art, schuelertext, erstellt_am,"
            " freigegeben, freigegeben_am)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                schueler_id, titel.strip(), text_original,
                woerter_zaehlen(bezug), datum or _heute(),
                json.dumps(ziel_kategorien or [], ensure_ascii=False),
                notiz, quelle, art, schuelertext, _jetzt(),
                int(freigegeben), _jetzt() if freigegeben else None,
            ),
        )
    return int(cur.lastrowid)


def diktat_liste(con, schueler_id: int, nur_freigegebene: bool = False) -> list[sqlite3.Row]:
    sql = "SELECT * FROM diktate WHERE schueler_id = ?"
    if nur_freigegebene:
        sql += " AND freigegeben = 1"
    sql += " ORDER BY date(datum) ASC, id ASC"
    return con.execute(sql, (schueler_id,)).fetchall()


def diktat_holen(con, diktat_id: int) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM diktate WHERE id = ?", (diktat_id,)).fetchone()


def diktat_aktualisieren(con, diktat_id: int, **felder) -> None:
    from .textwerkzeuge import woerter_zaehlen

    erlaubt = {"titel", "text_original", "datum", "notiz", "schuelertext",
               "ziel_kategorien", "wortzahl"}
    felder = {k: v for k, v in felder.items() if k in erlaubt}
    if "ziel_kategorien" in felder and not isinstance(felder["ziel_kategorien"], str):
        felder["ziel_kategorien"] = json.dumps(felder["ziel_kategorien"], ensure_ascii=False)
    if "text_original" in felder:
        felder.setdefault("wortzahl", woerter_zaehlen(felder["text_original"]))
    if "schuelertext" in felder and diktat_holen(con, diktat_id) is not None \
            and diktat_holen(con, diktat_id)["art"] == "freitext":
        felder["wortzahl"] = woerter_zaehlen(felder["schuelertext"])
    if not felder:
        return
    setzen = ", ".join(f"{k} = ?" for k in felder)
    with transaktion(con):
        con.execute(f"UPDATE diktate SET {setzen} WHERE id = ?",
                    (*felder.values(), diktat_id))


def diktat_freigeben(con, diktat_id: int, freigegeben: bool = True) -> None:
    """Setzt das allgemeine Freigabe-Häkchen samt Zeitstempel."""
    with transaktion(con):
        con.execute(
            "UPDATE diktate SET freigegeben = ?, freigegeben_am = ? WHERE id = ?",
            (int(freigegeben), _jetzt() if freigegeben else None, diktat_id),
        )


def diktat_loeschen(con, diktat_id: int) -> None:
    with transaktion(con):
        con.execute("DELETE FROM fehler WHERE diktat_id = ?", (diktat_id,))
        con.execute("DELETE FROM diktate WHERE id = ?", (diktat_id,))


# --------------------------------------------------------------------------
# Fehler
# --------------------------------------------------------------------------

def fehler_anlegen(con, schueler_id: int, kategorie_nr: str, diktat_id: int | None = None,
                   wort_original: str = "", wort_schueler: str = "", kontext: str = "",
                   datum: str | None = None, notiz: str = "") -> int:
    with transaktion(con):
        cur = con.execute(
            "INSERT INTO fehler (schueler_id, diktat_id, kategorie_nr, wort_original,"
            " wort_schueler, kontext, datum, notiz, erstellt_am)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (schueler_id, diktat_id, kategorie_nr, wort_original, wort_schueler,
             kontext, datum or _heute(), notiz, _jetzt()),
        )
    return int(cur.lastrowid)


def fehler_mehrere_anlegen(con, schueler_id: int, eintraege: list[dict]) -> int:
    """Legt mehrere Fehler in einer Transaktion an (Rückgabe: Anzahl)."""
    jetzt = _jetzt()
    zeilen = [
        (schueler_id, e.get("diktat_id"), e["kategorie_nr"], e.get("wort_original", ""),
         e.get("wort_schueler", ""), e.get("kontext", ""), e.get("datum") or _heute(),
         e.get("notiz", ""), jetzt)
        for e in eintraege
    ]
    if not zeilen:
        return 0
    with transaktion(con):
        con.executemany(
            "INSERT INTO fehler (schueler_id, diktat_id, kategorie_nr, wort_original,"
            " wort_schueler, kontext, datum, notiz, erstellt_am)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            zeilen,
        )
    return len(zeilen)


def fehler_liste(con, schueler_id: int, diktat_id: int | None = None) -> list[sqlite3.Row]:
    sql = "SELECT * FROM fehler WHERE schueler_id = ?"
    params: list[Any] = [schueler_id]
    if diktat_id is not None:
        sql += " AND diktat_id = ?"
        params.append(diktat_id)
    sql += " ORDER BY date(datum) ASC, id ASC"
    return con.execute(sql, params).fetchall()


def fehler_loeschen(con, fehler_id: int) -> None:
    with transaktion(con):
        con.execute("DELETE FROM fehler WHERE id = ?", (fehler_id,))


def fehler_umhaengen(con, von_nr: str, nach_nr: str) -> int:
    """Hängt alle Fehler einer Kategorie auf eine andere um – über ALLE Profile.

    Beim Zusammenlegen zweier gelernter Fehlerarten würden sonst die Einträge
    fremder Profile ins Leere zeigen.
    """
    with transaktion(con):
        cur = con.execute(
            "UPDATE fehler SET kategorie_nr = ? WHERE kategorie_nr = ?",
            (nach_nr, von_nr),
        )
    return cur.rowcount


def fehler_haeufigkeit(con, schueler_id: int) -> list[sqlite3.Row]:
    return con.execute(
        "SELECT kategorie_nr, COUNT(*) AS anzahl FROM fehler WHERE schueler_id = ?"
        " GROUP BY kategorie_nr ORDER BY anzahl DESC",
        (schueler_id,),
    ).fetchall()


# --------------------------------------------------------------------------
# Übungsblätter / Mini-Tests
# --------------------------------------------------------------------------

def blatt_anlegen(con, schueler_id: int, titel: str, kategorien: list[str],
                  inhalt_uebung: str, inhalt_test: str, loesungen: str = "",
                  datum: str | None = None) -> int:
    with transaktion(con):
        cur = con.execute(
            "INSERT INTO blaetter (schueler_id, titel, kategorien, inhalt_uebung,"
            " inhalt_test, loesungen, datum, erstellt_am)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (schueler_id, titel.strip(), json.dumps(kategorien, ensure_ascii=False),
             inhalt_uebung, inhalt_test, loesungen, datum or _heute(), _jetzt()),
        )
    return int(cur.lastrowid)


def blatt_liste(con, schueler_id: int) -> list[sqlite3.Row]:
    return con.execute(
        "SELECT * FROM blaetter WHERE schueler_id = ?"
        " ORDER BY date(datum) DESC, id DESC",
        (schueler_id,),
    ).fetchall()


def blatt_holen(con, blatt_id: int) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM blaetter WHERE id = ?", (blatt_id,)).fetchone()


def blatt_freigeben(con, blatt_id: int, pruef_loesungen: bool, pruef_niveau: bool) -> None:
    """Freigabe eines Blattes.

    ``pruef_loesungen`` und ``pruef_niveau`` sind die beiden bestätigten
    Prüffragen (keine Lösungen auf der Aufgabenseite / Niveau passt zur
    Altersstufe) und werden mit abgelegt.
    """
    with transaktion(con):
        con.execute(
            "UPDATE blaetter SET freigegeben = 1, freigegeben_am = ?,"
            " pruef_loesungen = ?, pruef_niveau = ? WHERE id = ?",
            (_jetzt(), int(pruef_loesungen), int(pruef_niveau), blatt_id),
        )


def blatt_loeschen(con, blatt_id: int) -> None:
    with transaktion(con):
        con.execute("DELETE FROM blaetter WHERE id = ?", (blatt_id,))


# --------------------------------------------------------------------------
# Aufträge (Prompt → Chat → Ergebnis)
# --------------------------------------------------------------------------

def auftrag_anlegen(con, schueler_id: int, code: str, typ: str,
                    parameter: dict, prompt_text: str) -> int:
    with transaktion(con):
        cur = con.execute(
            "INSERT INTO auftraege (schueler_id, code, typ, parameter, prompt_text,"
            " status, erstellt_am) VALUES (?,?,?,?,?,'offen',?)",
            (schueler_id, code, typ, json.dumps(parameter, ensure_ascii=False),
             prompt_text, _jetzt()),
        )
    return int(cur.lastrowid)


def auftrag_holen(con, code: str) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM auftraege WHERE code = ?", (code,)).fetchone()


def auftrag_liste(con, schueler_id: int, typ: str | None = None,
                  status: str | None = None) -> list[sqlite3.Row]:
    sql = "SELECT * FROM auftraege WHERE schueler_id = ?"
    params: list[Any] = [schueler_id]
    if typ:
        sql += " AND typ = ?"
        params.append(typ)
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY id DESC"
    return con.execute(sql, params).fetchall()


def auftrag_status_setzen(con, code: str, status: str, ergebnis_roh: str | None = None) -> None:
    with transaktion(con):
        if ergebnis_roh is None:
            con.execute("UPDATE auftraege SET status = ? WHERE code = ?", (status, code))
        else:
            con.execute(
                "UPDATE auftraege SET status = ?, ergebnis_roh = ?, eingefuegt_am = ?"
                " WHERE code = ?",
                (status, ergebnis_roh, _jetzt(), code),
            )


# --------------------------------------------------------------------------
# Einstellungen
# --------------------------------------------------------------------------

def einstellung_setzen(con, schluessel: str, wert: Any) -> None:
    with transaktion(con):
        con.execute(
            "INSERT INTO einstellungen (schluessel, wert) VALUES (?,?)"
            " ON CONFLICT(schluessel) DO UPDATE SET wert = excluded.wert",
            (schluessel, json.dumps(wert, ensure_ascii=False)),
        )


def einstellung_holen(con, schluessel: str, standard: Any = None) -> Any:
    zeile = con.execute(
        "SELECT wert FROM einstellungen WHERE schluessel = ?", (schluessel,)
    ).fetchone()
    if zeile is None:
        return standard
    try:
        return json.loads(zeile["wert"])
    except json.JSONDecodeError:
        return standard
