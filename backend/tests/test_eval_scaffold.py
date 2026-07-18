"""Test khung sườn CLI eval (T01) — cô lập dep nặng, không đụng app.main."""
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_app_main_does_not_import_eval():
    code = (
        "import sys; import app.main; "
        "bad = [m for m in sys.modules if m == 'eval' or m.startswith('eval.')]; "
        "assert not bad, f'app.main imported eval package: {bad}'"
    )
    proc = subprocess.run([sys.executable, "-c", code], cwd=BACKEND_ROOT,
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


def test_cli_registers_all_subcommands():
    from eval.cli import DATASET_SUBCOMMANDS, TOP_LEVEL_COMMANDS, build_parser

    assert TOP_LEVEL_COMMANDS == ("dataset", "judge")
    assert DATASET_SUBCOMMANDS == ("generate", "adapt-prompts", "review-queue", "promote")
    build_parser()  # constructs without error, no heavy imports triggered
    # Behavior of the two-command split (dispatch + legacy-name rejection) is covered by
    # test_eval_cli.py::test_two_command_split (rev 2, FR-9).


def test_requirements_eval_pins():
    lines = [ln.strip() for ln in
             (BACKEND_ROOT / "requirements-eval.txt").read_text().splitlines() if ln.strip()]
    assert "-r requirements.txt" in lines
    assert "ragas==0.4.3" in lines
    assert "mlflow==3.14.0" in lines


def test_importorskip_pattern():
    ragas = pytest.importorskip("ragas")
    assert hasattr(ragas, "__version__")
