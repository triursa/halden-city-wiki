#!/usr/bin/env python3
"""
Halden City Wiki Builder
Converts markdown files into a navigatable GitHub Pages site.
No third-party dependencies — stdlib only.
"""

import os
import re
import shutil
from pathlib import Path
from datetime import datetime

# ── Configuration ──────────────────────────────────────────────────────────────

REPO_ROOT  = Path(__file__).parent
DOCS_DIR   = REPO_ROOT / "docs"
IMAGES_SRC = REPO_ROOT / "images"          # source image tree
IMAGES_DST = DOCS_DIR  / "images"          # destination inside docs/

# Extensions checked in order when looking for a character portrait.
IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]

# Sections that get portrait injection (keyed by SECTION_CONFIG "key").
PORTRAIT_SECTIONS = {"pcs", "npcs"}

SECTION_CONFIG = [
    {
        "key":       "pcs",
        "label":     "Player Characters",
        "icon":      "★",
        "subfolder": "characters/pcs",
    },
    {
        "key":       "npcs",
        "label":     "Characters",
        "icon":      "◈",
        "subfolder": "characters/npcs",
    },
    {
        "key":       "factions",
        "label":     "Factions",
        "icon":      "◉",
        "subfolder": "factions",
    },
    {
        "key":       "locations",
        "label":     "Locations",
        "icon":      "◎",
        "subfolder": "locations",
    },
    {
        "key":       "lore",
        "label":     "Lore",
        "icon":      "◇",
        "subfolder": "lore",
    },
    {
        "key":       "plot",
        "label":     "Plot",
        "icon":      "◆",
        "subfolder": "plot",
    },
    {
        "key":       "meta",
        "label":     "Meta",
        "icon":      "◌",
        "subfolder": "meta",
    },
]

# ── Image helpers ──────────────────────────────────────────────────────────────

def find_image(stem: str):
    """
    Look for images/characters/<stem>.<ext> for each supported extension.
    Returns the Path if found, else None.
    """
    base = IMAGES_SRC / "characters"
    for ext in IMAGE_EXTENSIONS:
        candidate = base / (stem + ext)
        if candidate.exists():
            return candidate
    return None


def portrait_html(stem: str, title: str, prefix: str) -> str:
    """
    Return the HTML for a character portrait block, or '' if no images found.

    Priority / layout rules:
      1. Both -civilian and -super exist  ->  two images side by side, labelled
      2. Only one of -civilian / -super   ->  single image, labelled
      3. Neither suffix, plain stem       ->  single image, no label
      4. Nothing found                    ->  empty string
    """
    base_url = prefix + "images/characters/"

    civilian = find_image(stem + "-civilian")
    super_   = find_image(stem + "-super")
    plain    = find_image(stem)

    if civilian and super_:
        return (
            f'<div class="portrait-wrap portrait-dual">'
            f'<div class="portrait-panel">'
            f'<img src="{base_url}{civilian.name}" alt="{title} — Civilian" class="portrait-img">'
            f'<span class="portrait-label">Civilian</span>'
            f'</div>'
            f'<div class="portrait-panel">'
            f'<img src="{base_url}{super_.name}" alt="{title} — Superhero" class="portrait-img">'
            f'<span class="portrait-label">Superhero</span>'
            f'</div>'
            f'</div>\n'
        )

    single = civilian or super_ or plain
    if single is None:
        return ""

    label_html = (
        f'<span class="portrait-label">{"Civilian" if civilian else "Superhero"}</span>'
        if (civilian or super_) else ""
    )
    alt_suffix = " — Civilian" if civilian else (" — Superhero" if super_ else "")
    return (
        f'<div class="portrait-wrap">'
        f'<img src="{base_url}{single.name}" alt="{title}{alt_suffix}" class="portrait-img">'
        f'{label_html}'
        f'</div>\n'
    )


def copy_images():
    """Copy the entire images/ source tree into docs/images/ if it exists."""
    if not IMAGES_SRC.exists():
        return
    if IMAGES_DST.exists():
        shutil.rmtree(IMAGES_DST)
    shutil.copytree(IMAGES_SRC, IMAGES_DST)
    count = sum(1 for _ in IMAGES_DST.rglob("*") if _.is_file())
    print(f"  Copied {count} image(s) → docs/images/")


# ── Markdown renderer (stdlib only) ───────────────────────────────────────────

def escape_html(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def inline(text):
    """Process inline markdown: bold, italic, code, links, strikethrough."""
    parts = re.split(r'(`+)', text)
    result = []
    i = 0
    while i < len(parts):
        if re.match(r'`+', parts[i]) and i + 2 < len(parts) and parts[i+2] == parts[i]:
            result.append(f'<code>{escape_html(parts[i+1])}</code>')
            i += 3
        else:
            chunk = parts[i]
            chunk = re.sub(r'\*\*\*(.+?)\*\*\*', lambda m: f'<strong><em>{escape_html(m.group(1))}</em></strong>', chunk)
            chunk = re.sub(r'\*\*(.+?)\*\*',     lambda m: f'<strong>{escape_html(m.group(1))}</strong>', chunk)
            chunk = re.sub(r'\*(.+?)\*',          lambda m: f'<em>{escape_html(m.group(1))}</em>', chunk)
            chunk = re.sub(r'~~(.+?)~~',          lambda m: f'<del>{escape_html(m.group(1))}</del>', chunk)
            chunk = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', lambda m: f'<a href="{m.group(2)}">{escape_html(m.group(1))}</a>', chunk)
            chunk = re.sub(r'(?<!<)&(?!amp;|lt;|gt;|#)', '&amp;', chunk)
            result.append(chunk)
            i += 1
    return "".join(result)

def render_table(lines):
    html = ['<table>']
    header_done = False
    for line in lines:
        line = line.strip()
        if re.match(r'^\|[-| :]+\|$', line):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if not header_done:
            html.append('<thead><tr>')
            for c in cells:
                html.append(f'<th>{inline(c)}</th>')
            html.append('</tr></thead><tbody>')
            header_done = True
        else:
            html.append('<tr>')
            for c in cells:
                html.append(f'<td>{inline(c)}</td>')
            html.append('</tr>')
    html.append('</tbody></table>')
    return '\n'.join(html)

def render_markdown(md_text):
    lines = md_text.splitlines()
    html_parts = []
    i = 0

    def flush_paragraph(buf):
        if buf:
            content = ' '.join(buf).strip()
            if content:
                html_parts.append(f'<p>{inline(content)}</p>')
            buf.clear()

    paragraph_buf = []
    in_code_block = False
    code_buf = []
    code_lang = ''
    in_list = None
    list_buf = []
    in_table = False
    table_buf = []

    def flush_list():
        nonlocal in_list
        if in_list and list_buf:
            items_html = ''.join(f'<li>{inline(item)}</li>' for item in list_buf)
            html_parts.append(f'<{in_list}>{items_html}</{in_list}>')
            list_buf.clear()
            in_list = None

    def flush_table():
        nonlocal in_table
        if in_table and table_buf:
            html_parts.append(render_table(table_buf))
            table_buf.clear()
            in_table = False

    while i < len(lines):
        line = lines[i]

        if line.strip().startswith('```'):
            if in_code_block:
                code_html = escape_html('\n'.join(code_buf))
                lang_class = f' class="language-{code_lang}"' if code_lang else ''
                html_parts.append(f'<pre><code{lang_class}>{code_html}</code></pre>')
                code_buf = []; code_lang = ''; in_code_block = False
            else:
                flush_paragraph(paragraph_buf); flush_list(); flush_table()
                code_lang = line.strip()[3:].strip()
                in_code_block = True
            i += 1; continue

        if in_code_block:
            code_buf.append(line); i += 1; continue

        if '|' in line and i + 1 < len(lines) and re.match(r'^\|[-| :]+\|', lines[i+1].strip()):
            flush_paragraph(paragraph_buf); flush_list()
            in_table = True; table_buf.append(line); i += 1; continue

        if in_table:
            if '|' in line:
                table_buf.append(line); i += 1; continue
            else:
                flush_table()

        m = re.match(r'^(#{1,6})\s+(.*)', line)
        if m:
            flush_paragraph(paragraph_buf); flush_list()
            level = len(m.group(1))
            text  = inline(m.group(2))
            html_parts.append(f'<h{level}>{text}</h{level}>')
            i += 1; continue

        if re.match(r'^[-*_]{3,}\s*$', line):
            flush_paragraph(paragraph_buf); flush_list()
            html_parts.append('<hr>'); i += 1; continue

        if line.startswith('>'):
            flush_paragraph(paragraph_buf); flush_list()
            bq_lines = []
            while i < len(lines) and lines[i].startswith('>'):
                bq_lines.append(lines[i][1:].strip()); i += 1
            inner = render_markdown('\n'.join(bq_lines))
            html_parts.append(f'<blockquote>{inner}</blockquote>'); continue

        m = re.match(r'^[-*+]\s+(.*)', line)
        if m:
            flush_paragraph(paragraph_buf)
            if in_list != 'ul': flush_list(); in_list = 'ul'
            item = m.group(1)
            item = re.sub(r'^\[x\]\s*', '<input type="checkbox" checked disabled> ', item, flags=re.I)
            item = re.sub(r'^\[ \]\s*', '<input type="checkbox" disabled> ', item)
            list_buf.append(item); i += 1; continue

        m = re.match(r'^\d+\.\s+(.*)', line)
        if m:
            flush_paragraph(paragraph_buf)
            if in_list != 'ol': flush_list(); in_list = 'ol'
            list_buf.append(m.group(1)); i += 1; continue

        if line.strip() == '':
            flush_paragraph(paragraph_buf); flush_list(); flush_table()
            i += 1; continue

        paragraph_buf.append(line); i += 1

    flush_paragraph(paragraph_buf); flush_list(); flush_table()
    return '\n'.join(html_parts)

# ── Page collection ────────────────────────────────────────────────────────────

def page_title(path):
    try:
        text = path.read_text(encoding="utf-8")
        m = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
        if m:
            t = m.group(1).strip()
            t = re.sub(r'\*+', '', t)
            return t.strip('"\'')
    except Exception:
        pass
    return path.stem.replace('-', ' ').replace('_', ' ').title()

def collect_pages():
    pages = {}
    nav   = {}

    index_path = REPO_ROOT / "WIKI-INDEX.md"
    if index_path.exists():
        pages["index"] = {
            "path": index_path, "title": "Home",
            "section_key": None, "section_label": None, "section_icon": None,
            "stem": None,
        }

    for cfg in SECTION_CONFIG:
        key        = cfg["key"]
        source_dir = REPO_ROOT / cfg["subfolder"]
        if not source_dir.is_dir():
            continue
        nav[key] = []
        for md_file in sorted(source_dir.glob("*.md")):
            if md_file.stem.startswith("_"):
                continue
            slug  = cfg["subfolder"].replace("\\", "/") + "/" + md_file.stem
            title = page_title(md_file)
            pages[slug] = {
                "path":          md_file,
                "title":         title,
                "section_key":   key,
                "section_label": cfg["label"],
                "section_icon":  cfg["icon"],
                "stem":          md_file.stem,   # used for portrait lookup
            }
            nav[key].append({"slug": slug, "title": title})

    return pages, nav

def depth_prefix(slug):
    return "../" * slug.count("/")

# ── CSS ────────────────────────────────────────────────────────────────────────

STYLE = """
:root {
  --bg:         #0d0d0f;
  --bg-surface: #141418;
  --bg-hover:   #1c1c22;
  --border:     #2a2a35;
  --accent:     #c8a96e;
  --accent-dim: #7a6640;
  --accent-pc:  #7eb8c8;
  --text:       #d4d0c8;
  --text-dim:   #7a7870;
  --text-head:  #e8e4dc;
  --link:       #c8a96e;
  --link-hover: #e8c88a;
  --code-bg:    #1a1a20;
  --sidebar-w:  280px;
  --font-mono:  'JetBrains Mono','Fira Code','Consolas',monospace;
  --font-body:  'Inter','Segoe UI',system-ui,sans-serif;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; background: var(--bg); color: var(--text);
  font-family: var(--font-body); font-size: 15px; line-height: 1.7; }

.layout { display: flex; min-height: 100vh; }

/* sidebar */
.sidebar { width: var(--sidebar-w); min-width: var(--sidebar-w);
  background: var(--bg-surface); border-right: 1px solid var(--border);
  display: flex; flex-direction: column; position: sticky; top: 0;
  height: 100vh; overflow-y: auto; overflow-x: hidden; }
.sidebar-header { padding: 24px 20px 16px; border-bottom: 1px solid var(--border); }
.sidebar-title { font-size: 13px; font-weight: 700; letter-spacing: .12em;
  text-transform: uppercase; color: var(--accent); line-height: 1.3; }
.sidebar-subtitle { font-size: 11px; color: var(--text-dim); margin-top: 4px; letter-spacing: .04em; }
.sidebar-nav { padding: 12px 0 24px; flex: 1; }

.nav-home { display: block; padding: 8px 20px; color: var(--text-dim);
  text-decoration: none; font-size: 13px; letter-spacing: .03em;
  border-left: 2px solid transparent; transition: color .15s, border-color .15s; }
.nav-home:hover, .nav-home.active { color: var(--accent); border-left-color: var(--accent);
  background: var(--bg-hover); }

.nav-section { margin-top: 16px; }
.nav-section-header { padding: 6px 20px; font-size: 10px; font-weight: 700;
  letter-spacing: .14em; text-transform: uppercase; color: var(--text-dim);
  display: flex; align-items: center; gap: 8px; }
.nav-section-icon { color: var(--accent-dim); font-size: 12px; }
.nav-section-icon.pc { color: var(--accent-pc); }

.nav-link { display: block; padding: 6px 20px 6px 28px; color: var(--text-dim);
  text-decoration: none; font-size: 13px; border-left: 2px solid transparent;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  transition: color .15s, background .15s, border-color .15s; }
.nav-link:hover { color: var(--text); background: var(--bg-hover); }
.nav-link.active { color: var(--accent); border-left-color: var(--accent); background: var(--bg-hover); }
.nav-link.pc:hover { color: var(--accent-pc); }
.nav-link.pc.active { color: var(--accent-pc); border-left-color: var(--accent-pc); }

/* main */
.main { flex: 1; min-width: 0; padding: 48px 64px; max-width: 900px; }
.breadcrumb { font-size: 11px; color: var(--text-dim); letter-spacing: .08em;
  text-transform: uppercase; margin-bottom: 32px; }
.breadcrumb a { color: var(--text-dim); text-decoration: none; }
.breadcrumb a:hover { color: var(--accent); }
.breadcrumb .sep { margin: 0 8px; }
.pc-badge { display: inline-block; font-size: 10px; font-weight: 700;
  letter-spacing: .12em; text-transform: uppercase; color: var(--accent-pc);
  border: 1px solid var(--accent-pc); padding: 2px 8px; border-radius: 3px;
  margin-left: 12px; vertical-align: middle; opacity: .8; }

/* portrait — single */
.portrait-wrap {
  float: right;
  margin: 0 0 24px 32px;
  width: 220px;
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
  background: var(--bg-surface);
  box-shadow: 0 4px 24px rgba(0,0,0,.5);
}
.portrait-img {
  display: block;
  width: 100%;
  height: auto;
}
.portrait-label {
  display: block;
  text-align: center;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--text-dim);
  padding: 6px 0 7px;
  background: var(--bg-surface);
  border-top: 1px solid var(--border);
}
/* portrait — dual (civilian + superhero) */
.portrait-dual {
  width: 460px;
  display: flex;
  flex-direction: row;
  gap: 0;
  overflow: visible;
  background: none;
  border: none;
  box-shadow: none;
}
.portrait-panel {
  flex: 1;
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
  background: var(--bg-surface);
  box-shadow: 0 4px 24px rgba(0,0,0,.5);
}
.portrait-panel + .portrait-panel {
  margin-left: 12px;
}
.clearfix::after { content: ""; display: table; clear: both; }

/* typography */
.content h1 { font-size: 28px; font-weight: 700; color: var(--text-head);
  letter-spacing: -.02em; margin-bottom: 8px; line-height: 1.2;
  border-bottom: 1px solid var(--border); padding-bottom: 16px; }
.content h2 { font-size: 13px; font-weight: 700; color: var(--accent);
  letter-spacing: .1em; margin: 40px 0 12px; text-transform: uppercase; }
.content h3 { font-size: 16px; font-weight: 600; color: var(--text-head); margin: 28px 0 8px; }
.content h4 { font-size: 14px; font-weight: 600; color: var(--text-dim);
  margin: 20px 0 6px; text-transform: uppercase; letter-spacing: .08em; }
.content p { margin-bottom: 14px; color: var(--text); }
.content a { color: var(--link); text-decoration: none; border-bottom: 1px solid var(--accent-dim);
  transition: color .15s, border-color .15s; }
.content a:hover { color: var(--link-hover); border-bottom-color: var(--link-hover); }
.content strong { color: var(--text-head); }
.content em { color: var(--text); }

/* tables */
.content table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 13px; }
.content thead th { text-align: left; padding: 10px 14px; background: var(--bg-surface);
  color: var(--accent); font-size: 11px; font-weight: 700; letter-spacing: .1em;
  text-transform: uppercase; border-bottom: 1px solid var(--border); }
.content tbody tr { border-bottom: 1px solid var(--border); transition: background .1s; }
.content tbody tr:hover { background: var(--bg-hover); }
.content tbody td { padding: 10px 14px; color: var(--text); vertical-align: top; }
.content tbody td strong { color: var(--text-head); }

/* code */
.content code { font-family: var(--font-mono); font-size: 12px; background: var(--code-bg);
  color: var(--accent); padding: 2px 6px; border-radius: 3px; border: 1px solid var(--border); }
.content pre { background: var(--code-bg); border: 1px solid var(--border); border-radius: 6px;
  padding: 16px 20px; overflow-x: auto; margin: 16px 0; }
.content pre code { background: none; border: none; padding: 0; color: var(--text); font-size: 13px; }

/* blockquote */
.content blockquote { border-left: 3px solid var(--accent-dim); margin: 20px 0;
  padding: 12px 20px; background: var(--bg-surface); color: var(--text-dim);
  font-style: italic; border-radius: 0 4px 4px 0; }
.content blockquote p { margin-bottom: 0; }

/* lists */
.content ul, .content ol { padding-left: 24px; margin-bottom: 14px; }
.content li { margin-bottom: 4px; }
.content input[type=checkbox] { margin-right: 6px; accent-color: var(--accent); }

/* hr */
.content hr { border: none; border-top: 1px solid var(--border); margin: 32px 0; }

/* footer */
.footer { margin-top: 64px; padding-top: 20px; border-top: 1px solid var(--border);
  font-size: 11px; color: var(--text-dim); letter-spacing: .04em; }

/* mobile */
@media (max-width: 768px) {
  .sidebar { position: fixed; left: -100%; z-index: 100; transition: left .25s; height: 100dvh; }
  .sidebar.open { left: 0; }
  .main { padding: 24px 20px; }
  .menu-toggle { display: flex; align-items: center; gap: 10px; position: fixed;
    top: 12px; left: 16px; z-index: 200; background: var(--bg-surface);
    border: 1px solid var(--border); border-radius: 6px; padding: 8px 12px;
    color: var(--accent); font-size: 12px; font-family: var(--font-body);
    cursor: pointer; letter-spacing: .08em; }
  .main { padding-top: 56px; }
  .portrait-wrap { float: none; width: 100%; margin: 0 0 24px 0; max-width: 280px; }
  .portrait-dual { width: 100%; flex-direction: column; gap: 12px; }
  .portrait-panel + .portrait-panel { margin-left: 0; }
}
@media (min-width: 769px) { .menu-toggle { display: none; } }
"""

# ── HTML template ──────────────────────────────────────────────────────────────

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{page_title} — Halden City Wiki</title>
  <style>{style}</style>
</head>
<body>
<button class="menu-toggle" onclick="toggleSidebar()">☰ MENU</button>
<div class="layout">
  <nav class="sidebar" id="sidebar">
    <div class="sidebar-header">
      <div class="sidebar-title">Halden City</div>
      <div class="sidebar-subtitle">World Wiki</div>
    </div>
    <div class="sidebar-nav">
      {sidebar_html}
    </div>
  </nav>
  <main class="main">
    {breadcrumb_html}
    <article class="content clearfix">
      {portrait_html}{content_html}
    </article>
    <div class="footer">Halden City Wiki &mdash; Last built {build_date}</div>
  </main>
</div>
<script>
function toggleSidebar() {{
  document.getElementById('sidebar').classList.toggle('open');
}}
document.addEventListener('click', function(e) {{
  var sidebar = document.getElementById('sidebar');
  var toggle  = document.querySelector('.menu-toggle');
  if (sidebar.classList.contains('open') &&
      !sidebar.contains(e.target) && !toggle.contains(e.target)) {{
    sidebar.classList.remove('open');
  }}
}});
</script>
</body>
</html>
"""

# ── Sidebar & breadcrumb ───────────────────────────────────────────────────────

def build_sidebar(nav, current_slug, pages):
    prefix = depth_prefix(current_slug)
    lines  = []

    is_home = current_slug == "index"
    cls  = "nav-home active" if is_home else "nav-home"
    href = "index.html" if is_home else prefix + "index.html"
    lines.append(f'<a href="{href}" class="{cls}">Home</a>')

    for cfg in SECTION_CONFIG:
        key = cfg["key"]
        if key not in nav or not nav[key]:
            continue
        is_pc    = key == "pcs"
        icon_cls = "nav-section-icon pc" if is_pc else "nav-section-icon"
        lines.append('<div class="nav-section">')
        lines.append(
            f'  <div class="nav-section-header">'
            f'<span class="{icon_cls}">{cfg["icon"]}</span>{cfg["label"]}</div>'
        )
        for item in nav[key]:
            slug   = item["slug"]
            active = " active" if slug == current_slug else ""
            pc_cls = " pc" if is_pc else ""
            link_href = prefix + slug + ".html"
            lines.append(
                f'  <a href="{link_href}" class="nav-link{pc_cls}{active}" '
                f'title="{item["title"]}">{item["title"]}</a>'
            )
        lines.append('</div>')

    return "\n".join(lines)


def build_breadcrumb(slug, pages):
    if slug == "index":
        return ""
    prefix = depth_prefix(slug)
    page   = pages.get(slug, {})
    label  = page.get("section_label", "")
    title  = page.get("title", slug)
    is_pc  = page.get("section_key") == "pcs"
    badge  = ' <span class="pc-badge">Player Character</span>' if is_pc else ""
    parts  = [f'<a href="{prefix}index.html">Home</a>']
    if label:
        parts.append(f'<span class="sep">/</span>{label}')
    parts.append(f'<span class="sep">/</span>{title}{badge}')
    return f'<div class="breadcrumb">{"".join(parts)}</div>'


# ── Build ──────────────────────────────────────────────────────────────────────

def write_page(slug, pages, nav, build_date):
    page     = pages[slug]
    md_text  = page["path"].read_text(encoding="utf-8")

    content_html    = render_markdown(md_text)
    sidebar_html    = build_sidebar(nav, slug, pages)
    breadcrumb_html = build_breadcrumb(slug, pages)
    prefix          = depth_prefix(slug)

    # Portrait injection for character sections only
    section_key = page.get("section_key")
    stem        = page.get("stem")
    p_html = ""
    if section_key in PORTRAIT_SECTIONS and stem:
        p_html = portrait_html(stem, page["title"], prefix)

    html = PAGE_TEMPLATE.format(
        page_title=page["title"],
        style=STYLE,
        sidebar_html=sidebar_html,
        breadcrumb_html=breadcrumb_html,
        portrait_html=p_html,
        content_html=content_html,
        build_date=build_date,
    )

    out_path = DOCS_DIR / (slug + ".html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    portrait_note = " [+portrait]" if p_html else ""
    print(f"  Built: {out_path.relative_to(REPO_ROOT)}{portrait_note}")


def main():
    build_date = datetime.utcnow().strftime("%B %Y")
    print(f"Building Halden City Wiki  →  {DOCS_DIR}\n")

    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    DOCS_DIR.mkdir()

    # Copy images before building pages
    copy_images()
    print()

    pages, nav = collect_pages()
    total_pages    = len(pages)
    total_sections = sum(1 for k in nav if nav[k])
    print(f"Found {total_pages} pages across {total_sections} sections\n")

    for slug in pages:
        write_page(slug, pages, nav, build_date)

    print(f"\nDone. {total_pages} pages written to docs/")


if __name__ == "__main__":
    main()
