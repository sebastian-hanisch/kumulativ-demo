"""Messskript für `kum_sweeps.json`: die vorgerechneten Messreihen der Demo (in der App „vorgerechnet, nicht live“).

Aufruf (aus dem Repo-Ordner, mit dem Test-venv, das OR-Tools für die Gegenprobe enthält):
    python tools/messung_sweeps.py [--nur stufen,groesse,sat]

Gemessen wird in Suchknoten und Konflikten, nie in Sekunden. Zelle A, B, C: je 10 feste Instanzen (Zufalls-Seeds 0 bis 9, SplitMix64), die Stufen 0, 1, 2 des Mini-CP mit Knotenbudget 20.000
und der Gegenprobe OR-Tools CP-SAT (`AddCumulative`, ein Arbeiter, 60 s Grenze). Größe der zeitindizierten Kodierung: Zellen A bis D (H = beste serielle Konstruktion), exakt gezählt und
für die Zellen A bis C zusätzlich mit der gebauten Kodierung verglichen. SAT-Konflikte: die ersten sechs Seeds, Kern-CDCL, Konfliktbudget 20.000, H = Optimum (CP-SAT) und Optimum − 1.
OR-Tools gehört nur in `requirements-dev.txt`; die App liest ausschließlich die JSON-Datei."""

import argparse
import json
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import kum_algorithm as A  # noqa: E402
import kum_constants as C  # noqa: E402
import kum_sat as S  # noqa: E402
from kum_scenario import Instanz, beste_konstruktion, make_instanz, untere_schranke  # noqa: E402

OUT = ROOT / C.SWEEPS_FILE
CPSAT_ZEIT = 60


def _cpsat_modell(inst: Instanz, horizont: int):
    from ortools.sat.python import cp_model

    m = cp_model.CpModel()
    s = [m.NewIntVar(0, max(0, horizont - inst.d[i]), f"s{i}") for i in range(inst.n)]
    iv = [m.NewIntervalVar(s[i], inst.d[i], s[i] + inst.d[i], f"i{i}") for i in range(inst.n)]
    for i, j in inst.kanten:
        m.Add(s[i] + inst.d[i] <= s[j])
    for r in range(inst.ressourcen):
        idx = [i for i in range(inst.n) if inst.bedarf[r][i]]
        m.AddCumulative([iv[i] for i in idx], [inst.bedarf[r][i] for i in idx], inst.kap[r])
    return m, s


def cpsat_optimum(inst: Instanz) -> dict:
    """Optimum mit OR-Tools CP-SAT (AddCumulative, ein Arbeiter): optimum (oder bester Wert), bewiesen, Konflikte, Branches."""
    from ortools.sat.python import cp_model

    horizont = sum(inst.d)
    m, s = _cpsat_modell(inst, horizont)
    cm = m.NewIntVar(0, horizont, "cm")
    for i in range(inst.n):
        m.Add(cm >= s[i] + inst.d[i])
    m.Minimize(cm)
    lv = cp_model.CpSolver()
    lv.parameters.num_workers = 1
    lv.parameters.max_time_in_seconds = CPSAT_ZEIT
    status = lv.Solve(m)
    wert = int(round(lv.ObjectiveValue())) if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None
    return {"optimum": wert, "bewiesen": status == cp_model.OPTIMAL, "konflikte": int(lv.NumConflicts()), "branches": int(lv.NumBranches())}


def cpsat_entscheidung(inst: Instanz, H: int) -> dict:
    """Entscheidungsfassung „Plan mit Makespan höchstens H?“: antwort True/False/None, Konflikte."""
    from ortools.sat.python import cp_model

    m, _ = _cpsat_modell(inst, H)
    lv = cp_model.CpSolver()
    lv.parameters.num_workers = 1
    lv.parameters.max_time_in_seconds = CPSAT_ZEIT
    status = lv.Solve(m)
    antwort = {cp_model.OPTIMAL: True, cp_model.FEASIBLE: True, cp_model.INFEASIBLE: False}.get(status)
    return {"antwort": antwort, "konflikte": int(lv.NumConflicts())}


def _zelle(key: str) -> tuple:
    return C.ZELLEN[key]


def stufenreihe(key: str, seeds=C.SWEEP_SEEDS, budget: int = C.SWEEP_BUDGET, stufen=C.STAGES) -> dict:
    n, res, cap = _zelle(key)
    zeilen = []
    for seed in seeds:
        inst = make_instanz(n, res, cap, seed)
        cp = cpsat_optimum(inst)
        zeile = {"seed": seed, "untere_schranke": untere_schranke(inst), "start_schranke": beste_konstruktion(inst)[0], "cpsat": cp, "stufen": {}}
        for s in stufen:
            r = A.loese(inst, s, budget)
            zeile["stufen"][str(s)] = {"optimum": r.optimum, "bewiesen": r.bewiesen, **r.z.als_dict()}
        zeilen.append(zeile)
        print(f"Zelle {key} Seed {seed}: CP-SAT {cp['optimum']} ({'bewiesen' if cp['bewiesen'] else 'NICHT bewiesen'}, {cp['konflikte']} Konflikte); Knoten",
              {s: zeile["stufen"][str(s)]["knoten"] for s in stufen}, flush=True)
    return {"n": n, "ressourcen": res, "kap": cap, "seeds": list(seeds), "budget": budget, "stufen": list(stufen), "instanzen": zeilen}


def groessenreihe(key: str, seeds=C.SWEEP_SEEDS) -> dict:
    n, res, cap = _zelle(key)
    zeilen = []
    for seed in seeds:
        inst = make_instanz(n, res, cap, seed)
        H = beste_konstruktion(inst)[0]
        v, k = S.groesse(inst, H)
        if key != "D":                              # gezählte Größe gegen die gebaute Kodierung (D: 460.000 Klauseln, nur gezählt)
            kod = S.kodiere(inst, H)
            assert (kod.n_variablen, len(kod.klauseln)) == (v, k), (key, seed)
        zeilen.append({"seed": seed, "H": H, "variablen": v, "klauseln": k})
        print(f"Größe Zelle {key} Seed {seed}: H {H}, {v} Variablen, {k} Klauseln", flush=True)
    return {"n": n, "ressourcen": res, "kap": cap, "seeds": list(seeds), "instanzen": zeilen}


def satreihe(key: str, fall: str, seeds=C.SAT_SEEDS, budget: int = C.SAT_BUDGET) -> dict:
    """`fall`: „opt“ (H = Optimum, erfüllbar) oder „opt1“ (H = Optimum − 1, unerfüllbar); Optimum von CP-SAT (nur Instanzen, die CP-SAT bewiesen hat)."""
    n, res, cap = _zelle(key)
    zeilen = []
    for seed in seeds:
        inst = make_instanz(n, res, cap, seed)
        cp = cpsat_optimum(inst)
        if not cp["bewiesen"]:
            raise RuntimeError(f"CP-SAT beweist das Optimum von Zelle {key} Seed {seed} nicht")
        H = cp["optimum"] - (1 if fall == "opt1" else 0)
        e = cpsat_entscheidung(inst, H)
        t0 = time.time()
        sr = S.sat_entscheide(inst, H, budget)
        zeilen.append({"seed": seed, "H": H, "optimum": cp["optimum"], "sat_antwort": sr.antwort, "sat_konflikte": sr.konflikte, "variablen": sr.variablen, "klauseln": sr.klauseln,
                       "cpsat_antwort": e["antwort"], "cpsat_konflikte": e["konflikte"]})
        print(f"SAT Zelle {key} {fall} Seed {seed}: H {H}, SAT {sr.antwort} {sr.konflikte} Konflikte, CP-SAT {e['antwort']} {e['konflikte']} ({time.time() - t0:.0f} s)", flush=True)
    return {"zelle": key, "fall": fall, "seeds": list(seeds), "budget": budget, "instanzen": zeilen}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nur", default="stufen,groesse,sat")
    args = ap.parse_args()
    teile = set(args.nur.split(","))
    daten = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    import ortools

    daten["meta"] = {"skript": C.MEASURE_SCRIPT, "ortools": ortools.__version__, "python": platform.python_version(), "datum": time.strftime("%Y-%m-%d"),
                     "hinweis": "Zufalls-Seeds sind SplitMix64-Seeds (kum_scenario.make_instanz); CP-SAT mit einem Arbeiter und 60 s Grenze"}
    if "stufen" in teile:
        daten["reihen"] = {key: stufenreihe(key) for key in ("A", "B", "C")}
        OUT.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    if "groesse" in teile:
        daten["groesse"] = {key: groessenreihe(key) for key in ("A", "B", "C", "D")}
        OUT.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    if "sat" in teile:
        daten["sat"] = {"A_opt": satreihe("A", "opt"), "A_opt1": satreihe("A", "opt1"), "B_opt": satreihe("B", "opt")}
        OUT.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("fertig")


if __name__ == "__main__":
    sys.exit(main())
