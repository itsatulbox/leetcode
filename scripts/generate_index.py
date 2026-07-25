#!/usr/bin/env python3
"""Regenerate the README's table of solved problems from the solution files.

The table is written between marker comments, so the rest of the README is left
alone. Run from anywhere:  python3 scripts/generate_index.py
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

from repo import DIFFICULTIES, REPO_ROOT, Solution, solutions

README = REPO_ROOT / "README.md"

START = "<!-- INDEX:START -->"
END = "<!-- INDEX:END -->"


def build_index(records: list[Solution]) -> str:
    counts = dict.fromkeys(DIFFICULTIES, 0)
    for r in records:
        if r["difficulty"] in counts:
            counts[r["difficulty"]] += 1

    lines = [
        "",
        "**{} problems** &nbsp;·&nbsp; {} Easy &nbsp;·&nbsp; "
        "{} Medium &nbsp;·&nbsp; {} Hard".format(
            len(records), counts["Easy"], counts["Medium"], counts["Hard"]
        ),
        "",
        "| # | Problem | Difficulty | Lang | Date | Solution |",
        "|---|---------|------------|------|------|----------|",
    ]
    for r in records:
        # A pipe in a title would split the table cell.
        title = r["title"].replace("|", "\\|")
        title = f"[{title}]({r['link']})" if r["link"] else title
        lines.append(
            f"| {r['id']} | {title} | {r['difficulty']} | {r['lang']} "
            f"| {r['date']} | [solution]({r['path']}) |"
        )
    lines.append("")
    return "\n".join(lines)


def splice(text: str, block: str) -> str:
    """Replace the content between the index markers."""
    if START not in text or END not in text:
        # Appending a fresh pair here would leave two start markers, and the
        # next run would delete everything between them.
        missing = START if START not in text else END
        sys.exit(f"README.md is missing {missing}. Nothing to write the index into.")
    return re.sub(
        re.escape(START) + r".*?" + re.escape(END),
        lambda _: f"{START}\n{block}\n{END}",
        text,
        count=1,
        flags=re.DOTALL,
    )


def staged_or_committed() -> set[str]:
    """Solution files git already knows about, staged ones included."""
    listed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "--", "*.md"],
        capture_output=True,
        text=True,
        check=True,
    )
    return {line for line in listed.stdout.splitlines() if line}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--tracked",
        action="store_true",
        help="only count solutions git knows about, not every file on disk",
    )
    args = ap.parse_args()

    everything = solutions(staged_or_committed() if args.tracked else None)
    records = [r for r in everything if not r["draft"]]
    drafts = [r for r in everything if r["draft"]]

    text = README.read_text(encoding="utf-8")
    new = splice(text, build_index(records))

    if new != text:
        README.write_text(new, encoding="utf-8")
        print(f"Updated README.md: {len(records)} problems.")
    else:
        print(f"README.md already up to date ({len(records)} problems).")

    for r in drafts:
        print(f"  skipped (no code yet): {r['path']}")


if __name__ == "__main__":
    main()
