"""Cho phép chạy `python -m eval` từ thư mục backend/."""
import sys

from eval.cli import main

sys.exit(main())
