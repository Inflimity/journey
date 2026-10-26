"""Build the deployable site into dist/.

    ~/Inflimity/sportcrawl/.venv/bin/python build.py --url https://your-domain.com

index.html is written body-first (it doubles as the Claude artifact preview), so
this script wraps it in a real <head> with the SEO, social and structured-data
tags, pre-renders the JS-built story cards so crawlers that don't run scripts
still read them, renders the favicon set and the share image with Playwright,
and writes robots.txt, sitemap.xml, site.webmanifest and llms.txt.

Re-run it whenever index.html changes or the domain changes; dist/ is disposable.
"""
import argparse, asyncio, datetime, html, json, re, shutil, struct
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
EMAIL = "bamideleminerva@gmail.com"
GITHUB = "https://github.com/Inflimity"
TITLE = "Bamidele Musibau · Full-Stack Engineer for Websites & Software"
DESC = ("Full-stack engineer building websites, custom software and security checks for small "
        "businesses in the US, UK, Canada and Europe. Fixed prices, clear plans.")
AREAS = ["United States", "United Kingdom", "Canada"]


def strip_head_bits(src: str) -> str:
    """Drop the tags that move into the real <head>."""
    src = re.sub(r"<title>.*?</title>\s*", "", src, count=1, flags=re.S)
    src = re.sub(r'<meta name="(claude:viewport-fit-sides|description)"[^>]*>\s*', "", src)
    src = re.sub(r'<link rel="(preconnect|stylesheet)" href="https://fonts\.[^"]*"[^>]*>\s*', "", src)
    return src


def faq_pairs(src: str):
    return [(html.unescape(q), html.unescape(a)) for q, a in
            re.findall(r"<details><summary>(.*?)</summary><p>(.*?)</p></details>", src)]


def skills(src: str):
    return re.findall(r'skills: \[([^\]]*)\]', src) and \
        [s for block in re.findall(r'skills: \[([^\]]*)\]', src) for s in re.findall(r'"([^"]+)"', block)]


def jsonld(url: str, src: str) -> str:
    person, org, site = f"{url}/#person", f"{url}/#inflimity", f"{url}/#website"
    areas = [{"@type": "Country", "name": a} for a in AREAS] + [{"@type": "Place", "name": "European Union"}]
    graph = [
        {"@type": "WebSite", "@id": site, "url": f"{url}/", "name": "Bamidele Musibau", "inLanguage": "en"},
        {"@type": "ProfilePage", "@id": f"{url}/#page", "url": f"{url}/", "name": TITLE, "description": DESC,
         "isPartOf": {"@id": site}, "mainEntity": {"@id": person}, "primaryImageOfPage": f"{url}/og.png",
         "dateModified": datetime.date.today().isoformat()},
        {"@type": "Person", "@id": person, "name": "Bamidele Musibau", "alternateName": "Inflimity", "url": f"{url}/", "jobTitle": "Full-Stack Engineer",
         "email": f"mailto:{EMAIL}", "sameAs": [GITHUB], "worksFor": {"@id": org},
         "alumniOf": {"@type": "CollegeOrUniversity", "name": "Oduduwa University"},
         "knowsAbout": skills(src)},
        {"@type": "ProfessionalService", "@id": org, "name": "Inflimity", "url": f"{url}/", "image": f"{url}/og.png",
         "founder": {"@id": person}, "foundingDate": "2019", "email": EMAIL, "areaServed": areas, "availableLanguage": "English",
         "description": "Websites, custom software and security checks for small and growing businesses, delivered remotely.",
         "hasOfferCatalog": {"@type": "OfferCatalog", "name": "Services", "itemListElement": [
             {"@type": "Offer", "itemOffered": {"@type": "Service", "name": "Website design and development",
              "description": "Fast, mobile-first websites with online booking, usually live in 7 to 10 days."}},
             {"@type": "Offer", "itemOffered": {"@type": "Service", "name": "Custom software",
              "description": "Client portals, dashboards, data pipelines and internal apps that replace manual processes."}},
             {"@type": "Offer", "itemOffered": {"@type": "Service", "name": "Security check",
              "description": "Review of a website or codebase against common attack paths, with a plain-English report."}}]}},
        {"@type": "FAQPage", "@id": f"{url}/#faq", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq_pairs(src)]},
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=1)


def head(url: str, src: str) -> str:
    e = html.escape
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(TITLE)}</title>
<meta name="description" content="{e(DESC)}">
<link rel="canonical" href="{url}/">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
<meta name="author" content="Bamidele Musibau (Inflimity)">
<meta name="theme-color" content="#0b0e16">
<meta name="color-scheme" content="dark">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Bamidele Musibau">
<meta property="og:locale" content="en_US">
<meta property="og:url" content="{url}/">
<meta property="og:title" content="{e(TITLE)}">
<meta property="og:description" content="{e(DESC)}">
<meta property="og:image" content="{url}/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Bamidele Musibau, full-stack engineer. A glowing branch grows from a seed.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(TITLE)}">
<meta name="twitter:description" content="{e(DESC)}">
<meta name="twitter:image" content="{url}/og.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://cdnjs.cloudflare.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght,SOFT,WONK@0,9..144,100..900,0..100,0..1;1,9..144,100..900,0..100,0..1&family=Cormorant+Garamond:ital,wght@0,500;1,400;1,500;1,600&family=Major+Mono+Display&family=JetBrains+Mono:wght@400;600&display=swap">
<style>[hidden]{{display:none!important}}img{{max-width:100%}}:root{{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}</style>
<script type="application/ld+json">
{jsonld(url, src)}
</script>
</head>
<body>
"""


def ico(pngs):
    """An .ico that embeds PNGs directly (supported by every current browser)."""
    out = struct.pack("<HHH", 0, 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    body = b""
    for size, data in pngs:
        out += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset)
        offset += len(data); body += data
    return out + body


async def render(url: str, src_body: str):
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        # pre-render the story cards and skill list
        pg = await b.new_page(viewport={"width": 1280, "height": 800})
        await pg.goto((ROOT / "index.html").as_uri()); await pg.wait_for_timeout(1500)
        grid = await pg.inner_html("#levelsGrid"); inv = await pg.inner_html("#inv")
        clean = lambda h: re.sub(r'\sstyle="[^"]*"', "", h)
        body = src_body.replace('<div class="grid b9" id="levelsGrid"></div>', f'<div class="grid b9" id="levelsGrid">{clean(grid)}</div>')
        body = body.replace('<div class="inv" id="inv"></div>', f'<div class="inv" id="inv">{clean(inv)}</div>')
        # favicon set
        svg = (ROOT / "assets/favicon.svg").read_text()
        pngs = {}
        for size in (16, 32, 48, 180, 192, 512):
            ip = await b.new_page(viewport={"width": size, "height": size})
            await ip.set_content(f'<html><body style="margin:0;background:transparent">{svg.replace("<svg ", f"<svg width=\"{size}\" height=\"{size}\" ", 1)}</body></html>')
            pngs[size] = await ip.screenshot(omit_background=True, clip={"x": 0, "y": 0, "width": size, "height": size})
            await ip.close()
        # share image
        op = await b.new_page(viewport={"width": 1200, "height": 630})
        await op.goto((ROOT / "assets/og.html").as_uri()); await op.wait_for_timeout(2500)
        og = await op.screenshot()
        await b.close()
    return body, pngs, og


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://YOUR-DOMAIN.com", help="the live site's address, no trailing slash")
    url = ap.parse_args().url.rstrip("/")
    src = (ROOT / "index.html").read_text()
    body, pngs, og = asyncio.run(render(url, strip_head_bits(src)))
    if DIST.exists(): shutil.rmtree(DIST)
    DIST.mkdir()
    (DIST / "index.html").write_text(head(url, src) + body + "\n</body>\n</html>\n")
    shutil.copy(ROOT / "assets/favicon.svg", DIST / "favicon.svg")
    (DIST / "favicon.ico").write_bytes(ico([(16, pngs[16]), (32, pngs[32]), (48, pngs[48])]))
    (DIST / "apple-touch-icon.png").write_bytes(pngs[180])
    (DIST / "icon-192.png").write_bytes(pngs[192]); (DIST / "icon-512.png").write_bytes(pngs[512])
    (DIST / "og.png").write_bytes(og)
    (DIST / "site.webmanifest").write_text(json.dumps({
        "name": "Bamidele Musibau", "short_name": "Bamidele", "start_url": "/", "display": "standalone",
        "background_color": "#0b0e16", "theme_color": "#0b0e16",
        "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}]}, indent=1))
    bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "PerplexityBot", "Google-Extended", "Applebot-Extended"]
    (DIST / "robots.txt").write_text("User-agent: *\nAllow: /\n\n# AI assistants are welcome to read and cite this site\n"
                                     + "".join(f"User-agent: {b}\nAllow: /\n\n" for b in bots) + f"Sitemap: {url}/sitemap.xml\n")
    (DIST / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                      f'  <url><loc>{url}/</loc><lastmod>{datetime.date.today().isoformat()}</lastmod></url>\n</urlset>\n')
    faq = "\n".join(f"- **{q}** {a}" for q, a in faq_pairs(src))
    (DIST / "llms.txt").write_text(f"""# Bamidele Musibau (Inflimity)

> Full-stack engineer, also known by his nickname Inflimity, building under that name since 2019. Builds websites, custom software and security checks for small and growing businesses, remotely, for clients in the US, UK, Canada and Europe.

## Services
- Website design and development: fast, mobile-first sites with online booking, usually live in 7 to 10 days.
- Custom software: client portals, dashboards, data pipelines and internal apps that replace spreadsheets and manual processes.
- Security checks: review of a website or codebase against common attack paths, with a plain-English report and fixes ranked by risk.

## Experience
- Independent practice (Inflimity), 2019 to 2023: more than fifty websites and internal tools delivered.
- B.Eng Computer Engineering, Oduduwa University, 2021 to 2025.
- OurPass, 2023: onsite engineer for POS payment terminals.
- Globus Bank, 2024: internship.
- LISH Consulting, 2025: Head of Technology, team of 10; API gateway connecting government websites and systems.
- Teaching data analysis and data science since December 2025.

## Selected client work
- ALZ Trust Limited: website for a corporate training firm whose clients include Coca-Cola, Nestlé, Guinness, First Bank and Dangote.
- McBeverly Hills Consulting: website for a learning and development firm.
- Glo Concept: corporate services platform.
- RHQ Services (Alberta, Canada): website for a heavy construction and mining company.
- TD Partners (Canada): client website.

## Products
- Canary: open-source benchmark testing AI coding agents on unseen bugs (90% on textbook bugs, 0% on real ones).
- Vultix: security SaaS (built the backend).
- Pathfinder: career roadmap platform (built the frontend).
- Analyser: spreadsheet profiler that runs entirely on the user's machine.
- SportCrawl: real-time sports data pipeline.

## FAQ
{faq}

## Contact
- Email: {EMAIL}
- GitHub: {GITHUB}
- Website: {url}/
""")
    print(f"built {DIST} for {url}")
    for f in sorted(DIST.iterdir()): print(f"  {f.name:22} {f.stat().st_size:>8} bytes")


if __name__ == "__main__":
    main()
