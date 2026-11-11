"""End-to-end Smoke-Test via Streamlits offiziellem AppTest-Framework: lädt app.py mit den Standardeinstellungen, klickt jeden Preset-Button, jeden Knopf, fährt jeden Slider an seine Grenzen
und prüft, dass kein Python-Fehler auftritt - insbesondere `StreamlitDuplicateElementId` (mehrere st.plotly_chart-Aufrufe ohne eindeutiges key=) und `StreamlitAPIException` bei Slidern mit berechneten Grenzen."""

import os

from streamlit.testing.v1 import AppTest

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
TIMEOUT = int(os.environ.get("APPTEST_TIMEOUT", "300"))   # unter Last (parallele Läufe) reichen 180 s nicht immer; Umgebungsvariable zum Anpassen
AUTOPLAY_MARKER = "▶"                                # Auto-Play-Buttons (Animation mit sleep) im Smoke-Test auslassen
LANGE_KNOEPFE = ("Kern-CDCL rechnen", "Reihe rechnen")    # Live-Läufe über viele Instanzen: eigene Tests unten


def _fresh_app() -> AppTest:
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    return at


def test_app_loads_without_exception():
    _fresh_app()


def test_every_button_click_does_not_raise():
    labels = [b.label for b in _fresh_app().button]
    assert labels, "keine Buttons gefunden"
    for index, label in enumerate(labels):
        if AUTOPLAY_MARKER in label or label.startswith(LANGE_KNOEPFE):
            continue
        at = _fresh_app()
        at.button[index].click().run(timeout=TIMEOUT)
        assert not at.exception, (label, [str(e) for e in at.exception])


def test_every_slider_at_its_min_and_max_does_not_raise():
    labels = [s.label for s in _fresh_app().slider]
    assert labels, "keine Slider gefunden"
    for index, label in enumerate(labels):
        for edge in ("min", "max"):
            at = _fresh_app()
            slider = at.slider[index]
            value = slider.min if edge == "min" else slider.max
            if isinstance(slider.value, int):
                value = int(value)
            slider.set_value(value).run(timeout=TIMEOUT)
            assert not at.exception, (label, edge, [str(e) for e in at.exception])


def test_handbook_examples_horizons_and_stages_do_not_raise():
    """Alle 18 Kombinationen aus Beispiel (H1, H2), Horizont (6, 7, 8) und Stufe (0, 1, 2), jeweils bis zum letzten Schritt und zurück."""
    for bsp in (1, 2):
        for h in (6, 7, 8):
            for stufe in (0, 1, 2):
                at = _fresh_app()
                at.radio(key="hb_bsp_radio").set_value(bsp).run(timeout=TIMEOUT)
                at.radio(key="hb_h_radio").set_value(h).run(timeout=TIMEOUT)
                at.radio(key="hb_stufe_radio").set_value(stufe).run(timeout=TIMEOUT)
                assert not at.exception, (bsp, h, stufe, [str(e) for e in at.exception])
                at.button(key="hb_ende").click().run(timeout=TIMEOUT)
                assert not at.exception, (bsp, h, stufe)
                letzter = at.session_state["hb_schritt"]
                if letzter >= 2:
                    at.button(key="hb_zurueck").click().run(timeout=TIMEOUT)
                    assert at.session_state["hb_schritt"] == letzter - 1
                    at.button(key="hb_weiter").click().run(timeout=TIMEOUT)
                    assert at.session_state["hb_schritt"] == letzter and not at.exception


def test_changing_example_horizon_or_stage_restarts_the_step_view():
    at = _fresh_app()
    at.button(key="hb_ende").click().run(timeout=TIMEOUT)
    assert at.session_state["hb_schritt"] > 1
    at.radio(key="hb_stufe_radio").set_value(0).run(timeout=TIMEOUT)
    assert at.session_state["hb_schritt"] == 1


def test_the_handbook_verdicts_name_the_known_conclusions():
    """Standard (H1, H = 7, Stufe 1): zwei Schlüsse, Fensterbreiten 15 → 13; H = 6: Fehlschlag an der Wurzel; H2 bei H = 7, Stufe 2: Energie 15 > 14."""
    at = _fresh_app()
    assert any("2 Timetabling-Schlüsse verkleinern die Summe der Fensterbreiten von 15 auf 13" in i.value for i in at.info)
    at.radio(key="hb_h_radio").set_value(6).run(timeout=TIMEOUT)
    assert any("Fehlschlag an der Wurzel" in s.value and "keinen Plan mit Makespan höchstens 6" in s.value for s in at.success)
    at.radio(key="hb_bsp_radio").set_value(2).run(timeout=TIMEOUT)
    at.radio(key="hb_h_radio").set_value(7).run(timeout=TIMEOUT)
    at.radio(key="hb_stufe_radio").set_value(2).run(timeout=TIMEOUT)
    assert any("15 > Kapazität 2 · Länge 7 = 14" in s.value for s in at.success)


def test_live_run_shows_a_checked_plan_for_the_default_instance():
    at = _fresh_app()
    at.button(key="live_knopf").click().run(timeout=TIMEOUT)
    assert not at.exception
    assert any("als zulässig bestätigt" in c.value for c in at.caption)
    assert any("Einzelinstanz, kein Median" in i.value for i in at.info)


def test_the_series_button_shows_a_verdict_for_cell_a():
    at = _fresh_app()
    at.radio(key="zelle_radio").set_value(0).run(timeout=TIMEOUT)
    at.button(key="reihe_knopf").click().run(timeout=TIMEOUT)
    assert not at.exception
    assert any("Zelle A, live mit Budget 5.000" in m.value for m in list(at.success) + list(at.info))


def test_cell_c_has_no_live_series_button():
    at = _fresh_app()
    at.radio(key="zelle_radio").set_value(2).run(timeout=TIMEOUT)
    assert not [b for b in at.button if b.key == "reihe_knopf"] and any("nur vorgerechnet" in i.value for i in at.info)


def test_the_sat_button_answers_like_the_mini_cp_for_each_horizon_choice():
    """n = 6 (Standard): H = beste Konstruktion, Optimum, Optimum − 1; das Kern-CDCL stimmt mit der Entscheidungsfassung des Mini-CP überein."""
    for wahl in (0, 1, 2):
        at = _fresh_app()
        at.radio(key="sat_h_radio").set_value(wahl).run(timeout=TIMEOUT)
        knopf = next(b for b in at.button if b.label.startswith("Kern-CDCL rechnen"))
        knopf.click().run(timeout=TIMEOUT)
        assert not at.exception, (wahl, [str(e) for e in at.exception])
        assert any("Das Kern-CDCL" in s.value and "dieselbe Antwort" in s.value for s in at.success), wahl
