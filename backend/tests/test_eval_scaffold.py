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
    from eval.cli import (
        COMMANDS, build_parser,
        cmd_generate, cmd_adapt_prompts, cmd_review_queue, cmd_promote, cmd_run,
    )
    assert COMMANDS == ("generate", "adapt-prompts", "review-queue", "promote", "run")
    parser = build_parser()

    # All five subcommands are implemented (T09/T17/T18/T14-T15) — verify registration
    # only; invoking them needs live FPT/DB/MLflow, out of scope for this offline test.
    assert parser.parse_args(["generate", "--all"]).func is cmd_generate
    assert parser.parse_args(["adapt-prompts"]).func is cmd_adapt_prompts
    assert parser.parse_args(["review-queue", "--dataset", "d1"]).func is cmd_review_queue
    assert parser.parse_args(["promote", "--dataset", "d1"]).func is cmd_promote
    assert parser.parse_args(["run", "--dataset", "d1"]).func is cmd_run


def test_requirements_eval_pins():
    lines = [ln.strip() for ln in
             (BACKEND_ROOT / "requirements-eval.txt").read_text().splitlines() if ln.strip()]
    assert "-r requirements.txt" in lines
    assert "ragas==0.4.3" in lines
    assert "mlflow==3.14.0" in lines


def test_importorskip_pattern():
    ragas = pytest.importorskip("ragas")
    assert hasattr(ragas, "__version__")
