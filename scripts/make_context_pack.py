"""Build the context pack: one compact Markdown file that gives a Claude chat the project.

Students on Claude's free plan cannot give Claude the repository, so they upload this
pack instead. It summarises the brief, the architecture, the mart schema, the roadmap,
deployment, the folder tree, the key Python interfaces and the open issues.

Usage (standard library only, so no install is needed):

    python3 scripts/make_context_pack.py                      # writes docs/context-pack.md
    python3 scripts/make_context_pack.py --issues issues.json --zip dist/ihub-context-pack.zip

``--issues`` takes the JSON returned by the GitHub REST API
(``GET /repos/{owner}/{repo}/issues``). The GitHub Action ``context-pack.yml`` runs this
after every merge to ``main`` and publishes the result on the ``context-pack`` release.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_CHARS = 30_000  # about 8,000 tokens: leaves most of a free chat for the work itself
REPO_URL = "https://github.com/DataLab-UNZA/ihub-data-analytics-platform"

# Files bundled with the pack in the zip, next to context-pack.md.
ZIP_EXTRAS = ["docs/STUDENT_GUIDE.md", "docs/STUDENT_PROMPTS.md"]

INSTRUCTIONS = """\
## How to use this pack (instructions for Claude)

You are helping a student on the iHub team. You cannot see the repository or run anything:
the student copies your code into files on their own computer, runs the commands and
pastes the results back to you.

- Read this whole pack before answering. Treat it as the current state of the project.
- Follow the conventions below exactly (uv, ruff, pytest, dbt names, British English).
- Whenever a decision is needed, give 2 to 4 numbered options, one line each with the
  trade-off, mark your recommendation, and wait for the student's number.
- Keep answers short: the student is on the free plan and every message counts.
- Give complete files (or clearly marked whole functions) with the file path above each,
  never fragments that leave the student guessing where code goes.
- After code, list the exact commands to run: `uv run ruff check .`,
  `uv run ruff format --check .`, `uv run pytest`.
- Never invent identifiers, URLs, IDs or API fields. If something is not in this pack,
  ask the student to paste the file or say that it must be verified.
- Never put secrets in code. Never mention Claude in commits or pull requests.
- If the student's usage is running out, tell them to push their branch and email
  Lighton Phiri (lighton.phiri@unza.ac.zm), subject "iHub: please run on Max", with the
  branch name and the next prompt.
"""


def _run(*args: str) -> str:
    """Run a command in the repository and return its output ('' on failure)."""
    try:
        return subprocess.run(
            args, cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def _read(rel: str) -> str:
    path = ROOT / rel
    return path.read_text(encoding="utf-8") if path.exists() else ""


def section(markdown: str, heading: str) -> str:
    """Return the body of a '## heading' section (up to the next heading of the same level)."""
    pattern = rf"^## {re.escape(heading)}[^\n]*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, markdown, flags=re.S | re.M)
    return match.group(1).strip() if match else ""


def folder_tree() -> str:
    """Tracked files as an indented tree, with .gitkeep folders shown as empty."""
    files = _run("git", "ls-files").splitlines()
    skip = ("uv.lock", "docs/context-pack.md")
    lines: list[str] = []
    seen: set[str] = set()
    for f in sorted(files):
        if f in skip:
            continue
        parts = f.split("/")
        for depth in range(len(parts) - 1):
            folder = "/".join(parts[: depth + 1])
            if folder not in seen:
                seen.add(folder)
                lines.append("  " * depth + parts[depth] + "/")
        if parts[-1] != ".gitkeep":
            lines.append("  " * (len(parts) - 1) + parts[-1])
    return "\n".join(lines)


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = ast.unparse(node.args)
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"{node.name}({args}){returns}"


def _first_line(node: ast.AST) -> str:
    doc = ast.get_docstring(node)  # type: ignore[arg-type]
    return doc.strip().splitlines()[0] if doc else ""


def interfaces() -> str:
    """Public classes and functions in src/ihub, with their first docstring line."""
    out: list[str] = []
    for path in sorted((ROOT / "src" / "ihub").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        items: list[str] = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                if not node.name.startswith("_"):
                    items.append(f"- `{_signature(node)}`: {_first_line(node)}".rstrip(": "))
            elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                bases = ", ".join(ast.unparse(b) for b in node.bases)
                name = f"{node.name}({bases})" if bases else node.name
                items.append(f"- class `{name}`: {_first_line(node)}".rstrip(": "))
                for sub in node.body:
                    if isinstance(sub, ast.FunctionDef) and not sub.name.startswith("_"):
                        items.append(f"  - `{_signature(sub)}`: {_first_line(sub)}".rstrip(": "))
        if items:
            rel = path.relative_to(ROOT).as_posix()
            module_doc = _first_line(tree)
            out.append(f"**`{rel}`**" + (f": {module_doc}" if module_doc else ""))
            out.extend(items)
    return "\n".join(out) or "(no public functions yet)"


def dbt_models() -> str:
    """dbt models that exist so far, grouped by layer."""
    models = sorted((ROOT / "transform" / "models").rglob("*.sql"))
    if not models:
        return "No dbt models yet (stage 1 adds the first ones)."
    return "\n".join(f"- `{m.relative_to(ROOT).as_posix()}`" for m in models)


def open_issues(issues_json: Path | None) -> str:
    """Open issues (not pull requests) with their labels."""
    if issues_json is None or not issues_json.exists():
        return f"Not included in this local build. See {REPO_URL}/issues"
    issues = [i for i in json.loads(issues_json.read_text()) if "pull_request" not in i]
    if not issues:
        return "No open issues."
    lines = []
    for i in sorted(issues, key=lambda x: x["number"]):
        labels = ", ".join(lab["name"] for lab in i.get("labels", []))
        lines.append(f"- #{i['number']} {i['title']}" + (f" [{labels}]" if labels else ""))
    return "\n".join(lines)


def deployment_summary() -> str:
    text = _read("docs/DEPLOYMENT.md")
    intro = text.split("\n## ", 1)[0].split("\n", 1)[-1].strip()
    return "\n\n".join(
        part
        for part in (
            intro,
            section(text, "How it works"),
            section(text, "Approving a deployment"),
        )
        if part
    )


def build(issues_json: Path | None = None) -> str:
    """Return the context pack as Markdown."""
    claude = _read("CLAUDE.md")
    roadmap = _read("docs/ROADMAP.md")
    commit = _run("git", "rev-parse", "--short", "HEAD") or "unknown"
    built = datetime.now(UTC)
    when = f"{built:%B} {built.day}, {built:%Y} at {built:%H:%M} UTC"

    parts = [
        "# iHub Data Analytics Platform: context pack",
        f"Built from commit `{commit}` on {when}. Repository: {REPO_URL}",
        INSTRUCTIONS,
        "## Project\n\n" + section(claude, "Project context"),
        "## Architecture\n\n" + section(claude, "Architecture"),
        "## Conventions\n\n" + section(claude, "Conventions"),
        "## Roadmap and status\n\n" + section(roadmap, "Stages"),
        "## Open issues\n\n" + open_issues(issues_json),
        "## Deployment\n\n" + deployment_summary(),
        "## Folder tree\n\n```\n" + folder_tree() + "\n```",
        "## Key Python interfaces\n\n" + interfaces(),
        "## dbt models\n\n" + dbt_models(),
        "## Source settings (config/sources.yml)\n\n```yaml\n"
        + _read("config/sources.yml").strip()
        + "\n```",
    ]
    pack = "\n\n".join(p.strip() for p in parts) + "\n"
    if len(pack) > MAX_CHARS:
        note = f"\n\n(Pack cut at {MAX_CHARS:,} characters. Ask the student for any file.)\n"
        pack = pack[: MAX_CHARS - len(note)] + note
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "context-pack.md")
    parser.add_argument("--issues", type=Path, help="JSON from the GitHub issues API")
    parser.add_argument("--zip", type=Path, help="also write a zip with the student docs")
    args = parser.parse_args()

    pack = build(args.issues)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(pack, encoding="utf-8")
    print(f"Wrote {args.out} ({len(pack):,} characters)")

    if args.zip:
        args.zip.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.zip, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("ihub-context-pack/context-pack.md", pack)
            for rel in ZIP_EXTRAS:
                if (ROOT / rel).exists():
                    zf.write(ROOT / rel, f"ihub-context-pack/{Path(rel).name}")
        print(f"Wrote {args.zip}")


if __name__ == "__main__":
    main()
