"""Kennzahlen, Verdikt-Logik und Auswertung der vorgerechneten Messreihen (`kum_sweeps.json`, Messskript tools/messung_sweeps.py).

Alle Verdikte sind reine Funktionen `verdict_*(...) -> (Art, Text)`: die App ruft `getattr(st, Art)(Text)`, `tests/test_verdicts.py` prüft jede Zahl im Text an handgesetzten Werten.
Gezählt wird in Suchknoten und Konflikten, nie in Sekunden."""

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from statistics import median

import kum_algorithm as A
import kum_constants as C
from kum_scenario import Instanz, make_instanz

SWEEPS_PATH = Path(__file__).resolve().parent / C.SWEEPS_FILE


@dataclass(frozen=True)
class Settings:
    seed: int = C.DEFAULT_SEED
    n: int = C.DEFAULT_N
    res: int = C.DEFAULT_RES
    cap: int = C.DEFAULT_CAP
    budget: int = C.DEFAULT_BUDGET
    bsp: int = C.DEFAULT_HB_BSP
    h: int = C.DEFAULT_HB_H
    stufe: int = C.DEFAULT_HB_STAGE
    zelle: int = 0
    sat_h: int = 0
    sat_budget: int = C.DEFAULT_SAT_BUDGET


def instanz(s: Settings) -> Instanz:
    return make_instanz(s.n, s.res, s.cap, s.seed)


# ------------------------------------------------------------------------------------------------------------------------- Messreihen (JSON)
@lru_cache(maxsize=1)
def lade_sweeps() -> dict:
    return json.loads(SWEEPS_PATH.read_text(encoding="utf-8"))


def p90(werte) -> int:
    """90-%-Wert nach dem Nächste-Rang-Verfahren: der Wert an Stelle ceil(0,9 n) der aufsteigend sortierten Liste."""
    w = sorted(werte)
    return w[math.ceil(0.9 * len(w)) - 1]


def knoten(reihe: dict, stufe: int) -> list:
    return [z["stufen"][str(stufe)]["knoten"] for z in reihe["instanzen"]]


def bewiesen(reihe: dict, stufe: int) -> int:
    """Zahl der Instanzen, deren Optimum die Stufe im Knotenbudget bewiesen hat."""
    return sum(1 for z in reihe["instanzen"] if z["stufen"][str(stufe)]["bewiesen"])


def luecken(reihe: dict, stufe: int) -> list:
    """Bester Wert der Stufe minus Optimum, für die Instanzen mit von CP-SAT bewiesenem Optimum (0 = Optimum gefunden)."""
    return [z["stufen"][str(stufe)]["optimum"] - z["cpsat"]["optimum"] for z in reihe["instanzen"] if z.get("cpsat", {}).get("bewiesen")]


def statistik(reihe: dict, stufen=None) -> list:
    """Je Stufe Median, 90-%-Wert, Maximum, bewiesene Instanzen, Abbrüche am Budget (bei Abbruch ist der Wert das Budget plus 1, also eine untere Schranke), Summe, Lücke zum Optimum."""
    stufen = reihe["stufen"] if stufen is None else stufen
    rows = []
    for s in stufen:
        w = knoten(reihe, s)
        n = len(w)
        lk = luecken(reihe, s)
        rows.append({"stufe": s, "n": n, "median": median(w), "p90": p90(w), "max": max(w), "bewiesen": bewiesen(reihe, s), "abbrueche": n - bewiesen(reihe, s), "summe": sum(w),
                     "luecke_median": median(lk) if lk else None, "luecke_max": max(lk) if lk else None})
    return rows


def paar_ersparnis(reihe: dict, a: int = 1, b: int = 2) -> dict:
    """Stufe b gegen Stufe a an den Instanzen, die **beide** beweisen: Ersparnis je Instanz = (Knoten a − Knoten b) / Knoten a (bei Knoten a = 0: 0).
    Dazu die Zahl der zusätzlich von b bewiesenen Instanzen (b beweist, a nicht)."""
    ersparnisse, mehr, weniger = [], 0, 0
    for z in reihe["instanzen"]:
        sa, sb = z["stufen"][str(a)], z["stufen"][str(b)]
        if sa["bewiesen"] and sb["bewiesen"]:
            ersparnisse.append((sa["knoten"] - sb["knoten"]) / sa["knoten"] if sa["knoten"] else 0.0)
        elif sb["bewiesen"] and not sa["bewiesen"]:
            mehr += 1
        elif sa["bewiesen"] and not sb["bewiesen"]:
            weniger += 1
    return {"n": len(reihe["instanzen"]), "beide": len(ersparnisse), "median": median(ersparnisse) if ersparnisse else None, "max": max(ersparnisse) if ersparnisse else None,
            "mit_ersparnis": sum(1 for e in ersparnisse if e > 0), "gleich": sum(1 for e in ersparnisse if e == 0), "mehr_bewiesen": mehr, "weniger_bewiesen": weniger}


def optima_stimmen(reihe: dict) -> tuple:
    """(Zahl der bewiesenen Optima aller Stufen, die dem von CP-SAT bewiesenen Optimum gleichen, Zahl der bewiesenen Optima mit bewiesenem CP-SAT-Wert)."""
    ok = tot = 0
    for z in reihe["instanzen"]:
        if not z["cpsat"]["bewiesen"]:
            continue
        for st in z["stufen"].values():
            if st["bewiesen"]:
                tot += 1
                ok += st["optimum"] == z["cpsat"]["optimum"]
    return ok, tot


def nie_unter_cpsat(reihe: dict) -> bool:
    """Kein Mini-CP-Wert liegt unter dem von CP-SAT bewiesenen Optimum."""
    return all(st["optimum"] >= z["cpsat"]["optimum"] for z in reihe["instanzen"] if z["cpsat"]["bewiesen"] for st in z["stufen"].values())


def cpsat_stat(reihe: dict) -> dict:
    ks = [z["cpsat"]["konflikte"] for z in reihe["instanzen"]]
    return {"n": len(ks), "median": median(ks), "max": max(ks), "bewiesen": sum(1 for z in reihe["instanzen"] if z["cpsat"]["bewiesen"])}


def groesse_statistik(gr: dict) -> list:
    """Je Zelle Median von H, Variablen und Klauseln (H = beste serielle Konstruktion), in der Reihenfolge der Zellen."""
    rows = []
    for key, g in gr.items():
        z = g["instanzen"]
        rows.append({"zelle": key, "n": g["n"], "ressourcen": g["ressourcen"], "kap": g["kap"], "instanzen": len(z), "H": median(i["H"] for i in z),
                     "variablen": median(i["variablen"] for i in z), "klauseln": median(i["klauseln"] for i in z)})
    return rows


def sat_statistik(reihe: dict) -> dict:
    """Median und Maximum der Konflikte des Kern-CDCL und von CP-SAT, Abbrüche, übereinstimmende Antworten, Variablen und Klauseln (Median)."""
    z = reihe["instanzen"]
    s = [i["sat_konflikte"] for i in z]
    c = [i["cpsat_konflikte"] for i in z]
    return {"n": len(z), "sat_median": median(s), "sat_max": max(s), "cpsat_median": median(c), "cpsat_max": max(c), "abbrueche": sum(1 for i in z if i["sat_antwort"] is None),
            "gleiche_antwort": sum(1 for i in z if i["sat_antwort"] == i["cpsat_antwort"]), "variablen": median(i["variablen"] for i in z), "klauseln": median(i["klauseln"] for i in z)}


# ------------------------------------------------------------------------------------------------------------------------------ Live-Läufe
def live_vergleich(s: Settings, stufen=C.STAGES) -> dict:
    """Die Einzelinstanz mit allen Stufen bis zum bewiesenen Optimum (oder bis zum Knotenbudget)."""
    inst = instanz(s)
    return {st: A.loese(inst, st, budget=s.budget) for st in stufen}


def live_reihe_einheit(zelle: str, seed: int, stufe: int, budget: int) -> dict:
    """Eine Einheit der Messreihe: eine Stufe auf einer Instanz der Zelle (Format wie in der vorgerechneten Reihe)."""
    n, res, cap = C.ZELLEN[zelle]
    r = A.loese(make_instanz(n, res, cap, seed), stufe, budget=budget)
    return {**{"optimum": r.optimum, "bewiesen": r.bewiesen}, **r.z.als_dict()}


def live_reihe_aufbauen(zelle: str, budget: int, einheit, stufen=C.STAGES) -> dict:
    """Setzt die Reihe aus den Einheiten zusammen; `einheit(zelle, seed, stufe, budget)` liefert eine Einheit (gerechnet oder aus dem Zwischenspeicher)."""
    n, res, cap = C.ZELLEN[zelle]
    zeilen = [{"seed": seed, "stufen": {str(st): einheit(zelle, seed, st, budget) for st in stufen}} for seed in C.SWEEP_SEEDS]
    return {"n": n, "ressourcen": res, "kap": cap, "seeds": list(C.SWEEP_SEEDS), "budget": budget, "stufen": list(stufen), "instanzen": zeilen}


def live_reihe(zelle: str, budget: int, stufen=C.STAGES) -> dict:
    """Messreihe auf Knopfdruck: die 10 festen Instanzen der Zelle, alle Stufen, im selben Format wie die vorgerechnete Reihe (ohne CP-SAT)."""
    return live_reihe_aufbauen(zelle, budget, live_reihe_einheit, stufen)


def widerspruch_im_optimum(erg: dict) -> bool:
    """Wahr, wenn zwei Stufen, die ihr Optimum bewiesen haben, verschiedene Werte nennen (darf nie vorkommen)."""
    return len({e.optimum for e in erg.values() if e.bewiesen}) > 1


# --------------------------------------------------------------------------------------------------------------------------------- Verdikte
def _zahl(x) -> str:
    """Ganze Zahl mit Tausenderpunkt, Halbe mit Komma (Mediane über eine gerade Zahl von Instanzen können ,5 sein)."""
    if isinstance(x, float) and not x.is_integer():
        return f"{x:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{int(x):,}".replace(",", ".")


def _faktor(a, b) -> str:
    return f"{a / b:.1f}".replace(".", ",")


def _prozent(x: float) -> str:
    return f"{round(100 * x)} %"


def verdict_pflichtteile(fix: "A.Fixpunkt", name: str, H: int, stufe: int, breite_vorrang: int) -> tuple:
    """Experiment 1 (Wurzel-Propagation eines Handbeispiels). `breite_vorrang`: Summe der Fensterbreiten nur aus Vorrang und Horizont."""
    schritte = sum(1 for e in fix.protokoll.ereignisse if e.art in ("timetabling",))
    if not fix.ok:
        letzter = next((e.text for e in reversed(fix.protokoll.ereignisse) if e.art == "fehlschlag"), "")
        return "success", (f"{name} bei Horizont {H}, {C.STAGE_NAMES[stufe]}: Fehlschlag an der Wurzel, also gibt es keinen Plan mit Makespan höchstens {H}, ohne dass gesucht wurde. "
                           f"Der Schluss: {letzter}")
    breite = A.fensterbreite(fix.est, fix.lst)
    if breite == breite_vorrang:
        return "info", (f"{name} bei Horizont {H}, {C.STAGE_NAMES[stufe]}: Fixpunkt ohne Fehlschlag und ohne verschobene Fenstergrenze (Summe der Fensterbreiten {breite}, unverändert gegenüber dem Vorrang allein). "
                        f"Hier sieht diese Stufe nichts; ein Plan ist damit nicht bewiesen.")
    schluss = "1 Timetabling-Schluss verkleinert" if schritte == 1 else f"{schritte} Timetabling-Schlüsse verkleinern"
    return "info", (f"{name} bei Horizont {H}, {C.STAGE_NAMES[stufe]}: {schluss} die Summe der Fensterbreiten von {breite_vorrang} auf {breite}; "
                    f"kein Fehlschlag, die Suche muss also weiter.")


def verdict_stufen(rows: list, titel: str) -> tuple:
    """Experiment 2: Timetabling gegen reine Vorrang-Verzweigung über eine Messreihe. `rows`: Statistik je Stufe 0, 1 (und 2) mit Median, 90-%-Wert, Maximum, bewiesen, Abbrüchen."""
    by = {r["stufe"]: r for r in rows}
    r0, r1 = by[0], by[1]
    n = r0["n"]
    satz = (f"{titel} ({n} feste Instanzen): Timetabling beweist das Optimum in {r1['bewiesen']} von {n} Instanzen im Knotenbudget, reine Vorrang-Verzweigung in {r0['bewiesen']}. "
            f"Median der Knoten: {_zahl(r0['median'])} gegen {_zahl(r1['median'])}")
    if r1["median"] > 0 and r0["median"] > r1["median"]:
        satz += f" ({_faktor(r0['median'], r1['median'])}-fach weniger)"
    satz += f"; 90-%-Wert {_zahl(r0['p90'])} gegen {_zahl(r1['p90'])}, Maximum {_zahl(r0['max'])} gegen {_zahl(r1['max'])}."
    ab = r0["abbrueche"] + r1["abbrueche"]
    if ab:
        satz += f" {ab} Läufe brachen am Knotenbudget ab; ihre Zahlen sind untere Schranken."
    art = "success" if r1["bewiesen"] > r0["bewiesen"] or (r1["median"] > 0 and r0["median"] >= 2 * r1["median"]) else "info"
    return art, satz


def verdict_energie(paar: dict, rows: list, titel: str) -> tuple:
    """Experiment 3: Energie-Überlastprüfung (Stufe 2) gegen Timetabling allein (Stufe 1). Schwelle „kaum Wirkung“: `C.SCHWELLE_KAUM_WIRKUNG` (Median der Ersparnis unter 20 % und keine zusätzlich bewiesene Instanz)."""
    by = {r["stufe"]: r for r in rows}
    p1, p2, n = by[1]["bewiesen"], by[2]["bewiesen"], paar["n"]
    kopf = f"{titel} ({n} feste Instanzen): Stufe 2 beweist {p2} von {n} Instanzen, Stufe 1 {p1}."
    if paar["beide"] == 0:
        return "info", kopf + " Keine Instanz wird von beiden Stufen bewiesen; die Ersparnis lässt sich deshalb nicht bestimmen."
    kopf += (f" Unter den {paar['beide']} Instanzen, die beide beweisen, spart die Energieprüfung im Median {_prozent(paar['median'])} der Knoten (Maximum {_prozent(paar['max'])}; "
             f"in {paar['mit_ersparnis']} dieser Instanzen überhaupt etwas, in {paar['gleich']} genau gleich viele Knoten).")
    if paar["mehr_bewiesen"] == 0 and paar["median"] < C.SCHWELLE_KAUM_WIRKUNG:
        return "info", kopf + f" Das ist kaum Wirkung (Schwelle: Median unter {_prozent(C.SCHWELLE_KAUM_WIRKUNG)} und keine zusätzlich bewiesene Instanz); gilt für diese einfache Fassung (nur Fehlschlag), nicht für Edge-Finding oder energetisches Schließen der Literatur."
    if paar["mehr_bewiesen"] > 0:
        return "success", kopf + f" Sie beweist {paar['mehr_bewiesen']} Instanz" + ("" if paar["mehr_bewiesen"] == 1 else "en") + " mehr als Stufe 1."
    return "success", kopf + f" Der Median liegt bei oder über der Schwelle von {_prozent(C.SCHWELLE_KAUM_WIRKUNG)}: eine spürbare Ersparnis."


def verdict_groesse(zeilen: list) -> tuple:
    """Experiment 4 (vorgerechnet): Wachstum der zeitindizierten Kodierung über die Zellen. `zeilen`: `groesse_statistik`."""
    teile = [f"Zelle {z['zelle']} (n = {z['n']}): {_zahl(z['variablen'])} Variablen, {_zahl(z['klauseln'])} Klauseln (H im Median {_zahl(z['H'])})" for z in zeilen]
    faktoren = [z2["klauseln"] / z1["klauseln"] for z1, z2 in zip(zeilen, zeilen[1:]) if z1["klauseln"]]
    satz = f"Median über {zeilen[0]['instanzen']} Instanzen je Zelle, H = beste serielle Konstruktion: " + "; ".join(teile) + "."
    if faktoren:
        satz += " Klauseln je Größenstufe: " + ", ".join("×" + _faktor(f, 1) for f in faktoren) + "."
    satz += " Die Kodierung wächst also mit der Größe stark; welcher Anteil am Fenster und welcher am Totalizer je Zeitpunkt liegt, ist nicht getrennt gemessen."
    return "info", satz


def verdict_sat(reihen: dict) -> tuple:
    """Experiment 4 (vorgerechnet): Konflikte des Kern-CDCL gegen CP-SAT. `reihen`: Name → `sat_statistik`."""
    namen = {"A_opt": "Zelle A, H = Optimum (erfüllbar)", "A_opt1": "Zelle A, H = Optimum − 1 (unerfüllbar)", "B_opt": "Zelle B, H = Optimum (erfüllbar)"}
    teile = []
    for key, st in reihen.items():
        t = (f"{namen.get(key, key)}: Kern-CDCL {_zahl(st['sat_median'])} Konflikte im Median (Maximum {_zahl(st['sat_max'])}), CP-SAT {_zahl(st['cpsat_median'])} (Maximum {_zahl(st['cpsat_max'])})")
        if st["cpsat_median"] > 0:
            t += f", Verhältnis der Mediane {_faktor(st['sat_median'], st['cpsat_median'])}"
        if st["abbrueche"]:
            t += f", {st['abbrueche']} Abbrüche am Budget"
        teile.append(t)
    gleich = sum(st["gleiche_antwort"] for st in reihen.values())
    n = sum(st["n"] for st in reihen.values())
    return "info", ("Konflikte (je " + str(next(iter(reihen.values()))["n"]) + " feste Instanzen): " + "; ".join(teile) + f". Die Antwort stimmt mit CP-SAT in {gleich} von {n} Läufen überein. "
                    "Konflikte beider Löser sind verschiedene Einheiten; ob der Unterschied am Lernen, an der Kodierung oder an der Stärke von CP-SAT liegt, ist nicht getrennt gemessen.")


def verdict_einzel(erg: dict, budget: int) -> tuple:
    """Experiment 2, Einzelinstanz live: Knoten je Stufe, Optimum, Abbrüche. `erg`: Stufe → `Ergebnis`."""
    if widerspruch_im_optimum(erg):
        return "error", "Widerspruch: zwei Stufen nennen verschiedene bewiesene Optima. Das darf nicht vorkommen."
    teile = []
    for s in sorted(erg):
        e = erg[s]
        teile.append(f"Stufe {s}: {_zahl(e.z.knoten)} Knoten" + ("" if e.bewiesen else " (Abbruch am Budget, untere Schranke)"))
    beweis = [e for e in erg.values() if e.bewiesen]
    if any(e.optimum is None for e in erg.values()):
        return "info", "Keine Aktivität darf mehr Bedarf haben als die Ressource Kapazität; mit dieser Instanz gibt es keinen Plan."
    if beweis:
        satz = f"Optimaler Makespan {beweis[0].optimum}, bewiesen von {len(beweis)} der {len(erg)} Stufen. "
    else:
        satz = f"Keine Stufe beweist das Optimum innerhalb von {_zahl(budget)} Knoten; der beste gefundene Makespan ist {min(e.optimum for e in erg.values())}. "
    text = satz + "; ".join(teile) + ". Einzelinstanz, kein Median."
    if 0 in erg and 1 in erg and erg[0].bewiesen and erg[1].bewiesen and erg[1].z.knoten > 0 and erg[0].z.knoten > erg[1].z.knoten:
        text += f" Stufe 0 braucht hier {_faktor(erg[0].z.knoten, erg[1].z.knoten)}-mal so viele Knoten wie Stufe 1."
    if 1 in erg and 2 in erg and erg[1].bewiesen and erg[2].bewiesen and erg[1].z.knoten == erg[2].z.knoten:
        text += " Die Energieprüfung spart auf dieser Instanz nichts."
    return "info", text


def verdict_sat_live(sat, H: int, mini: "A.Entscheidung", budget: int) -> tuple:
    """Experiment 4, Lauf des Kern-CDCL auf der Einzelinstanz gegen die Entscheidungsfassung des Mini-CP (Stufe 1)."""
    if sat.antwort is None:
        return "warning", f"Das Kern-CDCL bricht bei H = {H} nach {_zahl(sat.konflikte)} Konflikten (Budget {_zahl(budget)}) ab: keine Antwort."
    wort = "findet einen Plan mit Makespan höchstens" if sat.antwort else "beweist: kein Plan mit Makespan höchstens"
    satz = f"Das Kern-CDCL {wort} {H} nach {_zahl(sat.konflikte)} Konflikten ({_zahl(sat.variablen)} Variablen, {_zahl(sat.klauseln)} Klauseln)."
    if mini.gefunden is None:
        return "info", satz + " Die Entscheidungsfassung des Mini-CP bricht am Knotenbudget ab: kein Vergleich möglich."
    if mini.gefunden != sat.antwort:
        return "error", satz + f" Widerspruch: die Entscheidungsfassung des Mini-CP sagt {'Plan' if mini.gefunden else 'kein Plan'} ({_zahl(mini.z.knoten)} Knoten). Das darf nicht vorkommen."
    return "success", satz + f" Die Entscheidungsfassung des Mini-CP (Stufe 1) gibt dieselbe Antwort ({_zahl(mini.z.knoten)} Knoten)."
