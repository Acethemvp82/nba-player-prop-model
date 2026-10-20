"""Safe foundation checks; no network or sportsbook credentials needed."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

def test_streamlit_entrypoint_parses():
    ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))

def test_required_dependencies_declared():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    for package in ("streamlit", "pandas", "numpy", "requests"):
        assert package in requirements

def test_no_committed_streamlit_secrets():
    assert not (ROOT / ".streamlit" / "secrets.toml").exists()

def test_model_plan_exists():
    assert (ROOT / "MODEL_PLAN.md").is_file()
