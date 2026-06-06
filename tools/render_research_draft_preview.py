"""Render a Financial Research Draft markdown file to a local HTML preview."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


def _inline(markdown_text: str) -> str:
    escaped = html.escape(markdown_text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def _slug(text: str) -> str:
    slug = re.sub(r"<[^>]+>", "", text)
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", slug).strip("-").lower()
    return slug or "section"


def _is_table_divider(line: str) -> bool:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in cells)


def _consume_table(lines: list[str], start: int) -> tuple[str, int]:
    rows: list[list[str]] = []
    index = start
    while index < len(lines):
        line = lines[index]
        if "|" not in line or not line.strip():
            break
        if _is_table_divider(line):
            index += 1
            continue
        rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
        index += 1

    if not rows:
        return "", start

    header = rows[0]
    body = rows[1:]
    parts = ["<div class=\"table-wrap\"><table>"]
    parts.append(
        "<thead><tr>"
        + "".join(f"<th>{_inline(cell)}</th>" for cell in header)
        + "</tr></thead>"
    )
    parts.append("<tbody>")
    for row in body:
        while len(row) < len(header):
            row.append("")
        parts.append("<tr>" + "".join(f"<td>{_inline(cell)}</td>" for cell in row) + "</tr>")
    parts.append("</tbody></table></div>")
    return "\n".join(parts), index


def render_markdown(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    body: list[str] = []
    toc: list[tuple[int, str, str]] = []
    in_list = False
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            body.append("<p>" + " ".join(_inline(part) for part in paragraph) + "</p>")
            paragraph = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            body.append("</ul>")
            in_list = False

    index = 0
    while index < len(lines):
        raw = lines[index]
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            close_list()
            index += 1
            continue

        if stripped.startswith("#"):
            flush_paragraph()
            close_list()
            level = len(stripped) - len(stripped.lstrip("#"))
            title = stripped[level:].strip()
            rendered_title = _inline(title)
            anchor = _slug(rendered_title)
            toc.append((level, anchor, html.escape(title)))
            body.append(f"<h{level} id=\"{anchor}\">{rendered_title}</h{level}>")
            index += 1
            continue

        if stripped.startswith("> "):
            flush_paragraph()
            close_list()
            body.append(f"<blockquote>{_inline(stripped[2:].strip())}</blockquote>")
            index += 1
            continue

        if "|" in stripped and index + 1 < len(lines) and _is_table_divider(lines[index + 1]):
            flush_paragraph()
            close_list()
            table_html, next_index = _consume_table(lines, index)
            body.append(table_html)
            index = next_index
            continue

        if stripped.startswith("- "):
            flush_paragraph()
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{_inline(stripped[2:].strip())}</li>")
            index += 1
            continue

        paragraph.append(stripped)
        index += 1

    flush_paragraph()
    close_list()

    toc_items = []
    for level, anchor, title in toc:
        if level <= 3:
            toc_items.append(f"<a class=\"toc-l{level}\" href=\"#{anchor}\">{title}</a>")

    return HTML_TEMPLATE.format(toc="\n".join(toc_items), body="\n".join(body))


HTML_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Financial Research Draft Preview</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --paper: #ffffff;
      --ink: #17202a;
      --muted: #667085;
      --line: #d9dee7;
      --accent: #1f6feb;
      --soft: #eef4ff;
      --code: #f2f4f7;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      line-height: 1.62;
    }}
    .shell {{
      display: grid;
      grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
      gap: 24px;
      max-width: 1480px;
      margin: 0 auto;
      padding: 28px;
    }}
    nav {{
      position: sticky;
      top: 20px;
      align-self: start;
      max-height: calc(100vh - 40px);
      overflow: auto;
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--paper);
    }}
    nav .label {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
      margin-bottom: 10px;
    }}
    nav a {{
      display: block;
      color: #344054;
      text-decoration: none;
      border-radius: 6px;
      padding: 5px 8px;
      font-size: 13px;
    }}
    nav a:hover {{ background: var(--soft); color: var(--accent); }}
    .toc-l2 {{ margin-left: 8px; }}
    .toc-l3 {{ margin-left: 20px; color: var(--muted); }}
    main {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 34px 42px;
      min-width: 0;
    }}
    h1 {{
      margin: 0 0 18px;
      font-size: 30px;
      line-height: 1.25;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 36px 0 14px;
      padding-top: 20px;
      border-top: 1px solid var(--line);
      font-size: 22px;
      letter-spacing: 0;
    }}
    h3 {{
      margin: 28px 0 10px;
      font-size: 17px;
      letter-spacing: 0;
    }}
    p, li {{ font-size: 15px; }}
    blockquote {{
      margin: 16px 0 22px;
      padding: 14px 16px;
      border-left: 4px solid var(--accent);
      background: var(--soft);
      color: #243b53;
      border-radius: 8px;
    }}
    code {{
      background: var(--code);
      border: 1px solid #eaecf0;
      border-radius: 5px;
      padding: 1px 5px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: .92em;
    }}
    ul {{ padding-left: 22px; }}
    .table-wrap {{
      overflow-x: auto;
      margin: 14px 0 24px;
      border: 1px solid var(--line);
      border-radius: 9px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      padding: 9px 10px;
      border-bottom: 1px solid #edf0f5;
      vertical-align: top;
      text-align: left;
    }}
    th {{
      background: #f8fafc;
      color: #344054;
      font-weight: 700;
      white-space: nowrap;
    }}
    tr:last-child td {{ border-bottom: none; }}
    @media (max-width: 920px) {{
      .shell {{ display: block; padding: 14px; }}
      nav {{ position: static; margin-bottom: 14px; max-height: none; }}
      main {{ padding: 22px 18px; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <nav>
      <div class="label">Contents</div>
      {toc}
    </nav>
    <main>
      {body}
    </main>
  </div>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    markdown_text = args.input.read_text(encoding="utf-8")
    args.output.write_text(render_markdown(markdown_text), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
