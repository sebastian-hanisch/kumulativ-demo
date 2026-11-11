"""Plotly-Abbildungen. Alle Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht am Diagramm hängen bleiben."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import kum_constants as C

AKTIVITAET_FARBEN = ["#4c78a8", "#f58518", "#54a24b", "#e45756", "#b279a2", "#9d755d", "#72b7b2", "#eeca3b"]


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height=360):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.25), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def pflicht_zeitpunkte(est, lst, d):
    """Die Aktivitäten mit nichtleerem Pflichtteil [lst, est + d) (lst < est + d)."""
    return [i for i in range(len(d)) if lst[i] < est[i] + d[i]]


def build_fenster_profil(inst, est, lst, H, r=0):
    """Oben: je Aktivität das Fenster [est, lct] (hell) und der Pflichtteil [lst, est + d) (dunkel). Unten: das Profil der Pflichtteile der Ressource r als Treppe gegen die Kapazitätslinie.
    Rote senkrechte Linie: Horizont H."""
    n = inst.n
    d = inst.d
    cap = inst.kap[r]
    namen = [f"{inst.name(i)} (d={d[i]}, Bedarf {inst.bedarf[r][i]})" for i in range(n)]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35], vertical_spacing=0.08)
    fig.add_trace(go.Bar(orientation="h", y=namen, x=[lst[i] + d[i] - est[i] for i in range(n)], base=[est[i] for i in range(n)],
                         marker=dict(color=C.COLOR_WINDOW, line=dict(color=C.COLOR_WINDOW_LINE, width=1)), name="Fenster (est bis lct)",
                         customdata=[[est[i], lst[i]] for i in range(n)], hovertemplate="%{y}: est %{customdata[0]}, lst %{customdata[1]}<extra></extra>"), row=1, col=1)
    pf = pflicht_zeitpunkte(est, lst, d)
    fig.add_trace(go.Bar(orientation="h", y=[namen[i] for i in pf], x=[est[i] + d[i] - lst[i] for i in pf], base=[lst[i] for i in pf], marker=dict(color=C.COLOR_MANDATORY),
                         name="Pflichtteil (lst bis est + d)", hovertemplate="%{y}: Pflichtteil von %{base} bis %{x}<extra></extra>"), row=1, col=1)
    prof = [0] * H
    for i in range(n):
        for t in range(lst[i], est[i] + d[i]):
            if 0 <= t < H:
                prof[t] += inst.bedarf[r][i]
    fig.add_trace(go.Bar(x=[t + 0.5 for t in range(H)], y=prof, width=0.96, marker=dict(color=C.COLOR_PROFILE), name="Profil der Pflichtteile",
                         hovertemplate="Zeitpunkt %{customdata}: Profil %{y}<extra></extra>", customdata=list(range(H))), row=2, col=1)
    fig.add_hline(y=cap, line=dict(color=C.COLOR_CAPACITY, width=2, dash="dash"), annotation_text=f"Kapazität {cap}", annotation_position="top left", row=2, col=1)
    fig.add_vline(x=H, line=dict(color=C.COLOR_HORIZON, width=2, dash="dot"), row="all", col=1)
    fig.update_layout(barmode="overlay", bargap=0.25)
    fig.update_xaxes(range=[0, H + 0.5], dtick=1)
    fig.update_xaxes(title_text="Zeitpunkt", row=2, col=1)
    fig.update_yaxes(autorange="reversed", categoryorder="array", categoryarray=namen, row=1, col=1)
    fig.update_yaxes(title_text="Bedarf", range=[0, max(cap, max(prof, default=0)) + 1], dtick=1, row=2, col=1)
    return _base(fig, height=max(340, 30 * n + 230))


def build_gantt(inst, plan):
    """Plan als Balkendiagramm: eine Zeile je Aktivität, die Balkenbreite ist die Dauer, im Text der Bedarf an der ersten Ressource."""
    fig = go.Figure()
    for i in range(inst.n):
        fig.add_trace(go.Bar(orientation="h", y=[inst.name(i)], x=[inst.d[i]], base=[plan[i]], marker=dict(color=AKTIVITAET_FARBEN[i % len(AKTIVITAET_FARBEN)], line=dict(color="white", width=1)),
                             text=[" ".join(f"B{inst.bedarf[r][i]}" for r in range(inst.ressourcen))], textposition="inside", insidetextanchor="middle", showlegend=False,
                             hovertemplate=f"{inst.name(i)}: Start {plan[i]}, Dauer {inst.d[i]}<extra></extra>"))
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title_text="Zeit", dtick=5)
    fig.update_yaxes(autorange="reversed", categoryorder="array", categoryarray=[inst.name(i) for i in range(inst.n)])
    return _base(fig, height=max(240, 26 * inst.n + 100))


def build_verteilung(werte_je_stufe: dict, abbrueche_je_stufe: dict, budget: int, titel_y="Knoten bis zum bewiesenen Optimum"):
    """Verteilung der Knotenzahlen je Stufe (logarithmische Achse): Kasten mit allen Punkten; rote Kreuze: Abbruch am Budget (untere Schranke)."""
    fig = go.Figure()
    for stufe, werte in werte_je_stufe.items():
        name = C.STAGE_SHORT[stufe]
        fig.add_trace(go.Box(y=werte, name=name, boxpoints="all", jitter=0.45, pointpos=0, marker=dict(color=C.COLOR_STAGE[stufe], size=6), line=dict(color=C.COLOR_STAGE[stufe]),
                             hovertemplate="%{y} Knoten<extra></extra>", showlegend=False))
        n_ab = abbrueche_je_stufe.get(stufe, 0)
        if n_ab:
            fig.add_trace(go.Scatter(x=[name], y=[budget], mode="markers+text", marker=dict(color=C.COLOR_HORIZON, symbol="x", size=11), text=[f"{n_ab} Abbruch"], textposition="top center",
                                     name="Abbruch am Budget", showlegend=False, hovertemplate=f"{n_ab} Abbrüche am Budget {budget}<extra></extra>"))
    fig.update_yaxes(type="log", title_text=titel_y)
    return _base(fig, height=380)


def build_groesse(punkte_je_reihe: dict):
    """Klauseln der Kodierung gegen n (logarithmische Achse). `punkte_je_reihe`: Name → [(n, Klauseln)]."""
    fig = go.Figure()
    stile = [("#2F6B65", "circle"), ("#c0392b", "diamond")]
    for (name, punkte), (farbe, symbol) in zip(punkte_je_reihe.items(), stile):
        fig.add_trace(go.Scatter(x=[p[0] for p in punkte], y=[p[1] for p in punkte], mode="lines+markers", name=name, line=dict(color=farbe), marker=dict(symbol=symbol, size=8),
                                 hovertemplate="n = %{x}: %{y} Klauseln<extra></extra>"))
    fig.update_xaxes(title_text="Zahl der Aktivitäten n")
    fig.update_yaxes(type="log", title_text="Klauseln (logarithmisch)")
    return _base(fig, height=340)


def build_konflikte(zeilen):
    """Konflikte (Median) von Kern-CDCL und CP-SAT je Fall, logarithmische Achse. `zeilen`: [(Name, SAT-Median, CP-SAT-Median)]; Null wird als 0,5 gezeichnet."""
    fig = go.Figure()
    namen = [z[0] for z in zeilen]
    fig.add_trace(go.Bar(x=namen, y=[max(z[1], 0.5) for z in zeilen], name="Kern-CDCL (zeitindizierte Kodierung)", marker_color="#2F6B65", customdata=[z[1] for z in zeilen],
                         hovertemplate="%{customdata} Konflikte<extra></extra>"))
    fig.add_trace(go.Bar(x=namen, y=[max(z[2], 0.5) for z in zeilen], name="CP-SAT (Intervallmodell, vorgerechnet)", marker_color="#4c78a8", customdata=[z[2] for z in zeilen],
                         hovertemplate="%{customdata} Konflikte<extra></extra>"))
    fig.update_layout(barmode="group")
    fig.update_yaxes(type="log", title_text="Konflikte im Median (logarithmisch)")
    return _base(fig, height=340)
