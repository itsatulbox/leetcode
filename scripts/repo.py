"""Reading the solution files in this repo."""

from __future__ import annotations

import re
from pathlib import Path
from string import Template
from typing import TypedDict

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = REPO_ROOT / "template.md"

DATE_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FIELD = re.compile(r'^(\w+):\s*"?(.*?)"?\s*$')
FENCE = re.compile(r"^```([A-Za-z+#]+)", re.MULTILINE)
CODE_BLOCK = re.compile(r"^```([A-Za-z+#]+)\n(.*?)^```", re.MULTILINE | re.DOTALL)

# Fence tag -> display name. Anything unlisted is ignored.
LANGS = {"cpp": "C++", "c++": "C++", "python": "Python", "py": "Python"}

DIFFICULTIES = ("Easy", "Medium", "Hard")


class Solution(TypedDict):
    id: str
    title: str
    link: str
    difficulty: str
    lang: str
    date: str
    path: str
    draft: bool


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Return the frontmatter fields of a solution file, or None if absent."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fields: dict[str, str] = {}
    for line in text[3:end].splitlines():
        m = FIELD.match(line.strip())
        if m:
            fields[m.group(1)] = m.group(2)
    return fields


def detect_langs(text: str) -> str:
    """Languages used, read off the code fences, in first-seen order."""
    seen: list[str] = []
    for tag in FENCE.findall(text):
        name = LANGS.get(tag.lower())
        if name and name not in seen:
            seen.append(name)
    return " / ".join(seen)


def has_code(text: str) -> bool:
    """True once a code fence actually contains something.

    `./new` leaves the fence empty, so an empty fence means a draft.
    """
    return any(
        body.strip() for tag, body in CODE_BLOCK.findall(text) if tag.lower() in LANGS
    )


def all_solutions(only: set[str] | None = None) -> list[Solution]:
    """Every solution file, including repeat attempts at the same problem.

    `only` restricts the walk to a set of repo-relative paths.
    """
    found: list[Solution] = []
    for path in sorted(REPO_ROOT.rglob("*.md")):
        if not DATE_DIR.match(path.parent.name):
            continue
        if only is not None and path.relative_to(REPO_ROOT).as_posix() not in only:
            continue
        text = path.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if not fm or not fm.get("question_id", "").isdigit():
            continue
        found.append(
            Solution(
                id=fm["question_id"],
                title=fm.get("title", ""),
                link=fm.get("question_link", ""),
                difficulty=fm.get("difficulty", ""),
                lang=detect_langs(text),
                date=path.parent.name,
                path=path.relative_to(REPO_ROOT).as_posix(),
                draft=not has_code(text),
            )
        )
    return found


def solutions(only: set[str] | None = None) -> list[Solution]:
    """The best record per problem, ordered by id.

    Re-attempting a problem scaffolds a fresh empty file on today's date, so a
    written-up file must outrank a newer draft of the same problem.
    """
    best: dict[int, Solution] = {}
    for rec in all_solutions(only):
        current = best.get(int(rec["id"]))
        if current is None or _rank(rec) > _rank(current):
            best[int(rec["id"])] = rec
    return [best[k] for k in sorted(best)]


def _rank(rec: Solution) -> tuple[bool, str]:
    return (not rec["draft"], rec["date"])


def scaffold(title: str, question_id: str, slug: str, difficulty: str, lang: str) -> str:
    """Fill template.md in with one problem's details."""
    return Template(TEMPLATE.read_text(encoding="utf-8")).safe_substitute(
        title=title,
        id=question_id,
        link=f"https://leetcode.com/problems/{slug}/",
        difficulty=difficulty,
        lang=lang,
    )
