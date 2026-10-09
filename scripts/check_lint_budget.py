"""Reject new lint debt by file and rule while retaining a visible legacy budget."""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "scripts" / "lint-baseline.json"


def collect_findings(findings: list[dict[str, object]]) -> Counter[tuple[str, str]]:
    """Count findings independently of changing line numbers."""
    counts: Counter[tuple[str, str]] = Counter()
    for finding in findings:
        filename = Path(str(finding["filename"])).resolve().relative_to(ROOT).as_posix()
        counts[filename, str(finding["code"])] += 1
    return counts


def main() -> int:
    """Fail if any file/rule exceeds its recorded allowance."""
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "src/flaxon", "--output-format", "json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        print(result.stderr, file=sys.stderr)
        return result.returncode
    findings = collect_findings(json.loads(result.stdout))
    baseline = json.loads(BASELINE.read_text())
    allowed = {(item["file"], item["rule"]): item["count"] for item in baseline["findings"]}
    increased = {key: count for key, count in findings.items() if count > allowed.get(key, 0)}
    print(f"Ruff: {sum(findings.values())} legacy findings; {len(increased)} file/rule increases.")
    for (filename, rule), count in sorted(increased.items()):
        print(f"{filename}: {rule}: {count} findings (budget {allowed.get((filename, rule), 0)})")
    if increased:
        print("Fix the new findings. Do not refresh the baseline to absorb new debt.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
