#!/usr/bin/env python3
"""Split hash-based SPA index.html into multi-page site."""
from __future__ import annotations

import os
import re
from html import unescape
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
DOMAIN = "https://gflexipack.com"
BACKUP = ROOT / "index.spa.backup.html"

ROUTE_TO_FILE = {
    "/": INDEX,
    "/about": ROOT / "about" / "index.html",
    "/products": ROOT / "products" / "index.html",
    "/products/stand-up-pouches": ROOT / "products" / "stand-up-pouches" / "index.html",
    "/products/zipper-pouches": ROOT / "products" / "zipper-pouches" / "index.html",
    "/products/gusseted-pouches": ROOT / "products" / "gusseted-pouches" / "index.html",
    "/products/centre-seal-pouches": ROOT / "products" / "centre-seal-pouches" / "index.html",
    "/products/vacuum-pouches": ROOT / "products" / "vacuum-pouches" / "index.html",
    "/products/reusable-pouches": ROOT / "products" / "reusable-pouches" / "index.html",
    "/products/3-side-seal-pouches": ROOT / "products" / "3-side-seal-pouches" / "index.html",
    "/products/4-side-seal-bags": ROOT / "products" / "4-side-seal-bags" / "index.html",
    "/products/patch-handle-bags": ROOT / "products" / "patch-handle-bags" / "index.html",
    "/products/spout-pouches": ROOT / "products" / "spout-pouches" / "index.html",
    "/products/poly-film-rolls": ROOT / "products" / "poly-film-rolls" / "index.html",
    "/products/retort-pouches": ROOT / "products" / "retort-pouches" / "index.html",
    "/products/breathing-pouches": ROOT / "products" / "breathing-pouches" / "index.html",
    "/products/shape-pouches": ROOT / "products" / "shape-pouches" / "index.html",
    "/industries": ROOT / "industries" / "index.html",
    "/industries/food": ROOT / "industries" / "food" / "index.html",
    "/industries/beverages": ROOT / "industries" / "beverages" / "index.html",
    "/industries/pharmaceuticals": ROOT / "industries" / "pharmaceuticals" / "index.html",
    "/industries/personal-care": ROOT / "industries" / "personal-care" / "index.html",
    "/industries/agrochemical": ROOT / "industries" / "agrochemical" / "index.html",
    "/industries/household": ROOT / "industries" / "household" / "index.html",
    "/industries/industrial": ROOT / "industries" / "industrial" / "index.html",
    "/infrastructure": ROOT / "infrastructure" / "index.html",
    "/quality": ROOT / "quality" / "index.html",
    "/inquiry": ROOT / "inquiry" / "index.html",
}

MAIN_OPEN = re.compile(
    r'<main\s+class="view(?:\s+is-active)?"\s+data-route="([^"]+)"\s+data-title="([^"]*)"\s*>',
    re.I,
)


def route_to_url(route: str) -> str:
    if route == "/":
        return f"{DOMAIN}/"
    return f"{DOMAIN}{route}/"


def hash_href_to_path(href: str) -> str:
    if not href.startswith("#/"):
        return href
    path = href[1:]  # leading /
    if path in ("/", ""):
        return "/"
    return path.rstrip("/") + "/"


def rewrite_links(html: str) -> str:
    def repl(m: re.Match) -> str:
        attr, quote, val = m.group(1), m.group(2), m.group(3)
        if val.startswith("#/"):
            return f'{attr}={quote}{hash_href_to_path(val)}{quote}'
        return m.group(0)

    html = re.sub(r'(href)=(["\'])(#/[^"\']*)\2', repl, html)
    html = re.sub(r'href="style\.css"', 'href="/style.css"', html)
    html = re.sub(r'src="script\.js"', 'src="/script.js"', html)
    html = re.sub(r'src="images/', 'src="/images/', html)
    return html


def extract_mains(source: str) -> list[tuple[str, str, str, int, int]]:
    """Return list of (route, title, inner_html, start, end)."""
    matches = list(MAIN_OPEN.finditer(source))
    blocks = []
    for i, m in enumerate(matches):
        route, title = m.group(1), unescape(m.group(2))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else source.find("</main>", start)
        if end == -1:
            raise RuntimeError(f"Could not find end of main for route {route}")
        # find closing </main> for this block
        depth = 1
        pos = start
        while depth > 0 and pos < len(source):
            next_open = source.find("<main", pos)
            next_close = source.find("</main>", pos)
            if next_close == -1:
                break
            if next_open != -1 and next_open < next_close:
                depth += 1
                pos = next_open + 5
            else:
                depth -= 1
                if depth == 0:
                    end = next_close
                pos = next_close + 7
        inner = source[start:end].strip()
        blocks.append((route, title, inner, m.start(), end + len("</main>")))
    return blocks


def extract_inquiry_section(home_inner: str) -> str | None:
    m = re.search(
        r'(<!-- ============ INQUIRY ============ -->.*?</section>)\s*$',
        home_inner,
        re.S,
    )
    return m.group(1).strip() if m else None


def strip_inquiry_from_home(home_inner: str) -> str:
    return re.sub(
        r'\s*<!-- ============ INQUIRY ============ -->.*?</section>\s*$',
        "",
        home_inner,
        flags=re.S,
    ).strip()


def derive_description(title: str, main_inner: str) -> str:
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", main_inner, re.S | re.I)
    if h1:
        text = re.sub(r"<[^>]+>", "", h1.group(1))
        text = re.sub(r"\s+", " ", unescape(text)).strip()
        if text:
            return f"{text} — G Flexipack, flexible packaging manufacturer in Bharuch, Gujarat."
    base = title.split("—")[0].split("|")[0].strip()
    if base:
        return f"{base}. Custom flexible packaging from Bharuch, Gujarat — G Flexipack."
    return (
        "Custom-printed flexible packaging from Bharuch, Gujarat. "
        "Fourteen pouch formats, 9-colour rotogravure print, ISO 9001:2015."
    )


def build_head(title: str, description: str, canonical: str) -> str:
    return f"""  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%233b2a20'/%3E%3Ctext x='16' y='22' font-family='Georgia,serif' font-size='18' fill='%23f4efe7' text-anchor='middle'%3EG%3C/text%3E%3C/svg%3E">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="">
  <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Space+Grotesk:wght@400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/style.css">"""


NAV = """
  <header class="nav">
    <div class="nav-inner">
      <a class="brand" href="/" aria-label="G Flexipack, home"><img data-img="logo" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" alt="G Flexipack" loading="lazy"></a>
      <nav class="nav-links" aria-label="Primary">
        <a href="/about/" data-nav="/about">About</a>
        <a href="/products/" data-nav="/products">Products</a>
        <a href="/industries/" data-nav="/industries">Industries</a>
        <a href="/quality/" data-nav="/quality">Quality</a>
        <a href="/infrastructure/" data-nav="/infrastructure">Infrastructure</a>
      </nav>
      <div class="nav-actions" style="display:flex; align-items:center; gap:12px;">
        <a class="nav-cta nav-cta-secondary" href="/inquiry/" style="border-color:transparent; background:transparent; padding:10px 4px;">Talk to a packaging expert</a>
        <a class="nav-cta" href="/inquiry/">Get a quote <span class="arrow" aria-hidden="true">→</span></a>
      </div>
    </div>
    <div class="nav-progress" id="navProgress" aria-hidden="true"></div>
  </header>"""

FOOTER = """
  <footer class="site-footer">
    <div class="footer-inner">
      <div class="footer-brand"><img data-img="logo" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" alt="G Flexipack" loading="lazy"><p>Flexible packaging, made in Bharuch, Gujarat. ISO 9001:2015 certified, exporting to 10+ countries since 2016.</p></div>
      <div class="footer-col"><h5>Products</h5><ul>
        <li><a href="/products/stand-up-pouches/">Stand-Up Pouches</a></li>
        <li><a href="/products/spout-pouches/">Spout &amp; Zipper Pouches</a></li>
        <li><a href="/products/retort-pouches/">Retort &amp; Vacuum Pouches</a></li>
        <li><a href="/products/">All 14 formats →</a></li>
      </ul></div>
      <div class="footer-col"><h5>Company</h5><ul>
        <li><a href="/about/">About us</a></li>
        <li><a href="/industries/">Industries</a></li>
        <li><a href="/infrastructure/">Infrastructure</a></li>
        <li><a href="/quality/">Quality &amp; certifications</a></li>
      </ul></div>
      <div class="footer-col"><h5>Contact</h5><address>Plot 43, GIDC Phase-1, Narmada Nagar<br>Bharuch, Gujarat 392015<br>India<br><br><a href="mailto:info@gflexipack.com">info@gflexipack.com</a><br><a href="tel:+919824032765">+91 98240 32765</a></address></div>
    </div>
    <div class="footer-bottom"><p>© 2026 G Flexipack. All rights reserved.</p></div>
  </footer>"""


def build_page(route: str, title: str, main_inner: str) -> str:
    description = derive_description(title, main_inner)
    canonical = route_to_url(route)
    main_inner = rewrite_links(main_inner)
    main_tag = f'<main class="view is-active" data-route="{route}">\n    {main_inner}\n  </main>'
    return (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n"
        + build_head(title, description, canonical)
        + "\n\n</head>\n<body id=\"top\">\n"
        + NAV
        + "\n\n  "
        + main_tag
        + "\n"
        + FOOTER
        + "\n\n    <script src=\"/script.js\"></script>\n  \n</body>\n</html>\n"
    )


def write_htaccess() -> None:
  content = """# G Flexipack — clean URLs
DirectoryIndex index.html

<IfModule mod_rewrite.c>
  RewriteEngine On
  RewriteBase /

  # Trailing slash for extensionless paths (not files)
  RewriteCond %{REQUEST_FILENAME} !-f
  RewriteCond %{REQUEST_URI} !/$
  RewriteCond %{REQUEST_URI} !\\.
  RewriteRule ^(.+)$ /$1/ [R=301,L]

  # Serve index.html inside directories
  RewriteCond %{REQUEST_FILENAME} -d
  RewriteRule ^(.+[^/])$ /$1/ [R=301,L]
</IfModule>

ErrorDocument 404 /index.html
"""
  (ROOT / ".htaccess").write_text(content, encoding="utf-8")


def write_robots() -> None:
  (ROOT / "robots.txt").write_text(
    f"User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n",
    encoding="utf-8",
  )


def write_sitemap() -> None:
  urlset = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
  for route in sorted(ROUTE_TO_FILE.keys(), key=lambda r: (r.count("/"), r)):
    url = SubElement(urlset, "url")
    SubElement(url, "loc").text = route_to_url(route)
    SubElement(url, "changefreq").text = "monthly"
    priority = "1.0" if route == "/" else "0.8" if route.count("/") == 1 else "0.6"
    SubElement(url, "priority").text = priority
  xml = b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(urlset, encoding="utf-8")
  (ROOT / "sitemap.xml").write_text(xml.decode("utf-8"), encoding="utf-8")


def main() -> None:
  if not BACKUP.exists() and INDEX.exists():
    BACKUP.write_text(INDEX.read_text(encoding="utf-8"), encoding="utf-8")
  source_path = BACKUP if BACKUP.exists() else INDEX
  source = source_path.read_text(encoding="utf-8")

  blocks = extract_mains(source)
  by_route = {r: (t, inner) for r, t, inner, _s, _e in blocks}

  if "/" not in by_route:
    raise RuntimeError("Home route / not found")

  home_title, home_inner = by_route["/"]
  inquiry_html = extract_inquiry_section(home_inner)
  home_inner = strip_inquiry_from_home(home_inner)

  created: list[str] = []

  for route, out_path in ROUTE_TO_FILE.items():
    if route == "/inquiry":
      if not inquiry_html:
        raise RuntimeError("Inquiry section not found in home")
      title = "Get a Quote — Flexible Packaging Inquiry | G Flexipack"
      inner = inquiry_html
    elif route == "/":
      title, inner = home_title, home_inner
    else:
      if route not in by_route:
        raise RuntimeError(f"Missing route in source: {route}")
      title, inner = by_route[route]

    page = build_page(route, title, inner)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    created.append(str(out_path.relative_to(ROOT)))

  write_htaccess()
  write_robots()
  write_sitemap()

  print(f"Created/updated {len(created)} HTML pages:")
  for p in created:
    print(f"  - {p}")
  print("Also wrote: .htaccess, robots.txt, sitemap.xml")
  print(f"SPA backup: {BACKUP.name}")


if __name__ == "__main__":
  main()