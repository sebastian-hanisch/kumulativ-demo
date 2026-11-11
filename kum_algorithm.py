"""Mini-CP für das kumulative Ressourcenproblem: Zeitfenster, Vorrang, Timetabling (Pflichtteile), Energie-Überlastprüfung, Suche bis zum bewiesenen Optimum.

Eigener Code dieser Demo (nur Standardbibliothek), nach Gedächtnis geschrieben und **nicht gegen die Literatur geprüft**. Jede Aktivität i hat ein Fenster: frühester Start `est`,
spätester Start `lst` (aus dem Horizont H: Makespan höchstens H) und spätestes Ende `lct = lst + d`. Der **Pflichtteil** ist [lst, est + d): der Zeitraum, in dem i auf jeden Fall läuft.

Stufen der Propagation (`stufe`), jede enthält die vorige:
  0  nur Vorrang: Kanten (a vor b) aus der Instanz und aus beschlossenen Paaren schieben die Fenster; Ressourcen werden nur gegen schon festgelegte Starts geprüft, nichts beschnitten.
  1  + Timetabling: je Ressource das Profil der Pflichtteile; überschreitet es irgendwo die Kapazität, Fehlschlag; sonst werden est und lst jeder Aktivität über Zeitpunkte
     hinausgeschoben, in denen das Profil (ohne ihren eigenen Pflichtteil) plus ihr Bedarf die Kapazität übersteigt.
  2  + Energie-Überlastprüfung (einfache Fassung, **nur Fehlschlag**, kein Verschieben der Fenster und **kein Edge-Finding im Sinne der Literatur**): für jedes Fenster [a, b) darf die
     Energie (Dauer mal Bedarf) der Aktivitäten, die mit ihrem ganzen Fenster hineinpassen, höchstens Kapazität mal (b − a) betragen.

Gezählt wird der Aufwand in Suchknoten (Zustand nach der Propagation; ein Abbruch am Budget zählt mit), Fehlschlägen, Runden und Schlüssen, nie in Sekunden.
Verzweigt wird zuerst auf die Reihenfolge eines Paares, das sich nach den Fenstern überlappen kann und gemeinsam eine Kapazität überschreitet (i vor j oder j vor i; Paar mit der
kleinsten Spielraumsumme), sonst auf den Start (früheste Zeit oder eine Einheit später). Die Suche beginnt mit der Schranke der besten von fünf seriellen Konstruktionen."""

from dataclasses import dataclass

from kum_scenario import Instanz, beste_konstruktion, fruehester_start, pruefe_plan, untere_schranke

MAX_EREIGNISSE = 400


# ------------------------------------------------------------------------------------------------------------------------------- Modell
class Modell:
    """Aus der Instanz abgeleitete Tabellen: je Ressource (Kapazität, [(Aktivität, Bedarf)]) und die Paare, die nie gemeinsam laufen dürfen."""

    def __init__(self, inst: Instanz):
        self.inst = inst
        self.n = inst.n
        self.d = list(inst.d)
        self.ressourcen = [(inst.kap[r], [(i, inst.bedarf[r][i]) for i in range(inst.n) if inst.bedarf[r][i]]) for r in range(inst.ressourcen)]
        self.konflikt = [[any(inst.bedarf[r][i] + inst.bedarf[r][j] > inst.kap[r] for r in range(inst.ressourcen)) for j in range(inst.n)] for i in range(inst.n)]
        self.kanten = list(inst.kanten)

    def name(self, i: int) -> str:
        return self.inst.name(i)

    def ressource_text(self, r: int) -> str:
        return f" (Ressource {r + 1})" if len(self.ressourcen) > 1 else ""


@dataclass
class Zaehler:
    """Zähler der Suche. `fehl_*` ordnen jeden Fehlschlag dem Schluss zu, der ihn gefunden hat (Summe = `fehlschlaege`)."""

    knoten: int = 0
    fehlschlaege: int = 0
    blaetter: int = 0
    runden: int = 0
    loesungen: int = 0
    tt_schluesse: int = 0         # vom Timetabling verschobene Fenstergrenzen
    fehl_vorrang: int = 0         # leeres Fenster durch Vorrang oder Horizont
    fehl_fest: int = 0            # Stufe 0: Kapazität unter schon festgelegten Starts verletzt
    fehl_timetabling: int = 0     # Profil über Kapazität oder Aktivität ohne Startzeitpunkt
    fehl_energie: int = 0         # Energie-Überlast
    fehl_wurzel: int = 0          # Fehlschlag schon an der Wurzel (Beweis ohne Verzweigung)

    def als_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass(frozen=True)
class Ereignis:
    """Ein Schritt der Spur mit dem Zustand der Fenster danach (für die Schritt-für-Schritt-Ansicht)."""

    art: str        # start, horizont, vorrang, timetabling, energie, fehlschlag, fixpunkt
    text: str
    est: tuple
    lst: tuple


class Protokoll:
    """Sammelt Ereignisse, höchstens MAX_EREIGNISSE (danach `abgeschnitten`)."""

    def __init__(self, limit: int = MAX_EREIGNISSE):
        self.ereignisse: list = []
        self.limit = limit
        self.abgeschnitten = False

    def add(self, art: str, text: str, est, lst):
        if len(self.ereignisse) >= self.limit:
            self.abgeschnitten = True
            return
        self.ereignisse.append(Ereignis(art, text, tuple(est), tuple(lst)))


def _log(prot, art, text, est, lst):
    if prot is not None:
        prot.add(art, text, est, lst)


# ------------------------------------------------------------------------------------------------------------------------------ Propagation
def _vorrang(M: Modell, est, lst, kanten, H, prot):
    """Horizont und Kanten: Fenster schieben, bis sich nichts mehr ändert. None = ein Fenster ist leer (Fehlschlag), sonst True/False (etwas verändert?)."""
    d = M.d
    veraendert = False
    while True:
        bewegt = False
        for i in range(M.n):
            if lst[i] > H - d[i]:
                lst[i] = H - d[i]
                _log(prot, "horizont", f"Horizont H = {H}: lst({M.name(i)}) → {lst[i]}", est, lst)
                bewegt = True
        for a, b in kanten:
            if est[a] + d[a] > est[b]:
                est[b] = est[a] + d[a]
                _log(prot, "vorrang", f"Vorrang {M.name(a)} vor {M.name(b)}: est({M.name(b)}) → {est[b]}", est, lst)
                bewegt = True
            if lst[b] - d[a] < lst[a]:
                lst[a] = lst[b] - d[a]
                _log(prot, "vorrang", f"Vorrang {M.name(a)} vor {M.name(b)}: lst({M.name(a)}) → {lst[a]}", est, lst)
                bewegt = True
        for o in range(M.n):
            if est[o] > lst[o]:
                _log(prot, "fehlschlag", f"Das Fenster von {M.name(o)} ist leer (est {est[o]} > lst {lst[o]}) → Fehlschlag", est, lst)
                return None
        if not bewegt:
            return veraendert
        veraendert = True


def _fest_pruefung(M: Modell, est, lst):
    """Stufe 0: Kapazität nur gegen schon festgelegte Aktivitäten (est = lst). None, wenn in Ordnung, sonst (Ressource, Zeitpunkt, Last)."""
    for r, (cap, akt) in enumerate(M.ressourcen):
        ereignisse = {}
        for i, c in akt:
            if est[i] == lst[i]:
                ereignisse[est[i]] = ereignisse.get(est[i], 0) + c
                ereignisse[est[i] + M.d[i]] = ereignisse.get(est[i] + M.d[i], 0) - c
        last = 0
        for t in sorted(ereignisse):
            last += ereignisse[t]
            if last > cap:
                return r, t, last
    return None


def _timetabling(M: Modell, est, lst, H, prot):
    """Profil der Pflichtteile je Ressource, Überlastprüfung, Verschieben von est und lst. Rückgabe (ok, geändert, Zahl der verschobenen Grenzen).

    Das Profil wird je Ressource einmal aufgebaut und dann nicht nachgeführt; es ist deshalb höchstens so groß wie das wahre (schwächer, aber gültig), der Fixpunkt der Außenschleife holt den Rest."""
    d = M.d
    geaendert = False
    verschoben = 0
    for r, (cap, akt) in enumerate(M.ressourcen):
        res = M.ressource_text(r)
        prof = [0] * (H + 2)
        eigen = {}
        for i, c in akt:
            if lst[i] < est[i] + d[i]:
                eigen[i] = (lst[i], est[i] + d[i])
                for t in range(lst[i], est[i] + d[i]):
                    prof[t] += c
        for t in range(len(prof)):
            if prof[t] > cap:
                _log(prot, "fehlschlag", f"Im Zeitpunkt {t} läuft laut Pflichtteilen Bedarf {prof[t]} > Kapazität {cap}{res} → Fehlschlag", est, lst)
                return False, geaendert, verschoben
        for i, c in akt:
            if est[i] == lst[i]:
                continue
            lo, hi = eigen.get(i, (0, 0))
            di = d[i]
            # Die Schleife sucht den ersten Start s >= est, dessen Zeitpunkte alle frei genug sind; `schlecht` ist der letzte blockierte Zeitpunkt im Fenster [s, s + d).
            s, grund = est[i], None
            while s <= lst[i]:
                schlecht = -1
                for t in range(s, s + di):
                    if prof[t] - (c if lo <= t < hi else 0) + c > cap:
                        schlecht = t
                if schlecht < 0:
                    break
                grund = schlecht
                s = schlecht + 1
            if s > lst[i]:
                _log(prot, "fehlschlag", f"{M.name(i)}{res}: kein Startzeitpunkt im Fenster [{est[i]}, {lst[i]}] mit Profil {prof[:H]} (Dauer {di}, Bedarf {c}, Kapazität {cap}) → Fehlschlag", est, lst)
                return False, geaendert, verschoben
            if s > est[i]:
                p = prof[grund] - (c if lo <= grund < hi else 0)
                alt = est[i]
                est[i] = s
                _log(prot, "timetabling", f"{M.name(i)} kann im Zeitpunkt {grund} nicht laufen{res}: Profil {p} + Bedarf {c} > Kapazität {cap}, est({M.name(i)}) {alt} → {s}", est, lst)
                geaendert = True
                verschoben += 1
            e, grund = lst[i], None
            while e >= est[i]:
                schlecht = -1
                for t in range(e + di - 1, e - 1, -1):
                    if prof[t] - (c if lo <= t < hi else 0) + c > cap:
                        schlecht = t
                        break
                if schlecht < 0:
                    break
                grund = schlecht
                e = schlecht - di
            if e < est[i]:
                _log(prot, "fehlschlag", f"{M.name(i)}{res}: kein Startzeitpunkt im Fenster [{est[i]}, {lst[i]}] mit Profil {prof[:H]} (Dauer {di}, Bedarf {c}, Kapazität {cap}) → Fehlschlag", est, lst)
                return False, geaendert, verschoben
            if e < lst[i]:
                p = prof[grund] - (c if lo <= grund < hi else 0)
                alt = lst[i]
                lst[i] = e
                _log(prot, "timetabling", f"{M.name(i)} kann im Zeitpunkt {grund} nicht laufen{res}: Profil {p} + Bedarf {c} > Kapazität {cap}, lst({M.name(i)}) {alt} → {e}", est, lst)
                geaendert = True
                verschoben += 1
    return True, geaendert, verschoben


def _energie(M: Modell, est, lst):
    """Energie-Überlastprüfung. None, wenn in Ordnung, sonst (Ressource, a, b, Energie, Kapazität mal Länge)."""
    d = M.d
    for r, (cap, akt) in enumerate(M.ressourcen):
        nach_ende = sorted(akt, key=lambda ic: lst[ic[0]] + d[ic[0]])
        for a in sorted({est[i] for i, _ in akt}):
            summe = 0
            for i, c in nach_ende:
                if est[i] >= a:
                    summe += d[i] * c
                    b = lst[i] + d[i]
                    if b > a and summe > cap * (b - a):
                        return r, a, b, summe, cap * (b - a)
    return None


def _energie_text(M: Modell, est, lst, treffer):
    r, a, b, summe, kapl = treffer
    cap, akt = M.ressourcen[r]
    drin = [(i, c) for i, c in akt if est[i] >= a and lst[i] + M.d[i] <= b]
    teile = " + ".join(f"{M.name(i)}: {M.d[i]}·{c}" for i, c in drin)
    return f"Im Fenster [{a}, {b}){M.ressource_text(r)} brauchen die ganz hineinpassenden Aktivitäten die Energie {teile} = {summe} > Kapazität {cap} · Länge {b - a} = {kapl} → Fehlschlag"


def propagiere(M: Modell, est, lst, kanten, H, stufe, z: Zaehler, prot=None) -> bool:
    """Fixpunkt der Stufe `stufe` für den Horizont H (verändert est und lst); False bei Fehlschlag. Die Fehlschläge ordnet der Zähler dem Schluss zu."""
    while True:
        z.runden += 1
        v = _vorrang(M, est, lst, kanten, H, prot)
        if v is None:
            z.fehl_vorrang += 1
            return False
        geaendert = v
        if stufe == 0:
            treffer = _fest_pruefung(M, est, lst)
            if treffer is not None:
                z.fehl_fest += 1
                _log(prot, "fehlschlag", f"Im Zeitpunkt {treffer[1]} laufen festgelegte Aktivitäten mit Bedarf {treffer[2]} > Kapazität {M.ressourcen[treffer[0]][0]} → Fehlschlag", est, lst)
                return False
        else:
            ok, ch, n_verschoben = _timetabling(M, est, lst, H, prot)
            z.tt_schluesse += n_verschoben
            if not ok:
                z.fehl_timetabling += 1
                return False
            geaendert = geaendert or ch
            if stufe >= 2:
                treffer = _energie(M, est, lst)
                if treffer is not None:
                    z.fehl_energie += 1
                    _log(prot, "fehlschlag", _energie_text(M, est, lst, treffer), est, lst)
                    return False
        if not geaendert:
            return True


# ----------------------------------------------------------------------------------------------------------------------------------- Suche
def _erreichbar(M: Modell, kanten) -> list:
    """Bitmasken: reach[i] hat Bit j, wenn j von i über Kanten erreichbar ist (i selbst eingeschlossen)."""
    nach = [[] for _ in range(M.n)]
    for a, b in kanten:
        nach[a].append(b)
    reach = [1 << i for i in range(M.n)]
    for i in reversed(range(M.n)):                 # Kanten gehen von kleinem zu großem Index
        for j in nach[i]:
            reach[i] |= reach[j]
    return reach


def _neue_kante(M: Modell, i, j, kanten, reach):
    rc = list(reach)
    for a in range(M.n):
        if (reach[a] >> i) & 1:
            rc[a] |= reach[j]
    return kanten + [(i, j)], rc


def _waehle_paar(M: Modell, est, lst, reach):
    """Paar (i, j), das gemeinsam eine Kapazität überschreitet, noch nicht geordnet ist und sich nach den Fenstern überlappen kann; kleinste Spielraumsumme, Gleichstand: kleinstes Paar."""
    d = M.d
    beste, schluessel = None, None
    for i in range(M.n):
        for j in range(i + 1, M.n):
            if not M.konflikt[i][j] or (reach[i] >> j) & 1 or (reach[j] >> i) & 1:
                continue
            if est[i] < lst[j] + d[j] and est[j] < lst[i] + d[i]:
                k = (lst[i] - est[i]) + (lst[j] - est[j])
                if schluessel is None or k < schluessel:
                    beste, schluessel = (i, j), k
    return beste


@dataclass
class Ergebnis:
    """Ergebnis der Optimierung. `optimum`: bester gefundener Makespan (bei `bewiesen` das Optimum, sonst eine obere Schranke), None, wenn es keinen Plan gibt."""

    optimum: int | None
    bewiesen: bool
    plan: list | None
    start_schranke: int | None
    z: Zaehler


@dataclass
class Entscheidung:
    """Ergebnis der Entscheidungsfassung „gibt es einen Plan mit Makespan höchstens H?“: `gefunden` True/False, None bei Abbruch am Budget."""

    gefunden: bool | None
    plan: list | None
    z: Zaehler


def _suche(M: Modell, stufe, budget, ub, best, lb, stop_erste, est0, lst0):
    """Iterative Tiefensuche (kein Rekursionslimit). Rückgabe (ub, best, bewiesen, Zähler)."""
    z = Zaehler()
    kanten0 = list(M.kanten)
    stapel = [(est0, lst0, kanten0, _erreichbar(M, kanten0))]
    bewiesen = True
    while stapel:
        if ub <= lb:
            break
        est, lst, kanten, reach = stapel.pop()
        z.knoten += 1
        if z.knoten > budget:
            bewiesen = False
            break
        if not propagiere(M, est, lst, kanten, ub - 1, stufe, z):
            z.fehlschlaege += 1
            if z.knoten == 1:
                z.fehl_wurzel += 1
            continue
        paar = _waehle_paar(M, est, lst, reach)
        if paar is not None:
            i, j = paar
            for a, b in ((j, i), (i, j)):                       # (i vor j) wird zuerst gerechnet, liegt also oben auf dem Stapel
                ed, rc = _neue_kante(M, a, b, kanten, reach)
                stapel.append((list(est), list(lst), ed, rc))
            continue
        frei = [i for i in range(M.n) if est[i] < lst[i]]
        if not frei:
            z.blaetter += 1
            cm = max(est[i] + M.d[i] for i in range(M.n)) if M.n else 0
            if cm < ub:
                ok, grund = pruefe_plan(M.inst, est)
                if not ok:
                    raise AssertionError(f"Plan verletzt die Instanz: {grund}")
                ub, best = cm, list(est)
                z.loesungen += 1
                if stop_erste:
                    break
            continue
        i = min(frei, key=lambda k: (est[k], lst[k] - est[k]))
        e3, l3 = list(est), list(lst)
        e3[i] = est[i] + 1
        stapel.append((e3, l3, kanten, reach))
        l2 = list(lst)
        l2[i] = est[i]
        stapel.append((list(est), l2, kanten, reach))
    return ub, best, bewiesen, z


def loese(inst: Instanz, stufe: int, budget: int = 20000) -> Ergebnis:
    """Kleinster Makespan: Start mit der besten seriellen Konstruktion, nach jedem Plan sinkt der Horizont auf Makespan − 1; Abbruch, wenn der Horizont die untere Schranke
    (längste Kette, Energie) unterschreitet. Bei Abbruch am Budget ist `optimum` nur eine obere Schranke und `bewiesen` falsch."""
    konstruktion = beste_konstruktion(inst)
    if konstruktion is None:                                    # ein Bedarf über der Kapazität: es gibt keinen Plan
        return Ergebnis(None, True, None, None, Zaehler())
    ub0, plan0 = konstruktion
    M = Modell(inst)
    lb = untere_schranke(inst)
    if ub0 - 1 < lb:
        return Ergebnis(ub0, True, plan0, ub0, Zaehler())
    est0 = fruehester_start(inst)
    lst0 = [ub0 - 1 - M.d[i] for i in range(M.n)]
    ub, best, bewiesen, z = _suche(M, stufe, budget, ub0, list(plan0), lb, False, est0, lst0)
    return Ergebnis(ub, bewiesen, best, ub0, z)


def entscheide(inst: Instanz, H: int, stufe: int, budget: int = 20000) -> Entscheidung:
    """Entscheidungsfassung: gibt es einen Plan mit Makespan höchstens H? Die Suche endet beim ersten Plan oder mit dem Beweis, dass es keinen gibt; keine Abkürzung über untere Schranken,
    die Propagation entscheidet allein."""
    M = Modell(inst)
    if M.n == 0:
        return Entscheidung(True, [], Zaehler())
    est0 = fruehester_start(inst)
    lst0 = [H - M.d[i] for i in range(M.n)]
    ub, best, bewiesen, z = _suche(M, stufe, budget, H + 1, None, -1, True, est0, lst0)
    if best is not None:
        return Entscheidung(True, best, z)
    return Entscheidung(False if bewiesen else None, None, z)


@dataclass
class Fixpunkt:
    """Die Propagation an der Wurzel für den Horizont H: Fenster nach jedem Schritt (`protokoll`), am Ende `ok` (False = Fehlschlag), `est` und `lst` im Endzustand."""

    ok: bool
    est: list
    lst: list
    protokoll: Protokoll
    z: Zaehler


def fixpunkt(inst: Instanz, H: int, stufe: int) -> Fixpunkt:
    """Wurzel-Propagation mit Spur: erst die Fenster nur aus Vorrang und Horizont („start“), dann jeder Schluss der Stufe einzeln, am Ende „fixpunkt“ oder „fehlschlag“."""
    M = Modell(inst)
    est = fruehester_start(inst)
    lst = [H - M.d[i] for i in range(M.n)]
    z = Zaehler()
    prot = Protokoll()
    v = _vorrang(M, est, lst, M.kanten, H, None)
    if v is None:
        prot.add("start", f"Schon der Vorrang macht ein Fenster leer: Horizont H = {H} ist kürzer als eine Kette von Aktivitäten.", est, lst)
        z.fehl_vorrang += 1
        return Fixpunkt(False, est, lst, prot, z)
    prot.add("start", f"Fenster bei H = {H} nur aus Vorrang und Horizont; Pflichtteil einer Aktivität = [lst, est + d).", est, lst)
    ok = propagiere(M, est, lst, M.kanten, H, stufe, z, prot)
    if ok:
        prot.add("fixpunkt", "Fixpunkt: kein Schluss verändert mehr ein Fenster.", est, lst)
    return Fixpunkt(ok, est, lst, prot, z)


def pflichtprofil(inst: Instanz, est, lst, H: int, r: int = 0) -> list:
    """Profil der Pflichtteile der Ressource r in den Zeitpunkten 0 .. H − 1 (Summe der Bedarfe der Aktivitäten mit lst <= t < est + d)."""
    prof = [0] * H
    for i in range(inst.n):
        c = inst.bedarf[r][i]
        for t in range(lst[i], est[i] + inst.d[i]):
            if c and 0 <= t < H:
                prof[t] += c
    return prof


def fensterbreite(est, lst) -> int:
    """Summe der Fensterbreiten (lst − est)."""
    return sum(l - e for e, l in zip(est, lst))
