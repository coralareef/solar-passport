from __future__ import annotations

from pathlib import Path

from validation.synthetic_profiles import build_validation_pack as build_profiles
from validation.run_finance_reconciliation import write_report as write_finance_report


def build(output: str | Path = "validation/generated") -> list[Path]:
    root = Path(output)
    files = []
    files.extend(build_profiles(root / "profiles"))
    files.extend(write_finance_report(root / "finance"))
    return files


if __name__ == "__main__":
    for path in build():
        print(path)
