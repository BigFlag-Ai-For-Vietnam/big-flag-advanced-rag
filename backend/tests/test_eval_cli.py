"""Test CLI 2 lệnh cấp cao (rev 2, FR-9) — offline, chỉ parse, không thực thi handler."""
import pytest

from eval.cli import build_parser, cmd_generate, cmd_judge


def test_two_command_split():
    parser = build_parser()

    args = parser.parse_args(["dataset", "generate", "--all", "--dataset", "d1"])
    assert args.command == "dataset"
    assert args.dataset_command == "generate"
    assert args.func is cmd_generate

    args3 = parser.parse_args(["judge", "--dataset", "d1"])
    assert args3.command == "judge"
    assert args3.func is cmd_judge
    assert args3.technique == "trivial"  # mặc định (FR-17)

    # --technique parse-only: lỗi "unknown technique" là runtime (resolve()), không phải argparse.
    args4 = parser.parse_args(["judge", "--dataset", "d1", "--technique", "agentic"])
    assert args4.technique == "agentic"

    # Lệnh phẳng cũ bị từ chối như lệnh không hợp lệ (unknown command).
    with pytest.raises(SystemExit):
        parser.parse_args(["generate", "--all"])
    with pytest.raises(SystemExit):
        parser.parse_args(["run", "--dataset", "d1"])
