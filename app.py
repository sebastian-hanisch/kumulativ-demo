"""Kumulativ – Pflichtteile statt Paare - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Eine Ressource mit Kapazität größer 1 lässt mehrere Aktivitäten zugleich laufen. Das Mini-CP dieser Demo zählt Suchknoten bei drei Stufen der Propagation (nur Vorrang, + Timetabling,
+ Energie-Überlastprüfung) und zählt die Größe der zeitindizierten SAT-Kodierung.

Lauffähig mit: streamlit run app.py
"""

import streamlit as st

import kum_algorithm as A
import kum_aufzaehlung as Z
import kum_constants as C
import kum_evaluation as ev
import kum_live as L
import kum_sat as S
from kum_layout import dunkles_design, kopf_css
from kum_presets import (
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    sidebar_presets,
    sync_query_params,
    SETTING_SPECS,
)
from kum_scenario import HANDBEISPIELE, beste_konstruktion, make_instanz, makespan, pruefe_plan
from kum_visualization import build_fenster_profil, build_gantt, build_groesse, build_konflikte, build_verteilung

st.set_page_config(page_title="Kumulativ – Sebastian Hanisch", layout="wide")


def _zahl(x) -> str:
    return ev._zahl(x)


def _md_table(headers, rows) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


@st.cache_data(show_spinner=False)
def _fixpunkt(bsp, H, stufe):
    return A.fixpunkt(HANDBEISPIELE[C.HB_NAMEN[bsp]], H, stufe)


@st.cache_data(show_spinner=False)
def _aufzaehlung(bsp):
    return Z.aufzaehlen(HANDBEISPIELE[C.HB_NAMEN[bsp]])


@st.cache_data(show_spinner=False, max_entries=16)
def _optimum_live(seed, n, res, cap, budget):
    return A.loese(make_instanz(n, res, cap, seed), 1, budget)


@st.cache_data(show_spinner=False, max_entries=16)
def _sat_live(seed, n, res, cap, H, budget):
    return S.sat_entscheide(make_instanz(n, res, cap, seed), H, budget)


@st.cache_data(show_spinner=False, max_entries=16)
def _mini_entscheidung(seed, n, res, cap, H, budget):
    return A.entscheide(make_instanz(n, res, cap, seed), H, 1, budget)


@st.cache_data(show_spinner=False)
def _groessenkurve(seed, res, cap):
    punkte = []
    for n in range(C.N_MIN, C.N_MAX + 1, 5):
        inst = make_instanz(n, res, cap, seed)
        g = S.groesse(inst, beste_konstruktion(inst)[0])
        punkte.append((n, g[1]))
    return punkte


DATA = ev.lade_sweeps()
REIHEN = DATA["reihen"]

# Fester Kopf: nur der Titel bleibt beim Scrollen oben (Stylesheet in kum_layout.py).
st.html(kopf_css(dunkles_design()))
with st.container(key="kopf"):
    st.title("🧩 Kumulativ – Pflichtteile statt Paare")
st.markdown(
    """
Eine **kumulative Ressource** hat eine Kapazität größer 1: Mehrere Aktivitäten dürfen zugleich laufen, solange ihr Bedarf zusammen die Kapazität nicht übersteigt. Wer nur Paare betrachtet, übersieht, was das **Zeitprofil der Pflichtteile** schon weiß:
Wo eine Aktivität wegen ihres engen Fensters sicher läuft, ist Kapazität belegt, und die Fenster der anderen schrumpfen. Das **Constraint Programming** (CP) nutzt das als **Timetabling**.
Diese Demo zählt **Suchknoten** bis zum bewiesenen Optimum bei drei Stufen (nur **Vorrang**, dazu **Timetabling**, dazu eine **Energie-Überlastprüfung**) und zählt die Größe der **zeitindizierten SAT-Kodierung** derselben Aufgabe.

Unten: die Experimente (**🎯 Pflichtteile von Hand**, **Stufen im Vergleich**, **Energie-Überlastprüfung**, **Größe der SAT-Kodierung**), der Abschnitt **🚧 Wo die Annahmen enden** und der Expander **📐 Mathematische Formulierung**.
"""
)

with st.expander("So funktioniert die Propagation bei Kapazität größer 1", expanded=True):
    st.markdown(
        """
Jede Aktivität hat ein **Fenster**: frühester Start `est`, spätester Start `lst` (aus dem Horizont H: Makespan höchstens H) und spätestes Ende `lct = lst + Dauer`. Der **Pflichtteil** `[lst, est + Dauer)` ist der Zeitraum, in dem die Aktivität auf jeden Fall läuft.
Die Suche verzweigt auf der Reihenfolge von Paaren, die nicht zugleich laufen können, und sonst auf dem Start; nach jeder Entscheidung schieben die Stufen die Fenster, bis sich nichts mehr ändert (Fixpunkt), oder melden einen **Fehlschlag**.

"""
        + _md_table(
            ["Stufe", "Was sie sieht", "Was sie nicht sieht", "Kosten je Knoten"],
            [
                ["0 Vorrang", "Vorrangkanten und beschlossene Reihenfolgen verschieben die Fenster; Ressourcen werden nur gegen schon festgelegte Starts geprüft", "dass sich Pflichtteile auf der Ressource aufsummieren", "nicht gemessen"],
                ["1 Timetabling", "Profil der Pflichtteile: ist es irgendwo größer als die Kapazität, Fehlschlag; sonst werden est und lst über Zeitpunkte hinausgeschoben, in denen Profil plus Bedarf die Kapazität übersteigt", "Überlast, die nur aus Energie entsteht, wenn keine Aktivität einen Pflichtteil hat", "nicht gemessen"],
                ["2 Energie", "dazu je Fenster [a, b): Passt die Energie (Dauer mal Bedarf) der ganz hineinpassenden Aktivitäten nicht in Kapazität mal (b − a), Fehlschlag", "verschiebt keine Fenster (nur Fehlschlag); kein Edge-Finding", "nicht gemessen"],
            ],
        )
        + "\n\nTimetabling und Energieprüfung sind hier **eigene einfache Fassungen, nach Gedächtnis, nicht gegen die Literatur geprüft**; die Korrektheit stützt sich auf Tests gegen die Aufzählung aller Pläne und gegen OR-Tools CP-SAT."
    )

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    sidebar_presets()  # Schnellstart oben, das aktive Preset ist hervorgehoben
    st.header("⚙️ Einstellungen")
    st.markdown("**Zufallsinstanz (Experimente 2 und 4)**")
    n = st.slider("Aktivitäten n", *bounds("n_slider"), key="n_slider", help="Wie viele Aktivitäten die Zufallsinstanz hat (Dauern 1 bis 9).")
    res = st.slider("Ressourcen", *bounds("res_slider"), key="res_slider", help="Zahl der erneuerbaren Ressourcen; jede Aktivität braucht an mindestens einer von ihnen Bedarf.")
    cap = st.slider("Kapazität je Ressource", *bounds("cap_slider"), key="cap_slider", help="Kapazität jeder Ressource; der Bedarf einer Aktivität liegt zwischen 1 und der Kapazität.")
    seed = st.number_input("Zufalls-Seed der Instanz", *bounds("seed_input"), key="seed_input", step=1)
    st.button("🎲 Neue Instanz generieren", width="stretch", on_click=randomize_seed)
    st.markdown("**Live-Läufe**")
    budget = st.slider("Knotenbudget", *bounds("budget_slider"), key="budget_slider", step=1000, help="Nach so vielen Suchknoten bricht ein Lauf ab; sein Ergebnis ist dann nur eine Schranke.")

# --- Experiment 1: Pflichtteile von Hand ---------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Pflichtteile von Hand")
st.markdown(
    "Zwei Handbeispiele mit **Kapazität 2** und einer Ressource. Eine Aktivität steht als **Dauer / Bedarf**:\n\n"
    + _md_table(
        ["Aktivität", "H1", "H2"],
        [[nm, f"{HANDBEISPIELE['H1'].d[i]} / {HANDBEISPIELE['H1'].bedarf[0][i]}", f"{HANDBEISPIELE['H2'].d[i]} / {HANDBEISPIELE['H2'].bedarf[0][i]}"] for i, nm in enumerate(HANDBEISPIELE["H1"].namen)],
    )
    + "\n\nVorrang in H1: U vor R, R vor T. Vorrang in H2: U vor R. **Frage:** Gibt es einen Plan mit Makespan höchstens H?"
)
a1, a2, a3 = st.columns(3)
for sp, bsp in zip((a1, a2), C.HB_BEISPIELE):
    az = _aufzaehlung(bsp)
    sp.metric(f"{C.HB_NAMEN[bsp]}: optimaler Makespan", _zahl(az.optimum), delta=f"{_zahl(az.am_optimum)} Pläne mit Makespan höchstens {az.optimum}; {_zahl(az.unter_optimum)} mit weniger", delta_color="off")
a3.metric("Verfahren der Aufzählung", "alle Startzeitvektoren", delta="Gegenentwurf ohne Propagation", delta_color="off")

st.subheader("🔬 Experiment 1: Schritt für Schritt durch die Schlüsse")
st.caption("Die Wurzel-Propagation bei Horizont H, jeder Schluss einzeln mit Begründung. Wählen Sie Beispiel, Horizont und Stufe; der Schieberegler geht durch die Schritte.")
c1, c2, c3 = st.columns(3)
hb_bsp = c1.radio("Beispiel", C.HB_BEISPIELE, key="hb_bsp_radio", horizontal=True, format_func=lambda b: C.HB_NAMEN[b])
hb_h = c2.radio("Horizont H", C.HB_HORIZONTS, key="hb_h_radio", horizontal=True, format_func=lambda h: f"H = {h}")
hb_stufe = c3.radio("Stufe", C.STAGES, key="hb_stufe_radio", horizontal=True, format_func=lambda s: C.STAGE_SHORT[s])
inst_hb = HANDBEISPIELE[C.HB_NAMEN[hb_bsp]]
fix = _fixpunkt(int(hb_bsp), int(hb_h), int(hb_stufe))
events = fix.protokoll.ereignisse
if st.session_state.get("hb_sig") != (hb_bsp, hb_h, hb_stufe):
    st.session_state["hb_sig"] = (hb_bsp, hb_h, hb_stufe)
    st.session_state["hb_schritt"] = 1
st.session_state["hb_schritt"] = max(1, min(int(st.session_state.get("hb_schritt", 1)), len(events)))


def _schritt(delta):
    st.session_state["hb_schritt"] = max(1, min(len(events), st.session_state["hb_schritt"] + delta))


def _zum_ende():
    st.session_state["hb_schritt"] = len(events)


b1, b2, b3 = st.columns(3)
b1.button("← Zurück", on_click=_schritt, args=(-1,), width="stretch", key="hb_zurueck")
b2.button("Weiter →", on_click=_schritt, args=(1,), width="stretch", key="hb_weiter")
b3.button("Zum Ende", on_click=_zum_ende, width="stretch", key="hb_ende")
schritt = st.slider("Schritt", 1, len(events), key="hb_schritt") if len(events) > 1 else 1
ev_now = events[schritt - 1]
st.markdown(f"**Schritt {schritt} von {len(events)}:** {ev_now.text}")
st.plotly_chart(build_fenster_profil(inst_hb, ev_now.est, ev_now.lst, int(hb_h)), width="stretch", key="hb_chart")
st.caption("Oben hell: das Fenster einer Aktivität (frühester Start bis spätestes Ende), dunkel: der **Pflichtteil**. Unten: das Profil der Pflichtteile als Treppe gegen die Kapazität (rote Linie). Rote gepunktete Linie: Horizont H. Die Zustände sind die Fenster nach dem jeweiligen Schritt.")
if fix.protokoll.abgeschnitten:
    st.warning(f"Die Spur ist nach {A.MAX_EREIGNISSE} Ereignissen abgeschnitten.")
vor = _fixpunkt(int(hb_bsp), int(hb_h), 0)
kind, text = ev.verdict_pflichtteile(fix, C.HB_NAMEN[hb_bsp], int(hb_h), int(hb_stufe), A.fensterbreite(vor.est, vor.lst) if vor.ok else A.fensterbreite(fix.est, fix.lst))
getattr(st, kind)(text)
with st.expander("Alle Schritte als Liste"):
    st.markdown(_md_table(["Nr.", "Art", "Begründung"], [[i + 1, e.art, e.text.replace("|", "/")] for i, e in enumerate(events)]))

st.markdown("---")

# --- Experiment 2: Stufen im Vergleich -----------------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment 2: Die Stufen im Vergleich")
st.caption(
    f"Vorgerechnet, nicht live: Knoten bis zum bewiesenen Optimum auf festen Zufallsinstanzen (Dauern 1 bis 9, Zufalls-Seeds {C.SWEEP_SEEDS[0]} bis {C.SWEEP_SEEDS[-1]}, Messskript `{C.MEASURE_SCRIPT}`, Datei `{C.SWEEPS_FILE}`). "
    "Eine Stufe bricht am Knotenbudget ab, wenn sie dort noch nicht fertig ist: Dann ist die Zahl eine untere Schranke. Das Optimum ist mit OR-Tools CP-SAT geprüft, wo CP-SAT es bewiesen hat."
)
zelle = st.radio("Zelle", range(len(C.CELL_KEYS)), key="zelle_radio", horizontal=True,
                 format_func=lambda i: f"{C.CELL_KEYS[i]}: n = {C.ZELLEN[C.CELL_KEYS[i]][0]}, {C.ZELLEN[C.CELL_KEYS[i]][1]} Ressource" + ("n" if C.ZELLEN[C.CELL_KEYS[i]][1] > 1 else "") + f", Kapazität {C.ZELLEN[C.CELL_KEYS[i]][2]}")
zkey = C.CELL_KEYS[zelle]
reihe = REIHEN[zkey]
rows = ev.statistik(reihe)
st.markdown(f"**Zelle {zkey}: {len(reihe['instanzen'])} Instanzen, Budget {_zahl(reihe['budget'])}**")
st.plotly_chart(build_verteilung({r["stufe"]: ev.knoten(reihe, r["stufe"]) for r in rows}, {r["stufe"]: r["abbrueche"] for r in rows}, reihe["budget"] + 1), width="stretch", key=f"verteilung_{zkey}")
st.markdown(_md_table(["Stufe", "bewiesen", "Median", "90-%-Wert", "Maximum", "Abbrüche", "Lücke zum Optimum (Median / Maximum)"],
                      [[C.STAGE_SHORT[r["stufe"]], f"{r['bewiesen']} von {r['n']}", _zahl(r["median"]), _zahl(r["p90"]), _zahl(r["max"]), r["abbrueche"],
                        "–" if r["luecke_median"] is None else f"{_zahl(r['luecke_median'])} / {_zahl(r['luecke_max'])}"] for r in rows]))
kind, text = ev.verdict_stufen(rows, f"Zelle {zkey}")
getattr(st, kind)(text)
cp = ev.cpsat_stat(reihe)
st.caption(f"OR-Tools CP-SAT (Gegenprobe, vorgerechnet): bewiesenes Optimum in {cp['bewiesen']} von {cp['n']} Instanzen, Konflikte im Median {_zahl(cp['median'])} (Maximum {_zahl(cp['max'])}). "
           "Knoten und Konflikte sind verschiedene Einheiten, kein Verfahrensvergleich.")

if zkey in ("A", "B"):
    st.markdown(f"**Messreihe auf Knopfdruck** (Zelle {zkey}, dieselben 10 Instanzen, Knotenbudget {_zahl(C.LIVE_REIHE_BUDGET)} statt {_zahl(reihe['budget'])})")
    if st.button(f"Reihe rechnen: Zelle {zkey}", key="reihe_knopf"):
        st.session_state["reihe_live"] = zkey
        L.reihe(zkey, C.LIVE_REIHE_BUDGET)
    if st.session_state.get("reihe_live") == zkey:
        lr = L.reihe_aus_speicher(zkey, C.LIVE_REIHE_BUDGET)
        lrows = ev.statistik(lr)
        st.markdown(_md_table(["Stufe", "bewiesen", "Median", "90-%-Wert", "Maximum", "Abbrüche"], [[C.STAGE_SHORT[r["stufe"]], f"{r['bewiesen']} von {r['n']}", _zahl(r["median"]), _zahl(r["p90"]), _zahl(r["max"]), r["abbrueche"]] for r in lrows]))
        kind, text = ev.verdict_stufen(lrows, f"Zelle {zkey}, live mit Budget {_zahl(C.LIVE_REIHE_BUDGET)}")
        getattr(st, kind)(text)
else:
    st.info("Zelle C ist nur vorgerechnet: eine Reihe dieser Größe sprengt das Zeitbudget einer Live-Messung.")

st.markdown("**Eine Einzelinstanz live rechnen** (Aktivitäten, Ressourcen, Kapazität, Zufalls-Seed und Knotenbudget aus der Seitenleiste)")
live_key = (int(seed), int(n), int(res), int(cap), int(budget))
if st.button(f"Rechnen: n = {n}, {res} Ressource(n), Kapazität {cap}, Zufalls-Seed {seed}, Budget {_zahl(budget)}", key="live_knopf"):
    st.session_state["live_key"] = live_key
    L.stufen_einzel(live_key)
if st.session_state.get("live_key") == live_key:
    erg = L.einzel_aus_speicher(live_key)
    st.markdown(_md_table(["Stufe", "Knoten", "Fehlschläge", "Timetabling-Schlüsse", "bester Makespan", "bewiesen"],
                          [[C.STAGE_NAMES[s], _zahl(e.z.knoten), _zahl(e.z.fehlschlaege), _zahl(e.z.tt_schluesse), e.optimum, "ja" if e.bewiesen else "nein (Abbruch)"] for s, e in erg.items()]))
    kind, text = ev.verdict_einzel(erg, int(budget))
    getattr(st, kind)(text)
    beste = min((e for e in erg.values() if e.plan is not None), key=lambda e: (e.optimum, not e.bewiesen), default=None)
    if beste is not None:
        inst_live = make_instanz(*(live_key[1:4]), live_key[0])
        ok, grund = pruefe_plan(inst_live, beste.plan)
        st.plotly_chart(build_gantt(inst_live, beste.plan), width="stretch", key="live_gantt")
        st.caption(f"Der beste gefundene Plan (Makespan {makespan(inst_live, beste.plan)}), vom unabhängigen Prüfer " + ("als zulässig bestätigt." if ok else f"**abgelehnt: {grund}**"))
else:
    st.info("Noch nichts gerechnet für diese Einstellungen: der Knopf startet den Lauf.")

st.markdown("---")

# --- Experiment 3: Energie-Überlastprüfung ----------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment 3: Was die Energie-Überlastprüfung bringt")
h2 = HANDBEISPIELE["H2"]
f_tt, f_en = _fixpunkt(2, 7, 1), _fixpunkt(2, 7, 2)
st.markdown(
    "**Handbeispiel H2 bei Horizont 7:** Keine Aktivität hat einen Pflichtteil, Timetabling (Stufe 1) schließt nichts. Die **Energie** im Fenster [0, 7) ist 4·1 + 4·1 + 1·1 + 2·1 + 2·2 = 15, die Kapazität mal Länge ist 2 · 7 = 14. "
    f"Stufe 1: {'kein Fehlschlag' if f_tt.ok else 'Fehlschlag'}; Stufe 2: {'kein Fehlschlag' if f_en.ok else 'Fehlschlag (Überlast)'}."
)
st.caption("Die Energieprüfung sieht also, was das Profil nicht sieht. Ob solche Fälle im Suchbaum den Ausschlag geben, zeigt die Messreihe:")
rows_e = {k: ev.statistik(REIHEN[k]) for k in C.CELL_KEYS}
for k in C.CELL_KEYS:
    kind, text = ev.verdict_energie(ev.paar_ersparnis(REIHEN[k]), rows_e[k], f"Zelle {k}")
    getattr(st, kind)(text)
st.markdown(_md_table(["Zelle", "Stufe 1: bewiesen", "Stufe 2: bewiesen", "Median Knoten Stufe 1", "Median Knoten Stufe 2", "beide beweisen", "Median der Ersparnis"],
                      [[k, rows_e[k][1]["bewiesen"], rows_e[k][2]["bewiesen"], _zahl(rows_e[k][1]["median"]), _zahl(rows_e[k][2]["median"]), ev.paar_ersparnis(REIHEN[k])["beide"],
                        "–" if ev.paar_ersparnis(REIHEN[k])["median"] is None else f"{round(100 * ev.paar_ersparnis(REIHEN[k])['median'])} %"] for k in C.CELL_KEYS]))
st.caption("Nur Fehlschlag-Prüfung, einfache Fassung: **kein Edge-Finding im Sinne der Literatur.** Kumulatives Edge-Finding ist nicht gebaut und nicht gemessen; die Aussage gilt nicht für energetisches Schließen, das auch Fenster verschiebt.")

st.markdown("---")

# --- Experiment 4: Größe der SAT-Kodierung ------------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment 4: Größe der zeitindizierten SAT-Kodierung")
st.caption("Dieselbe Aufgabe als SAT: eine Variable je (Aktivität, Startzeitpunkt), Kapazität je Zeitpunkt als Totalizer. Vorgerechnet (Median über 10 Instanzen je Zelle, H = beste serielle Konstruktion) und live für die Instanz der Seitenleiste.")
gr_rows = ev.groesse_statistik(DATA["groesse"])
st.markdown(_md_table(["Zelle", "n", "Ressourcen × Kapazität", "H (Median)", "Variablen (Median)", "Klauseln (Median)"],
                      [[z["zelle"], z["n"], f"{z['ressourcen']} × {z['kap']}", _zahl(z["H"]), _zahl(z["variablen"]), _zahl(z["klauseln"])] for z in gr_rows]))
kind, text = ev.verdict_groesse(gr_rows)
getattr(st, kind)(text)

inst_sat = make_instanz(int(n), int(res), int(cap), int(seed))
konstr = beste_konstruktion(inst_sat)
st.markdown(f"**Live: Instanz n = {n}, {res} Ressource(n), Kapazität {cap}, Zufalls-Seed {seed}**")
kurve = _groessenkurve(int(seed), int(res), int(cap))
st.plotly_chart(build_groesse({f"Zufalls-Seed {seed}, {res} Ressource(n), Kapazität {cap}, H = beste Konstruktion": kurve}), width="stretch", key="groesse_chart")
sat_h = st.radio("Horizont H des SAT-Laufs", C.SAT_H_WAHL, key="sat_h_radio", horizontal=True, format_func=lambda k: C.SAT_H_NAMEN[k])
sat_budget = st.slider("Konfliktbudget des SAT-Laufs", *bounds("sat_budget_slider"), key="sat_budget_slider", step=500, help="Nach so vielen Konflikten bricht das Kern-CDCL ab.")
if sat_h == 0:
    H = konstr[0]
else:
    with st.spinner("Bestimmt das Optimum (Stufe 1) für den Horizont …"):
        opt_run = _optimum_live(int(seed), int(n), int(res), int(cap), int(budget))
    H = opt_run.optimum - (1 if sat_h == 2 else 0)
    if not opt_run.bewiesen:
        st.warning(f"Das Optimum ist nach {_zahl(budget)} Knoten nicht bewiesen; H bezieht sich auf den besten gefundenen Makespan {opt_run.optimum} (obere Schranke).")
g = S.groesse(inst_sat, H)
if g is None:
    st.info(f"Bei H = {H} macht schon der Vorrang ein Fenster leer: es gibt keine Kodierung und keinen Plan.")
else:
    m1, m2, m3 = st.columns(3)
    m1.metric("Horizont H", _zahl(H))
    m2.metric("Variablen", _zahl(g[0]))
    m3.metric("Klauseln", _zahl(g[1]))
    st.caption("Exakt gezählt (ohne die Klauseln zu bauen; ein Test vergleicht die Zählung mit der gebauten Kodierung).")
    if st.button(f"Kern-CDCL rechnen (H = {H}, Budget {_zahl(sat_budget)} Konflikte)", key="sat_knopf"):
        st.session_state["sat_key"] = (int(seed), int(n), int(res), int(cap), int(H), int(sat_budget))
        with st.status("Rechnet das Kern-CDCL: ein einzelner Lauf bis zur Antwort oder bis zum Konfliktbudget, ohne Zwischenstand …", expanded=True) as sat_status:
            _sat_live(*st.session_state["sat_key"])
            sat_status.update(label="Kern-CDCL: fertig", state="complete", expanded=False)
    if st.session_state.get("sat_key") == (int(seed), int(n), int(res), int(cap), int(H), int(sat_budget)):
        sr = _sat_live(*st.session_state["sat_key"])
        mini = _mini_entscheidung(int(seed), int(n), int(res), int(cap), int(H), int(budget))
        kind, text = ev.verdict_sat_live(sr, int(H), mini, int(sat_budget))
        getattr(st, kind)(text)
        if sr.plan is not None:
            st.plotly_chart(build_gantt(inst_sat, sr.plan), width="stretch", key="sat_gantt")
            st.caption("Das Modell des CDCL, in einen Plan zurückübersetzt und vom unabhängigen Prüfer bestätigt.")

st.markdown("**Vorgerechnet: Konflikte des Kern-CDCL gegen CP-SAT** (je 6 feste Instanzen, Konfliktbudget " + _zahl(C.SAT_BUDGET) + ", Messskript `" + C.MEASURE_SCRIPT + "`)")
sat_stat = {k: ev.sat_statistik(v) for k, v in DATA["sat"].items()}
st.plotly_chart(build_konflikte([(k.replace("_opt1", ", H = Optimum − 1").replace("_opt", ", H = Optimum"), s["sat_median"], s["cpsat_median"]) for k, s in sat_stat.items()]), width="stretch", key="konflikte_chart")
kind, text = ev.verdict_sat(sat_stat)
getattr(st, kind)(text)

st.markdown("---")

# --- Grenzen -------------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Eigene einfache Fassungen** von Timetabling und Energieprüfung | Die Aussagen gelten für diese Fassungen, nicht für Edge-Finding oder energetisches Schließen der Literatur; kumulatives Edge-Finding ist nicht gebaut. | Propagatoren in CP-SAT und anderen CP-Lösern |
| **Eine Verzweigungsregel, eine Startschranke** | Die Knotenzahlen gelten für diese Regel (Paar mit kleinster Spielraumsumme, sonst Start) und die beste von fünf seriellen Konstruktionen als Start. | – |
| **Kleine Instanzen** (n bis 20, Dauern 1 bis 9, 10 Instanzen je Zelle) | Mediane mit Abbrüchen am Budget sind untere Schranken; Knoten sind keine Rechenzeit (Kosten je Knoten nicht gemessen); keine Benchmark-Instanzen. | Prioritätsregeln und CP-SAT als Maßstab (rcpsp-demo) |
| **Zeitindizierte Kodierung** | Sie wächst mit Fensterbreite, Kapazität und n; die Konflikte von Kern-CDCL und CP-SAT sind verschiedene Einheiten, die Ursache des Unterschieds ist nicht getrennt. | Lazy Clause Generation, zeitkontinuierliche Kodierungen |
"""
)

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Lesehilfe.** Gegeben sind Aktivitäten mit ganzzahliger Dauer $d_i \ge 1$ und Bedarf $r_i$ an einer Ressource der Kapazität $C$ sowie Vorrangkanten. Gesucht ist ein Plan (Startzeiten $s_i$) mit kleinstem Makespan, der die Vorrangkanten und in jedem Zeitpunkt die Kapazität einhält.

| Symbol | Bedeutung |
|---|---|
| $d_i,\ r_i$ | Dauer und Bedarf der Aktivität $i$ |
| $C$ | Kapazität der Ressource |
| $\mathrm{est}_i,\ \mathrm{lst}_i$ | frühester und spätester Start (Fenster) |
| $H$ | Horizont: Makespan höchstens $H$ |

**Kumulativ-Bedingung.** In jedem Zeitpunkt $t$ gilt

$$\sum_{i:\ s_i \le t < s_i + d_i} r_i \le C.$$

**Pflichtteil.** Der Zeitraum, in dem $i$ auf jeden Fall läuft:

$$[\mathrm{lst}_i,\ \mathrm{est}_i + d_i), \quad \text{nichtleer genau dann, wenn } \mathrm{lst}_i < \mathrm{est}_i + d_i.$$

**Profil und Timetabling.** Das Profil der Pflichtteile aller Aktivitäten außer $i$ ist

$$P_{-i}(t) = \sum_{j \ne i:\ \mathrm{lst}_j \le t < \mathrm{est}_j + d_j} r_j .$$

Ist $P_{-i}(t) + r_i > C$ für einen Zeitpunkt $t$, darf $i$ dort nicht laufen: Startzeitpunkte $s$ mit $s \le t < s + d_i$ sind ausgeschlossen, und $\mathrm{est}_i$ und $\mathrm{lst}_i$ rücken an den nächsten erlaubten Startzeitpunkt. Ist $P(t) > C$ schon ohne weitere Aktivität, gibt es keinen Plan.

**Energie-Überlastprüfung (Stufe 2, nur Fehlschlag).** Für jedes Fenster $[a, b)$ gilt: Passt die Energie der Aktivitäten, die mit ihrem ganzen Fenster hineinpassen, nicht in die Kapazität, gibt es keinen Plan:

$$\sum_{i:\ \mathrm{est}_i \ge a,\ \mathrm{lst}_i + d_i \le b} r_i\, d_i > C\,(b - a) \;\Rightarrow\; \text{Fehlschlag}.$$

**Zeitindizierte SAT-Kodierung.** Variable $x_{i,t}$ heißt „$i$ startet in $t$“; je Aktivität genau ein Start, Vorrang $(i,j)$ als Klauseln $x_{i,t} \to \bigvee_{t' \ge t + d_i} x_{j,t'}$, und je Zeitpunkt $t$

$$\sum_{i} \sum_{s = t - d_i + 1}^{t} r_i\, x_{i,s} \le C$$

als Totalizer (Kardinalitätskodierung; ein Bedarf $r_i$ zählt als $r_i$-fach wiederholtes Literal).

**Literatur.** Timetabling und Energieprüfung sind eigene Fassungen nach Gedächtnis, **nicht gegen die Literatur geprüft**; zu kumulativer Propagation ist keine Primärquelle gelesen. Die Korrektheit stützt sich auf Tests gegen die Aufzählung aller Pläne und gegen OR-Tools CP-SAT.
        """
    )

sync_query_params({key: st.session_state[key] for key in SETTING_SPECS if key in st.session_state})

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zur Reihe: [SAT und CP: Konfliktlernen bis Wahl](https://sebastianhanisch.net/konzepte-sat-constraint-programming.html)."
)
