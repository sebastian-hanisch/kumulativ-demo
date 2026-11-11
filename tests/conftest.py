"""Gemeinsame Fixtures: die Mini-Instanzen, an denen jede Einheit von Hand geprüft wird (DEMO-PLAYBOOK §1b)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from kum_scenario import H1, H2  # noqa: E402


@pytest.fixture
def h1():
    """Handbeispiel H1 (Kapazität 2): P(4, 1), Q(4, 1), U(1, 1), R(2, 1), T(1, 1), Vorrang U → R → T; Optimum 7, 24 Pläne mit Makespan ≤ 7."""
    return H1


@pytest.fixture
def h2():
    """Handbeispiel H2 (Kapazität 2): wie H1, aber T(2, 2) und nur Vorrang U → R; Optimum 8, 12 Pläne mit Makespan ≤ 8."""
    return H2
