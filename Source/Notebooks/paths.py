"""Pfade zu den Projektordnern, gemeinsam für alle Notebooks.

Die Notebooks liegen unter Source/Notebooks und importieren ihre Pfade von hier.
So ist die Ordnerstruktur nur an einer Stelle festgelegt.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRAPER = PROJECT_ROOT / 'Source' / 'scraper'
ROHDATEN = PROJECT_ROOT / 'Rohdaten'
GRAPHEN = PROJECT_ROOT / 'Graphen'
ERGEBNISSE = PROJECT_ROOT / 'Ergebnisse'
REPORT_GRAPHICS = PROJECT_ROOT / 'Report' / 'graphics'
