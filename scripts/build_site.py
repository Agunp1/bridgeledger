"""Build the public website (GitHub Pages) from the single app file.

    python scripts/build_site.py

Reads web/index.html (the same file published as the Claude link) and writes:
  docs/index.html   full HTML document with the login library and config loaded
  docs/market.json  the built-in market data snapshot (the weekly refresh updates it)
  docs/config.js    Supabase settings; created once as a template, never overwritten
  docs/.nojekyll    serve files as-is
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "web" / "index.html"
OUT = ROOT / "docs"
SUPABASE_JS = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.117.2/dist/umd/supabase.js"

RESET = """<style>
*,*::before,*::after{box-sizing:border-box}
html{color-scheme:light}
:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
body{margin:0}
img{max-width:100%}
[hidden]{display:none!important}
</style>"""

CONFIG_TEMPLATE = """// BridgeLedger website settings.
// Paste your Supabase Project URL and anon public key below (Supabase: Project Settings -> API).
// The anon key is meant to be public: the database rules in supabase/schema.sql
// make sure each signed-in person can only read and change their own plan.
window.BRIDGE_SITE = {
  supabaseUrl: "",
  supabaseAnonKey: ""
};
"""


def market_snapshot(html: str) -> dict:
    script = html.split("<script>", 1)[1].split("</script>", 1)[0]
    match = re.search(r"const MARKET_SNAPSHOT = (\{[\s\S]*?\n\});", script)
    if not match:
        raise SystemExit("MARKET_SNAPSHOT not found in web/index.html")
    out = subprocess.run(["node", "-e", f"process.stdout.write(JSON.stringify({match.group(1)}))"],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def build() -> None:
    html = SRC.read_text(encoding="utf-8")
    head, body = html.split('<div class="wrap">', 1)
    body = '<div class="wrap">' + body
    main_script = "<script>\n/* =================== planning engine"
    if main_script not in body:
        raise SystemExit("Main script marker not found")
    body = body.replace(main_script,
                        f'<script src="config.js"></script>\n<script src="{SUPABASE_JS}"></script>\n' + main_script, 1)
    doc = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
           "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">\n"
           "<meta name=\"description\" content=\"Personal finance discipline for money in two countries: debts, goals, an investment advisor and monthly check-ins.\">\n"
           f"{RESET}\n{head.strip()}\n</head>\n<body>\n{body.strip()}\n</body>\n</html>\n")
    OUT.mkdir(exist_ok=True)
    (OUT / "index.html").write_text(doc, encoding="utf-8")
    market = OUT / "market.json"
    if not market.exists() or json.loads(market.read_text())["as_of"] < market_snapshot(html)["as_of"]:
        market.write_text(json.dumps(market_snapshot(html), indent=1, ensure_ascii=False), encoding="utf-8")
    config = OUT / "config.js"
    if not config.exists():
        config.write_text(CONFIG_TEMPLATE, encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Built {OUT / 'index.html'} ({len(doc):,} bytes)")


if __name__ == "__main__":
    build()
