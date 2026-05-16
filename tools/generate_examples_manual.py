#!/usr/bin/env python3
"""Generate a Markdown manual from KrakenOS example scripts.

The generator reads `KrakenOS/Examples/EXAMPLES_INDEX.md`, extracts the module
docstring from each listed example, and writes `docs/examples_manual.md`.

It intentionally does not execute examples. Many KrakenOS examples open 3D
viewers, use large datasets, or depend on an interactive plotting backend. Image
capture can be added later example by example under `docs/assets/examples/`.
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "KrakenOS" / "Examples"
INDEX_PATH = EXAMPLES_DIR / "EXAMPLES_INDEX.md"
OUTPUT_PATH = REPO_ROOT / "docs" / "examples_manual.md"
ASSET_DIR = REPO_ROOT / "docs" / "assets" / "examples"


@dataclass
class Example:
    file_name: str
    level: str
    topic: str
    description: str
    required_files: str
    docstring: str

    @property
    def code_link(self) -> str:
        return f"../KrakenOS/Examples/{quote_link_path(self.file_name)}"

    @property
    def anchor(self) -> str:
        base = self.file_name.lower().replace(".py", "")
        base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
        return base

    @property
    def image_file_name(self) -> str:
        return self.file_name.replace(".py", ".png")

    @property
    def image_path(self) -> Path:
        return ASSET_DIR / self.image_file_name

    @property
    def image_link(self) -> str:
        return f"assets/examples/{quote_link_path(self.image_file_name)}"


def quote_link_path(path: str) -> str:
    return (
        path.replace(" ", "%20")
        .replace("(", "%28")
        .replace(")", "%29")
        .replace(",", "%2C")
        .replace("#", "%23")
    )


def parse_index() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in INDEX_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `Examp_"):
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) != 5:
            continue
        file_name = parts[0].strip("`")
        rows.append(
            {
                "file_name": file_name,
                "level": parts[1],
                "topic": parts[2],
                "description": parts[3],
                "required_files": parts[4],
            }
        )
    return rows


def read_docstring(file_name: str) -> str:
    source_path = EXAMPLES_DIR / file_name
    try:
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        tree = ast.parse(source_path.read_text(encoding="latin-1"))
    return ast.get_docstring(tree) or ""


def load_examples() -> list[Example]:
    examples = []
    for row in parse_index():
        examples.append(
            Example(
                file_name=row["file_name"],
                level=row["level"],
                topic=row["topic"],
                description=row["description"],
                required_files=row["required_files"],
                docstring=read_docstring(row["file_name"]),
            )
        )
    return examples


def first_paragraph(docstring: str, fallback: str) -> str:
    if not docstring:
        return fallback
    paragraphs = [part.strip() for part in docstring.split("\n\n") if part.strip()]
    if len(paragraphs) == 1:
        return paragraphs[0]
    title = paragraphs[0]
    body = paragraphs[1]
    if title.lower().startswith("example:"):
        return body
    return f"{title}\n\n{body}"


def extract_section(docstring: str, heading: str) -> list[str]:
    lines = docstring.splitlines()
    capture = False
    result: list[str] = []
    known_headings = {
        "what this example teaches:",
        "key ideas:",
        "expected output:",
        "didactic note:",
        "units:",
        "required packaged files:",
    }

    for line in lines:
        normalized = line.strip().lower()
        if normalized == heading.lower():
            capture = True
            continue
        if capture and normalized in known_headings:
            break
        if capture:
            result.append(line.rstrip())

    return [line for line in result if line.strip()]


def render_bullets(lines: list[str]) -> list[str]:
    if not lines:
        return []
    rendered = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- "):
            rendered.append(stripped)
        elif rendered:
            rendered[-1] = f"{rendered[-1]} {stripped}"
        else:
            rendered.append(f"- {stripped}")
    return rendered


def render_manual(examples: list[Example]) -> str:
    by_topic: dict[str, list[Example]] = defaultdict(list)
    for example in examples:
        by_topic[example.topic].append(example)

    lines: list[str] = [
        "# KrakenOS Examples Manual",
        "",
        "This manual is generated from the example scripts in `KrakenOS/Examples`.",
        "Each section links back to the runnable Python file and summarizes the",
        "didactic notes written in the example docstrings.",
        "",
        "Generated with:",
        "",
        "```bash",
        "python tools/generate_examples_manual.py",
        "```",
        "",
        "Images can be added manually under `docs/assets/examples/` and linked from",
        "the relevant example sections. The generator does not run examples because",
        "many scripts open interactive 2D or 3D viewers.",
        "",
        "## Quick Index",
        "",
    ]

    for topic in sorted(by_topic):
        lines.append(f"- [{topic}](#{quote_anchor(topic)})")
    lines.append("")

    for topic in sorted(by_topic):
        lines.extend([f"## {topic}", ""])
        topic_examples = sorted(by_topic[topic], key=lambda item: (item.level, item.file_name))

        lines.extend(["| Example | Level | Summary | Required files |", "| --- | --- | --- | --- |"])
        for example in topic_examples:
            lines.append(
                f"| [`{example.file_name}`](#{example.anchor}) | "
                f"{example.level} | {example.description} | {example.required_files} |"
            )
        lines.append("")

        for example in topic_examples:
            lines.extend(
                [
                    f"### {example.file_name}",
                    "",
                    f"- **Level:** {example.level}",
                    f"- **Topic:** {example.topic}",
                    f"- **Required files:** {example.required_files}",
                    f"- **Source:** [`{example.file_name}`]({example.code_link})",
                    "",
                    first_paragraph(example.docstring, example.description),
                    "",
                ]
            )

            teaches = extract_section(example.docstring, "What this example teaches:")
            if not teaches:
                teaches = extract_section(example.docstring, "Key ideas:")
            expected = extract_section(example.docstring, "Expected output:")
            didactic = extract_section(example.docstring, "Didactic note:")
            units = extract_section(example.docstring, "Units:")

            if teaches:
                lines.extend(["**What You Learn**", ""])
                lines.extend(render_bullets(teaches))
                lines.append("")
            if expected:
                lines.extend(["**Expected Output**", ""])
                lines.extend(render_bullets(expected))
                lines.append("")
            if didactic:
                lines.extend(["**Didactic Notes**", ""])
                lines.extend(render_bullets(didactic))
                lines.append("")
            if units:
                lines.extend(["**Units**", ""])
                lines.extend(render_bullets(units))
                lines.append("")

            lines.extend(
                [
                    "**Run**",
                    "",
                    "```bash",
                    f"python KrakenOS/Examples/{shell_path(example.file_name)}",
                    "```",
                    "",
                ]
            )

            if example.image_path.exists():
                lines.extend(
                    [
                        "**Example Image**",
                        "",
                        f"![{example.file_name}]({example.image_link})",
                        "",
                    ]
                )
            else:
                lines.extend(
                    [
                        "<!-- Optional image placeholder:",
                        f"Add docs/assets/examples/{example.image_file_name} to show an image here.",
                        "-->",
                        "",
                    ]
                )

    return "\n".join(lines).rstrip() + "\n"


def quote_anchor(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def shell_path(path: str) -> str:
    if any(char in path for char in " ()#,"):
        return f'"{path}"'
    return path


def main() -> int:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    manual = render_manual(load_examples())
    OUTPUT_PATH.write_text(manual, encoding="utf-8", newline="\n")
    keep = ASSET_DIR / ".gitkeep"
    if not keep.exists():
        keep.write_text("", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
