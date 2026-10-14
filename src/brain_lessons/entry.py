"""Absolute hook entry, invoked with Python -I to exclude project imports."""
from pathlib import Path
import sys

# This path belongs to the installed distribution, never the calling project.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from brain_lessons.cli import main

raise SystemExit(main())
