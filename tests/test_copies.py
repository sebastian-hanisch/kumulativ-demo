"""Die kopierten Kern-Module sind unverändert gegenüber der Kern-Version, die im Modulkopf steht (Hash der Datei ohne Kopfzeilen und mit rückübersetzten Importen).

`kum_rng.py`, `kum_kodierung.py` und `kum_cdcl.py` sind Kopien von `rng.py`, `kodierung.py` und `cdcl.py` aus sat-cp-planung/kern/ ohne Abweichung."""

import hashlib
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MODULE = ["rng", "kodierung", "cdcl"]


def _kern_text(modul: str) -> tuple[str, str]:
    """(Kern-Version aus dem Kopf, Text im Zustand des Kerns)."""
    text = (ROOT / f"kum_{modul}.py").read_text(encoding="utf-8").replace("\r\n", "\n")
    version = re.match(r"# Herkunft: Kopie von sat-cp-planung/kern/\w+\.py \(Kern-Version ([0-9a-f]{16})", text).group(1)
    zeilen = text.split("\n")
    i = 0
    while zeilen[i].startswith("#"):
        i += 1
    return version, "\n".join(zeilen[i:]).replace("from kum_rng import", "from rng import")


@pytest.mark.parametrize("modul", MODULE)
def test_kopie_gleicht_der_kern_version(modul):
    version, text = _kern_text(modul)
    assert hashlib.sha256(text.encode("utf-8")).hexdigest()[:16] == version


def test_kopien_importieren_nichts_aus_dem_kern_oder_anderen_demos():
    erlaubt = {"heapq", "itertools", "dataclasses", "math", "typing", "kum_rng"}
    for modul in MODULE:
        for zeile in (ROOT / f"kum_{modul}.py").read_text(encoding="utf-8").splitlines():
            if zeile.startswith(("import ", "from ")):
                assert zeile.split()[1] in erlaubt, (modul, zeile)


def test_kein_modul_der_demo_importiert_aus_dem_kern_oder_anderen_demos():
    eigene = {p.stem for p in ROOT.glob("kum_*.py")} | {"app"}
    for pfad in ROOT.glob("*.py"):
        for zeile in pfad.read_text(encoding="utf-8").splitlines():
            m = re.match(r"(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)", zeile)
            if m and m.group(1) in {"rng", "cdcl", "kodierung", "instanzen", "dpll", "alldifferent", "dje"}:
                pytest.fail(f"{pfad.name}: {zeile}")
            if m and m.group(1).startswith(("ald_", "dje_", "wlt_")):
                pytest.fail(f"{pfad.name}: {zeile}")
    assert "kum_cdcl" in eigene
