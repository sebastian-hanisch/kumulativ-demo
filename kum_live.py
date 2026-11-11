"""Live-Knöpfe: Zwischenspeicher und Fortschrittsanzeige.

Jede lange Aktion (Messreihe, Einzelinstanz mit drei Stufen) besteht aus Einheiten (eine Stufe auf einer Instanz). Jede Einheit ist eine reine Funktion ihrer Parameter
und liegt einzeln im Zwischenspeicher (`st.cache_data`, kleine `max_entries`); die Anzeige zählt die fertigen Einheiten (`mit_fortschritt`). Ein zweiter Klick mit denselben
Einstellungen und auch eine Reihe, die Einheiten mit einer früheren teilt, antworten aus dem Speicher. Die Ergebnisse sind bitgleich zu den ungespeicherten Funktionen
(`tests/test_live.py`). Rechnung, Zahlen und Aussagen ändern sich nicht."""

import streamlit as st

import kum_algorithm as A
import kum_constants as C
import kum_evaluation as ev
from kum_scenario import make_instanz


def stufe_lauf_ungespeichert(seed: int, n: int, res: int, cap: int, budget: int, stufe: int):
    """Eine Stufe auf der Einzelinstanz (dieselbe Rechnung wie `ev.live_vergleich`, je Stufe)."""
    return A.loese(make_instanz(n, res, cap, seed), stufe, budget=budget)


@st.cache_data(show_spinner=False, max_entries=24)
def stufe_lauf(seed, n, res, cap, budget, stufe):
    return stufe_lauf_ungespeichert(seed, n, res, cap, budget, stufe)


@st.cache_data(show_spinner=False, max_entries=120)
def reihe_einheit(zelle, seed, stufe, budget):
    return ev.live_reihe_einheit(zelle, seed, stufe, budget)


def mit_fortschritt(titel: str, schritte: list, rechne) -> list:
    """Führt die Schritte nacheinander aus und zeigt, wie viele fertig sind. `schritte`: Liste aus (Beschriftung, Argumente); `rechne(*Argumente)` liefert das Ergebnis
    (aus dem Zwischenspeicher oder frisch gerechnet). Rückgabe: die Ergebnisse in der Reihenfolge der Schritte."""
    n = len(schritte)
    ergebnisse = []
    with st.status(titel, expanded=True) as status:
        balken = st.progress(0.0, text=f"0 von {n} fertig")
        for i, (beschriftung, args) in enumerate(schritte):
            balken.progress(i / n, text=f"{beschriftung} (Schritt {i + 1} von {n})")
            ergebnisse.append(rechne(*args))
        balken.progress(1.0, text=f"{n} von {n} fertig")
        status.update(label=f"{titel}: fertig", state="complete", expanded=False)
    return ergebnisse


def stufen_einzel(live_key: tuple) -> dict:
    """Die Einzelinstanz mit allen Stufen, mit Fortschrittsanzeige (je Stufe ein Schritt). `live_key` = (seed, n, res, cap, budget)."""
    seed, n, res, cap, budget = live_key
    schritte = [(C.STAGE_NAMES[s], (seed, n, res, cap, budget, s)) for s in C.STAGES]
    laeufe = mit_fortschritt("Rechnet die Stufen bis zum Beweis des Optimums oder bis zum Knotenbudget", schritte, stufe_lauf)
    return dict(zip(C.STAGES, laeufe))


def reihe(zelle: str, budget: int) -> dict:
    """Die Messreihe der Zelle mit Fortschrittsanzeige (je Instanz und Stufe ein Schritt)."""
    schritte = [(f"Instanz {i + 1} von {len(C.SWEEP_SEEDS)}, Stufe {s}", (zelle, seed, s, budget)) for i, seed in enumerate(C.SWEEP_SEEDS) for s in C.STAGES]
    ergebnisse = mit_fortschritt(f"Rechnet Zelle {zelle}: 3 Stufen auf {len(C.SWEEP_SEEDS)} Instanzen (Budget {budget} Knoten)", schritte, reihe_einheit)
    je_schritt = {(seed, s): e for (seed, s), e in zip(((seed, s) for seed in C.SWEEP_SEEDS for s in C.STAGES), ergebnisse)}
    return ev.live_reihe_aufbauen(zelle, budget, lambda z, seed, s, b: je_schritt[(seed, s)])


def einzel_aus_speicher(live_key: tuple) -> dict:
    """Die Einzelinstanz aus dem Zwischenspeicher (ohne Anzeige); rechnet nur, was dort fehlt."""
    seed, n, res, cap, budget = live_key
    return {s: stufe_lauf(seed, n, res, cap, budget, s) for s in C.STAGES}


def reihe_aus_speicher(zelle: str, budget: int) -> dict:
    """Die Messreihe aus dem Zwischenspeicher (ohne Anzeige); rechnet nur, was dort fehlt."""
    return ev.live_reihe_aufbauen(zelle, budget, reihe_einheit)
