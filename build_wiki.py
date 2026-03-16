#!/usr/bin/env python3
"""
Halden City Wiki Builder
Converts markdown files into a navigatable GitHub Pages site.
"""

import os
import re
import shutil
import markdown
from pathlib import Path
from datetime import datetime

# ── Configuration ──────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent
DOCS_DIR = REPO_ROOT / "docs"

# Section config — supports both flat folders and subfolders.
# For subfolders, set "subfolder" to the path relative to REPO_ROOT.
# "folder" is the top-level directory (used for output path prefix).
SECTION_CONFIG = [
    {
        "key":      "pcs",
        "label":    "Player Characters",
        "icon":     "★",
        "folder":   "characters",
        "subfolder": "characters/pcs",
    },
    {
        "key":      "npcs",
        "label":    "Characters",
        "icon":     "◈",
        "folder":   "characters",
        "subfolder": "characters/npcs",
    },
    {
        "key":      "factions",
        "label":    "Factions",
        "icon":     "◉",
        "folder":   "factions",
        "subfolder": None,
    },
    {
        "key":      "locations",
        "label":    "Locations",
        "icon":     "◎",
        "folder":   "locations",
        "subfolder": None,
    },
    {
        "key":      "lore",
        "label":    "Lore",
        "icon":     "◇",
        "folder":   "lore",
        "subfolder": None,
    },
    {
        "key":      "plot",
        "label":    "Plot",
        "icon":     "◆",
        "folder":   "plot",
        "subfolder": None,
    },
    {
        "key":      "meta",
        "label":    "Meta",
        "icon":     "◌",
        "folder":   "meta",
        "subfolder": None,
    },
]

# ── Helpers ────────────────────────────────────────────────────────────────────

def page_title(path: Path) -> str:
    """Derive a display title from first H1 in file, or filename."""
    try:
        text = path.read_text(encoding="utf-8")
        m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if m:
            # Strip bold markers and quotes from title
            t = m.group(1).strip()
            t = re.sub(r"\*+", "", t)
            t = t.strip('"').strip("'")
            return t
    except Exception:
        pass
    name = path.stem.replace("-", " ").replace("_", " ")
    return name.title()

def collect_pages():
    """Walk the wiki directory and collect all content pages."""
    pages = {}   # slug -> {path, title, section_key, section_label, section_icon}
    nav = {}     # section_key -> [{slug, title}]

    # Homepage
    index_path = REPO_ROOT / "WIKI-INDEX.md"
    if index_path.exists():
        pages["index"] = {
            "path": index_path,
            "title": "Home",
            "section_key": None,
        }

    for cfg in SECTION_CONFIG:
        key = cfg["key"]
        source_dir = REPO_ROOT / (cfg["subfolder"] if cfg["subfolder"] else cfg["folder"])
        out_prefix = cfg["subfolder"] if cfg["subfolder"] else cfg["folder"]

        if not source_dir.is_dir():
            continue

        nav[key] = []
        for md_file in sorted(source_dir.glob("*.md")):
            if md_file.stem.startswith("_"):
                continue
            slug = out_prefix + "/" + md_file.stem
            title = page_title(md_file)
            pages[slug] = {
                "path": md_file,
                "title": title,
                "section_key": key,
                "section_label": cfg["label"],
                "section_icon": cfg["icon"],
            }
            nav[key].append({"slug": slug, "title": title})

    return pages, nav

def render_markdown(md_text: str) -> str:
    """Convert markdown to HTML."""
    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "attr_list", "def_list"],
    )
    return md.convert(md_text)

def depth_prefix(slug: str) -> str:
    """Return ../ prefix to reach docs root from this page's depth."""
    depth = slug.count("/")
    return "../" * depth

# ── HTML Template ──────────────────────────────────────────────────────────────

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
  --font-mono:  'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  --font-body:  'Inter', 'Segoe UI', system-ui, sans-serif;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

html, body {
  height: 100%;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-body);
  font-size: 15px;
  line-height: 1.7;
}

.layout {
  display: flex;
  min-height: 100vh;
}

/* ── Sidebar ── */
.sidebar {
  width: var(--sidebar-w);
  min-width: var(--sidebar-w);
  background: var(--bg-surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar-header {
  padding: 24px 20px 16px;
  border-bottom: 1px solid var(--border);
}

.sidebar-title {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent);
  line-height: 1.3;
}

.sidebar-subtitle {
  font-size: 11px;
  color: var(--text-dim);
  margin-top: 4px;
  letter-spacing: 0.04em;
}

.sidebar-nav {
  padding: 12px 0 24px;
  flex: 1;
}

.nav-home {
  display: block;
  padding: 8px 20px;
  color: var(--text-dim);
  text-decoration: none;
  font-size: 13px;
  letter-spacing: 0.03em;
  border-left: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
}

.nav-home:hover, .nav-home.active {
  color: var(--accent);
  border-left-color: var(--accent);
  background: var(--bg-hover);
}

.nav-section {
  margin-top: 16px;
}

.nav-section-header {
  padding: 6px 20px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-dim);
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-section-icon {
  color: var(--accent-dim);
  font-size: 12px;
}

.nav-section-icon.pc-icon {
  color: var(--accent-pc);
}

.nav-link {
  display: block;
  padding: 6px 20px 6px 28px;
  color: var(--text-dim);
  text-decoration: none;
  font-size: 13px;
  border-left: 2px solid transparent;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color 0.15s, background 0.15s, border-color 0.15s;
}

.nav-link:hover {
  color: var(--text);
  background: var(--bg-hover);
}

.nav-link.active {
  color: var(--accent);
  border-left-color: var(--accent);
  background: var(--bg-hover);
}

.nav-link.pc-link.active {
  color: var(--accent-pc);
  border-left-color: var(--accent-pc);
}

.nav-link.pc-link:hover {
  color: var(--accent-pc);
}

/* ── Main ── */
.main {
  flex: 1;
  min-width: 0;
  padding: 48px 64px;
  max-width: 900px;
}

.breadcrumb {
  font-size: 11px;
  color: var(--text-dim);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 32px;
}

.breadcrumb a {
  color: var(--text-dim);
  text-decoration: none;
}

.breadcrumb a:hover { color: var(--accent); }
.breadcrumb .sep { margin: 0 8px; }

/* ── PC badge ── */
.pc-badge {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent-pc);
  border: 1px solid var(--accent-pc);
  padding: 2px 8px;
  border-radius: 3px;
  margin-left: 12px;
  vertical-align: middle;
  opacity: 0.8;
}

/* ── Typography ── */
.content h1 {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-head);
  letter-spacing: -0.02em;
  margin-bottom: 8px;
  line-height: 1.2;
  border-bottom: 1px solid var(--border);
  padding-bottom: 16px;
}

.content h2 {
  font-size: 13px;
  font-weight: 700;
  color: var(--accent);
  letter-spacing: 0.1em;
  margin: 40px 0 12px;
  text-transform: uppercase;
}

.content h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-head);
  margin: 28px 0 8px;
}

.content h4 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-dim);
  margin: 20px 0 6px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.content p { margin-bottom: 14px; color: var(--text); }

.content a {
  color: var(--link);
  text-decoration: none;
  border-bottom: 1px solid var(--accent-dim);
  transition: color 0.15s, border-color 0.15s;
}

.content a:hover {
  color: var(--link-hover);
  border-bottom-color: var(--link-hover);
}

/* ── Tables ── */
.content table {
  width: 100%;
  border-collapse: collapse;
  margin: 20px 0;
  font-size: 13px;
}

.content thead th {
  text-align: left;
  padding: 10px 14px;
  background: var(--bg-surface);
  color: var(--accent);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  border-bottom: 1px solid var(--border);
}

.content tbody tr {
  border-bottom: 1px solid var(--border);
  transition: background 0.1s;
}

.content tbody tr:hover { background: var(--bg-hover); }

.content tbody td {
  padding: 10px 14px;
  color: var(--text);
  vertical-align: top;
}

.content tbody td strong { color: var(--text-head); }

/* ── Code ── */
.content code {
  font-family: var(--font-mono);
  font-size: 12px;
  background: var(--code-bg);
  color: var(--accent);
  padding: 2px 6px;
  border-radius: 3px;
  border: 1px solid var(--border);
}

.content pre {
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 16px 20px;
  overflow-x: auto;
  margin: 16px 0;
}

.content pre code {
  background: none;
  border: none;
  padding: 0;
  color: var(--text);
  font-size: 13px;
}

/* ── Blockquotes ── */
.content blockquote {
  border-left: 3px solid var(--accent-dim);
  margin: 20px 0;
  padding: 12px 20px;
  background: var(--bg-surface);
  color: var(--text-dim);
  font-style: italic;
  border-radius: 0 4px 4px 0;
}

.content blockquote p { margin-bottom: 0; }

/* ── Lists ── */
.content ul, .content ol { padding-left: 24px; margin-bottom: 14px; }
.content li { margin-bottom: 4px; }

/* ── Hr ── */
.content hr {
  border: none;
  border-top: 1px solid var(--border);
  margin: 32px 0;
}

/* ── Footer ── */
.footer {
  margin-top: 64px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
  font-size: 11px;
  color: var(--text-dim);
  letter-spacing: 0.04em;
}

/* ── Mobile ── */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: -100%;
    z-index: 100;
    transition: left 0.25s;
    height: 100dvh;
  }
  .sidebar.open { left: 0; }
  .main { padding: 24px 20px; }
  .menu-toggle {
    display: flex;
    align-items: center;
    gap: 10px;
    position: fixed;
    top: 12px;
    left: 16px;
    z-index: 200;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 8px 12px;
    color: var(--accent);
    font-size: 12px;
    font-family: var(--font-body);
    cursor: pointer;
    letter-spacing: 0.08em;
  }
  .main { padding-top: 56px; }
}

@media (min-width: 769px) {
  .menu-toggle { display: none; }
}
"""

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
    <article class="content">
      {content_html}
    </article>
    <div class="footer">
      Halden City Wiki &mdash; Last built {build_date}
    </div>
  </main>
</div>
<script>
function toggleSidebar() {{
  document.getElementById('sidebar').classList.toggle('open');
}}
document.addEventListener('click', function(e) {{
  const sidebar = document.getElementById('sidebar');
  const toggle = document.querySelector('.menu-toggle');
  if (sidebar.classList.contains('open') && !sidebar.contains(e.target) && !toggle.contains(e.target)) {{
    sidebar.classList.remove('open');
  }}
}});
</script>
</body>
</html>
"""

# ── Build functions ────────────────────────────────────────────────────────────

def build_sidebar(nav, current_slug, pages):
    lines = []

    is_home = current_slug == "index"
    home_class = "nav-home active" if is_home else "nav-home"
    prefix = depth_prefix(current_slug)
    home_href = "index.html" if is_home else prefix + "index.html"
    lines.append(f'<a href="{home_href}" class="{home_class}">Home</a>')

    for cfg in SECTION_CONFIG:
        key = cfg["key"]
        if key not in nav or not nav[key]:
            continue

        icon = cfg["icon"]
        label = cfg["label"]
        is_pc_section = key == "pcs"
        icon_class = "nav-section-icon pc-icon" if is_pc_section else "nav-section-icon"

        lines.append('<div class="nav-section">')
        lines.append(f'  <div class="nav-section-header"><span class="{icon_class}">{icon}</span>{label}</div>')

        for item in nav[key]:
            slug = item["slug"]
            title = item["title"]
            is_active = slug == current_slug
            link_extra = " pc-link" if is_pc_section else ""
            cls = f"nav-link{link_extra}{' active' if is_active else ''}"
            href = prefix + slug + ".html"
            lines.append(f'  <a href="{href}" class="{cls}" title="{title}">{title}</a>')

        lines.append('</div>')

    return "\n".join(lines)


def build_breadcrumb(slug, pages):
    if slug == "index":
        return ""
    prefix = depth_prefix(slug)
    page = pages.get(slug, {})
    section_label = page.get("section_label", "")
    title = page.get("title", slug)
    is_pc = page.get("section_key") == "pcs"

    badge = ' <span class="pc-badge">Player Character</span>' if is_pc else ""
    parts = [f'<a href="{prefix}index.html">Home</a>']
    if section_label:
        parts.append(f'<span class="sep">/</span>{section_label}')
    parts.append(f'<span class="sep">/</span>{title}{badge}')
    return f'<div class="breadcrumb">{"".join(parts)}</div>'


def write_page(slug, pages, nav, build_date):
    page = pages[slug]
    md_text = page["path"].read_text(encoding="utf-8")
    content_html = render_markdown(md_text)
    sidebar_html = build_sidebar(nav, slug, pages)
    breadcrumb_html = build_breadcrumb(slug, pages)

    html = PAGE_TEMPLATE.format(
        page_title=page["title"],
        style=STYLE,
        sidebar_html=sidebar_html,
        breadcrumb_html=breadcrumb_html,
        content_html=content_html,
        build_date=build_date,
    )

    out_path = DOCS_DIR / (slug + ".html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"  Built: {out_path.relative_to(REPO_ROOT)}")


def main():
    build_date = datetime.utcnow().strftime("%B %Y")
    print(f"Building Halden City Wiki → {DOCS_DIR}")

    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    DOCS_DIR.mkdir()

    pages, nav = collect_pages()
    print(f"Found {len(pages)} pages across {len([k for k in nav if nav[k]])} sections\n")

    for slug in pages:
        write_page(slug, pages, nav, build_date)

    print(f"\nDone. {len(pages)} pages written to docs/")


if __name__ == "__main__":
    main()
