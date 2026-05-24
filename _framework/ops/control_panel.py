# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Control panel — operator UI at localhost:9118/control-panel.

v0.1 ships a read-only view that surfaces:

  - Learning loop health  (top — central promise's status)
  - Per-profile cards     (which agents are present, their stats)
  - Recent events feed    (last 50 from events.db)
  - Audit summary         (last run, blocking finding count)

Interactive controls (pause/resume/run/clear) ship in v0.2 — they
depend on cron infrastructure the framework doesn't own directly.

Auth: v0.1 binds to localhost only (no remote access). v0.2 adds
email-OTP authentication for remote dashboards.

Start:
    agency panel    # or: python -m _framework.ops.control_panel
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    from aiohttp import web
except ImportError as e:  # pragma: no cover
    raise SystemExit(
        f"aiohttp not installed ({e}). Run `pip install aiohttp` or install with "
        "the framework's dependencies."
    )

from _framework.constants import (
    AGENCY_HOME,
    CONTROL_PANEL_PORT,
    DEPLOYMENT_YAML,
    PROFILES_DIR,
)
from _framework.manifest import validate


# ── Data fetchers ────────────────────────────────────────────────────────


def _learning_health() -> dict[str, Any]:
    """Read learning.db for the loop's current health."""
    out = {
        "rules_total": 0,
        "rules_captured_7d": 0,
        "recapture_events_7d_open": 0,
        "firings_24h": 0,
        "broken_skills": [],  # skill names with >3 rules, 0 firings in 30d
        "available": False,
    }
    try:
        from _framework.learning.learning_db import get_db, decode_json_col
    except Exception:
        return out

    try:
        db = get_db()
    except Exception:
        return out
    try:
        out["available"] = True
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        day_ago = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        thirty_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

        out["rules_total"] = int(db.execute(
            "SELECT COUNT(*) AS n FROM learning_rules WHERE status='active'"
        ).fetchone()["n"])
        out["rules_captured_7d"] = int(db.execute(
            "SELECT COUNT(*) AS n FROM learning_rules WHERE created_at >= ? AND status='active'",
            (week_ago,),
        ).fetchone()["n"])
        out["recapture_events_7d_open"] = int(db.execute(
            "SELECT COUNT(*) AS n FROM recapture_events "
            "WHERE detected_at >= ? AND dismissed=0",
            (week_ago,),
        ).fetchone()["n"])
        out["firings_24h"] = int(db.execute(
            "SELECT COUNT(*) AS n FROM firings WHERE created_at >= ?",
            (day_ago,),
        ).fetchone()["n"])

        # Broken-loop skills
        rules_rows = db.execute("SELECT skill_tags FROM learning_rules WHERE status='active'").fetchall()
        skill_rule_count: dict[str, int] = {}
        for r in rules_rows:
            for tag in decode_json_col(r["skill_tags"]):
                if tag == "general":
                    continue
                skill_rule_count[tag] = skill_rule_count.get(tag, 0) + 1
        active_skills_rows = db.execute(
            "SELECT DISTINCT skill_tag FROM firings WHERE created_at >= ?",
            (thirty_ago,),
        ).fetchall()
        active_skills = {r["skill_tag"] for r in active_skills_rows}
        broken = [
            (skill, n) for skill, n in skill_rule_count.items()
            if n > 3 and skill not in active_skills
        ]
        broken.sort(key=lambda x: -x[1])
        out["broken_skills"] = broken[:10]
    finally:
        db.close()
    return out


def _profiles_overview() -> list[dict[str, Any]]:
    """Enumerate profiles on disk + a few stats per profile."""
    out: list[dict[str, Any]] = []
    if not PROFILES_DIR.exists():
        return out
    for p in sorted(PROFILES_DIR.iterdir()):
        if not p.is_dir():
            continue
        role_file = p / "role.txt"
        role = role_file.read_text(encoding="utf-8", errors="replace").strip() if role_file.exists() else "?"
        n_skills = len(list((p / "skills").glob("*"))) if (p / "skills").exists() else 0
        n_scripts = len(list((p / "scripts").glob("*.py"))) if (p / "scripts").exists() else 0
        out.append({
            "id": p.name,
            "role": role,
            "skills": n_skills,
            "scripts": n_scripts,
            "has_soul": (p / "SOUL.md").exists(),
            "has_standards": (p / "standards.md").exists(),
        })
    return out


def _recent_events(limit: int = 50) -> list[dict[str, Any]]:
    try:
        from _framework.sentinel import recent_events
        return recent_events(limit=limit, minutes=60 * 24)
    except Exception:
        return []


def _manifest_state() -> dict[str, Any]:
    if not DEPLOYMENT_YAML.exists():
        return {"present": False}
    result = validate(DEPLOYMENT_YAML)
    return {
        "present": True,
        "ok": result.ok,
        "errors": len(result.errors),
        "warnings": len(result.warnings),
    }


# ── Handlers ─────────────────────────────────────────────────────────────


async def _handle_root(_req: web.Request) -> web.Response:
    return web.Response(text=_render_html(), content_type="text/html")


async def _handle_data(_req: web.Request) -> web.Response:
    payload = {
        "agency_home": str(AGENCY_HOME),
        "manifest": _manifest_state(),
        "learning": _learning_health(),
        "profiles": _profiles_overview(),
        "events": _recent_events(50),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return web.json_response(payload)


def _render_html() -> str:
    return """<!doctype html>
<html lang=en>
<head>
  <meta charset=utf-8>
  <title>HermesAgency — Control Panel</title>
  <style>
    :root { --bg:#0f1115; --fg:#e6e6e6; --muted:#888; --warn:#e6a23c;
            --crit:#e64a3c; --ok:#5fa34f; --card:#1a1d24; --border:#2a2d34; }
    * { box-sizing: border-box; }
    body { background: var(--bg); color: var(--fg); font-family: -apple-system, sans-serif;
           margin: 0; padding: 24px; line-height: 1.5; }
    h1 { font-weight: 600; margin: 0 0 8px 0; }
    .sub { color: var(--muted); font-size: 14px; margin-bottom: 24px; }
    .grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
    .card { background: var(--card); border: 1px solid var(--border); border-radius: 8px;
            padding: 16px; }
    .card h2 { margin: 0 0 12px 0; font-size: 14px; font-weight: 600; text-transform: uppercase;
               letter-spacing: 0.06em; color: var(--muted); }
    .big { font-size: 28px; font-weight: 700; }
    .row { display: flex; gap: 12px; align-items: baseline; }
    .label { color: var(--muted); font-size: 12px; }
    .warn { color: var(--warn); }
    .crit { color: var(--crit); }
    .ok { color: var(--ok); }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    td, th { padding: 6px 8px; text-align: left; border-bottom: 1px solid var(--border); }
    .feed td { font-family: ui-monospace, monospace; font-size: 12px; }
    .badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;
             text-transform: uppercase; letter-spacing: 0.05em; }
    .b-info { background: #2a2d34; color: var(--muted); }
    .b-warn { background: #4a3a1a; color: var(--warn); }
    .b-crit { background: #4a1a1a; color: var(--crit); }
    .b-ok   { background: #1a4a2a; color: var(--ok); }
    a, a:visited { color: #6aa3ff; }
    footer { margin-top: 32px; color: var(--muted); font-size: 12px; }
  </style>
</head>
<body>
  <h1>HermesAgency — control panel</h1>
  <div class="sub" id="generated_at">loading…</div>

  <h2 id="learning-loop-header">Learning loop health</h2>
  <div class="grid">
    <div class="card">
      <h2>Rules captured (7d)</h2>
      <div class="big" id="rules_7d">—</div>
      <div class="label">of <span id="rules_total">—</span> active total</div>
    </div>
    <div class="card">
      <h2>Recapture events (7d, open)</h2>
      <div class="big" id="recapture_7d">—</div>
      <div class="label">each is a system-failure flag</div>
    </div>
    <div class="card">
      <h2>Firings (24h)</h2>
      <div class="big" id="firings_24h">—</div>
      <div class="label">rules influencing decisions</div>
    </div>
    <div class="card">
      <h2>Skills with broken loop</h2>
      <div class="big" id="broken_count">—</div>
      <div class="label">&gt;3 rules, 0 firings in 30d</div>
      <div id="broken_list" style="margin-top:8px;font-size:12px"></div>
    </div>
  </div>

  <h2 style="margin-top:32px">Profiles</h2>
  <div class="card">
    <table id="profiles-table">
      <thead><tr><th>ID</th><th>Role</th><th>Skills</th><th>Scripts</th><th>SOUL</th><th>standards</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>

  <h2 style="margin-top:32px">Recent events</h2>
  <div class="card">
    <table class="feed">
      <thead><tr><th>When</th><th>Severity</th><th>Kind</th><th>Actor</th><th>Target</th></tr></thead>
      <tbody id="events-tbody"></tbody>
    </table>
  </div>

  <footer>
    HermesAgency v0.1 control panel.
    Read-only in v0.1; interactive controls ship in v0.2.
    Auto-refreshes every 10s.
  </footer>

  <script>
    function badge(sev) {
      const cls = sev === 'critical' ? 'b-crit' :
                  sev === 'warn'     ? 'b-warn' :
                  sev === 'info'     ? 'b-info' : 'b-info';
      return '<span class="badge ' + cls + '">' + (sev || 'info') + '</span>';
    }
    async function tick() {
      try {
        const r = await fetch('/control-panel/data');
        const j = await r.json();
        document.getElementById('generated_at').textContent =
          'AGENCY_HOME: ' + j.agency_home + ' · last refresh ' + j.generated_at;

        const L = j.learning;
        document.getElementById('rules_7d').textContent = L.rules_captured_7d;
        document.getElementById('rules_total').textContent = L.rules_total;
        const rec = document.getElementById('recapture_7d');
        rec.textContent = L.recapture_events_7d_open;
        rec.className = (L.recapture_events_7d_open > 0) ? 'big crit' : 'big ok';
        document.getElementById('firings_24h').textContent = L.firings_24h;
        document.getElementById('broken_count').textContent = L.broken_skills.length;
        document.getElementById('broken_list').innerHTML =
          L.broken_skills.map(s => s[0] + ' (' + s[1] + ' rules)').join('<br>') || '—';

        const tbody = document.querySelector('#profiles-table tbody');
        tbody.innerHTML = j.profiles.map(p =>
          '<tr><td>' + p.id + '</td><td>' + p.role + '</td>' +
          '<td>' + p.skills + '</td><td>' + p.scripts + '</td>' +
          '<td>' + (p.has_soul ? '✓' : '<span class=crit>missing</span>') + '</td>' +
          '<td>' + (p.has_standards ? '✓' : '<span class=warn>missing</span>') + '</td></tr>'
        ).join('');

        const eb = document.getElementById('events-tbody');
        eb.innerHTML = j.events.map(e =>
          '<tr><td>' + e.ts.slice(11,19) + '</td>' +
          '<td>' + badge(e.severity) + '</td>' +
          '<td>' + e.kind + '</td>' +
          '<td>' + (e.actor || '-') + '</td>' +
          '<td>' + (e.target || '-') + '</td></tr>'
        ).join('') || '<tr><td colspan=5 class="label">no events yet</td></tr>';
      } catch (e) {
        document.getElementById('generated_at').textContent = 'fetch failed: ' + e;
      }
    }
    tick();
    setInterval(tick, 10000);
  </script>
</body>
</html>"""


# ── Server ───────────────────────────────────────────────────────────────


def build_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/control-panel", _handle_root)
    app.router.add_get("/control-panel/data", _handle_data)
    app.router.add_get("/", _handle_root)  # convenience
    return app


def main() -> int:
    """Run the control panel on localhost:9118."""
    import argparse
    p = argparse.ArgumentParser(description="HermesAgency control panel")
    p.add_argument("--port", type=int, default=CONTROL_PANEL_PORT)
    p.add_argument("--host", default="127.0.0.1",
                   help="Bind address (v0.1: localhost only by default)")
    args = p.parse_args()

    app = build_app()
    print(f"HermesAgency control panel on http://{args.host}:{args.port}/control-panel")
    print(f"  AGENCY_HOME: {AGENCY_HOME}")
    print("  Read-only in v0.1; Ctrl-C to stop.")
    web.run_app(app, host=args.host, port=args.port, print=None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["build_app", "main"]
