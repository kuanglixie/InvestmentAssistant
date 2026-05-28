from __future__ import annotations

import html
import re
import sys
from pathlib import Path


STYLE = """:root{color-scheme:light;--bg:#f6f5f1;--paper:#fffdf8;--ink:#1f2933;--muted:#65717f;--line:#dedbd1;--soft:#f1efe8;--accent:#0f766e;--accent-soft:#dff6f2}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.58}.shell{max-width:1220px;margin:0 auto;padding:0 26px 72px;background:var(--paper);min-height:100vh;box-shadow:0 0 0 1px var(--line)}.topbar{position:sticky;top:0;z-index:5;margin:0 -26px 34px;padding:16px 26px;background:rgba(255,253,248,.96);border-bottom:1px solid var(--line);backdrop-filter:blur(10px);display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap}.title{font-size:15px;color:var(--muted)}.nav{display:flex;gap:8px;flex-wrap:wrap}.nav a{display:inline-flex;align-items:center;min-height:34px;padding:6px 11px;border:1px solid var(--line);border-radius:6px;background:#fff;color:#0f766e;text-decoration:none;font-size:13px}.nav a:hover{background:var(--accent-soft)}section.report{padding:8px 0 36px;border-bottom:1px solid var(--line)}h1,h2,h3,h4,h5,h6{line-height:1.22;color:#111827;letter-spacing:0}h1{font-size:34px;margin:0 0 10px}h2{font-size:23px;margin:38px 0 14px;border-top:1px solid var(--line);padding-top:24px}section.report>h1:first-child{padding-top:16px}h3{font-size:18px;margin:28px 0 10px}h4{font-size:16px;margin:24px 0 8px;color:#374151}h5{font-size:15px;margin:20px 0 8px;color:#111827}h6{font-size:14px;margin:18px 0 8px;color:#374151}p,li{font-size:14px}p{margin:0 0 12px}ul,ol{padding-left:22px;margin:8px 0 16px}li{margin:5px 0}code{background:#eef1f4;border-radius:4px;padding:1px 5px;font-size:13px}pre{background:#111827;color:#f9fafb;border-radius:7px;padding:14px 16px;overflow-x:auto;font-size:13px;line-height:1.45}pre code{background:transparent;color:inherit;padding:0}.table-wrap{overflow-x:auto;margin:15px 0 22px;border:1px solid #e3e0d8;border-radius:7px;background:#fff}table{border-collapse:collapse;min-width:760px;width:100%;font-size:13px}th,td{padding:9px 11px;border-bottom:1px solid #e8e5dd;vertical-align:top;text-align:left}th{background:var(--soft);color:#111827;font-weight:650}tr:nth-child(even) td{background:#fbfaf6}a{color:var(--accent);text-decoration:none}strong{font-weight:700;color:#111827}@media(max-width:760px){.shell{padding:0 16px 56px}.topbar{margin:0 -16px 28px;padding:13px 16px;align-items:flex-start}h1{font-size:27px}h2{font-size:20px}table{min-width:700px}}"""


def render_inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def render_markdown(markdown: str) -> str:
    lines = markdown.splitlines()
    out: list[str] = []
    in_list = False
    in_code = False
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_code:
                out.append("<pre><code>")
                in_code = True
            else:
                out.append("</code></pre>")
                in_code = False
            index += 1
            continue
        if in_code:
            out.append(html.escape(line))
            index += 1
            continue
        if stripped.startswith("|") and index + 1 < len(lines) and set(lines[index + 1].replace("|", "").strip()) <= {"-", ":", " "}:
            if in_list:
                out.append("</ul>")
                in_list = False
            headers = [cell.strip() for cell in stripped.strip("|").split("|")]
            out.append('<div class="table-wrap"><table><thead><tr>')
            out.extend(f"<th>{render_inline(cell)}</th>" for cell in headers)
            out.append("</tr></thead><tbody>")
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                out.append("<tr>")
                out.extend(f"<td>{render_inline(cell)}</td>" for cell in cells)
                out.append("</tr>")
                index += 1
            out.append("</tbody></table></div>")
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            if in_list:
                out.append("</ul>")
                in_list = False
            level = len(heading.group(1))
            text = render_inline(heading.group(2))
            out.append(f"<h{level}>{text}</h{level}>")
            index += 1
            continue
        if stripped.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{render_inline(stripped[2:])}</li>")
            index += 1
            continue
        if not stripped:
            if in_list:
                out.append("</ul>")
                in_list = False
            index += 1
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        out.append(f"<p>{render_inline(stripped)}</p>")
        index += 1
    if in_list:
        out.append("</ul>")
    if in_code:
        out.append("</code></pre>")
    return "\n".join(out)


def main() -> int:
    if len(sys.argv) < 4:
        print("Usage: render_markdown_preview.py input.md output.html title [nav_html]", file=sys.stderr)
        return 2
    source = Path(sys.argv[1])
    output = Path(sys.argv[2])
    title = sys.argv[3]
    nav = sys.argv[4] if len(sys.argv) > 4 else ""
    body = render_markdown(source.read_text(encoding="utf-8"))
    doc = (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{html.escape(title)}</title><style>{STYLE}</style></head><body><main class=\"shell\">"
        f"<div class=\"topbar\"><div class=\"title\">Rendered preview from <code>{html.escape(source.name)}</code></div><nav class=\"nav\">{nav}</nav></div>"
        f"<section class=\"report\">{body}</section></main></body></html>"
    )
    output.write_text(doc, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
