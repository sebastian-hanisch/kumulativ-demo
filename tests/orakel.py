"""Orakel für die Tests: andere Rechenwege als die der Demo (ORACLE-PLAYBOOK §2: Scheduling → Aufzählung, CP-SAT).

* `ist_plan`: eigener, bewusst schlichter Prüfer (Mengen statt Zähler, eine Funktion, kein Code aus `kum_scenario`).
* `alle_plaene`: **alle** ganzzahligen Startzeitvektoren mit `itertools.product` über die vollen Bereiche [0, H − d_i] und danach gefiltert (kein Ausschneiden unterwegs).
* `cpsat_optimum` / `cpsat_entscheidung`: OR-Tools CP-SAT mit `AddCumulative` (nur im Test-venv)."""

import functools
import itertools


def ist_plan(inst, s, H=None):
    n = len(inst.d)
    if H is not None and any(s[i] + inst.d[i] > H for i in range(n)):
        return False
    for i, j in inst.kanten:
        if s[i] + inst.d[i] > s[j]:
            return False
    zeitpunkte = range(max(s[i] + inst.d[i] for i in range(n))) if n else []
    for r in range(len(inst.kap)):
        for t in zeitpunkte:
            laufen = {i for i in range(n) if s[i] <= t < s[i] + inst.d[i]}
            if sum(inst.bedarf[r][i] for i in laufen) > inst.kap[r]:
                return False
    return True


@functools.lru_cache(maxsize=None)
def alle_plaene(inst, H):
    bereiche = [range(0, H - d + 1) for d in inst.d]
    return [v for v in itertools.product(*bereiche) if ist_plan(inst, v, H)]


@functools.lru_cache(maxsize=None)
def optimum(inst, hoechst=30):
    for H in range(max(inst.d), hoechst):
        if alle_plaene(inst, H):
            return H
    raise AssertionError("kein Optimum bis zum Höchstwert")


def cpsat_optimum(inst):
    """(Optimum, bewiesen) mit CP-SAT (ein Arbeiter, 60 s)."""
    from ortools.sat.python import cp_model

    horizont = sum(inst.d)
    m = cp_model.CpModel()
    s = [m.NewIntVar(0, horizont, f"s{i}") for i in range(len(inst.d))]
    iv = [m.NewIntervalVar(s[i], inst.d[i], s[i] + inst.d[i], f"i{i}") for i in range(len(inst.d))]
    for i, j in inst.kanten:
        m.Add(s[i] + inst.d[i] <= s[j])
    for r in range(len(inst.kap)):
        idx = [i for i in range(len(inst.d)) if inst.bedarf[r][i]]
        m.AddCumulative([iv[i] for i in idx], [inst.bedarf[r][i] for i in idx], inst.kap[r])
    cm = m.NewIntVar(0, horizont, "cm")
    for i in range(len(inst.d)):
        m.Add(cm >= s[i] + inst.d[i])
    m.Minimize(cm)
    lv = cp_model.CpSolver()
    lv.parameters.num_workers = 1
    lv.parameters.max_time_in_seconds = 60
    st = lv.Solve(m)
    return int(round(lv.ObjectiveValue())), st == cp_model.OPTIMAL


def cpsat_entscheidung(inst, H):
    """True/False: gibt es einen Plan mit Makespan höchstens H (CP-SAT)?"""
    from ortools.sat.python import cp_model

    m = cp_model.CpModel()
    n = len(inst.d)
    s = [m.NewIntVar(0, max(0, H - inst.d[i]), f"s{i}") for i in range(n)]
    iv = [m.NewIntervalVar(s[i], inst.d[i], s[i] + inst.d[i], f"i{i}") for i in range(n)]
    for i, j in inst.kanten:
        m.Add(s[i] + inst.d[i] <= s[j])
    for r in range(len(inst.kap)):
        idx = [i for i in range(n) if inst.bedarf[r][i]]
        m.AddCumulative([iv[i] for i in idx], [inst.bedarf[r][i] for i in idx], inst.kap[r])
    lv = cp_model.CpSolver()
    lv.parameters.num_workers = 1
    lv.parameters.max_time_in_seconds = 60
    st = lv.Solve(m)
    assert st in (cp_model.OPTIMAL, cp_model.FEASIBLE, cp_model.INFEASIBLE), st
    return st != cp_model.INFEASIBLE
