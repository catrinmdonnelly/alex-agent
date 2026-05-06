"""
Alex — weekly SEO agent.

Runs once a week (default Wednesday 10:00 UK) and writes a weekly SEO report.
Alex pulls Google Search Console for the last 7 days, compares against the
previous 7, finds rising queries, declining pages, ranking opportunities,
and writes the report. He also drafts content briefs and outreach targets
for review.

Pipeline:
  1. Pull GSC data (last 7 days vs previous 7 days)
  2. Read optional weekly direction from a strategy agent
  3. Ask Claude (with web search) to produce the analysis
  4. Write seo-reports/YYYY-MM-DD.md     — full report
  5. Write blog-briefs/YYYY-MM-DD.md     — content briefs ready to draft
  6. Write outreach-targets/YYYY-MM-DD.md — backlink and forum targets
  7. Write exchange/seo-trends-latest.md  — trend findings for downstream agents
  8. Write exchange/seo-report-latest.md  — short summary for upstream agents
  9. Write reports/alex-<timestamp>.json  — Station inbox JSON
 10. Email on failure

Exit code 0 on success, 1 on any step failing.
"""

from __future__ import annotations

import json
import os
import re
import smtplib
import sys
import tempfile
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).parent
CONFIG = ROOT / "config"
EXCHANGE = ROOT / "exchange"
SEO_REPORTS = ROOT / "seo-reports"
BLOG_BRIEFS = ROOT / "blog-briefs"
OUTREACH = ROOT / "outreach-targets"
LOGS = ROOT / "logs"
REPORTS = ROOT / "reports"

TIMEZONE = ZoneInfo(os.environ.get("AGENT_TIMEZONE", "Europe/London"))
GSC_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


# ─── Helpers ───────────────────────────────────────────────────────────────────

def env(name: str, required: bool = True, default: str = "") -> str:
    val = os.environ.get(name, default)
    if required and not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


def now_local() -> datetime:
    return datetime.now(TIMEZONE)


def today_key() -> str:
    return now_local().strftime("%Y-%m-%d")


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def read_if_exists(path: Path, fallback: str = "") -> str:
    return path.read_text() if path.exists() else fallback


# ─── GSC pull ──────────────────────────────────────────────────────────────────

def _gsc_credentials_path() -> Path:
    """
    Resolve GSC service account credentials.

    Order of precedence:
      1. GSC_CREDENTIALS_JSON env var — full JSON content (used in CI)
      2. config/gsc-credentials.json (local only, do not commit)
    """
    raw = os.environ.get("GSC_CREDENTIALS_JSON", "").strip()
    if raw:
        tmp = Path(tempfile.gettempdir()) / "alex-gsc-credentials.json"
        tmp.write_text(raw)
        return tmp
    candidate = CONFIG / "gsc-credentials.json"
    if candidate.exists():
        return candidate
    raise RuntimeError(
        "No GSC credentials found. Either set the GSC_CREDENTIALS_JSON secret "
        "(recommended for GitHub Actions) or place gsc-credentials.json in the "
        "config/ folder for local runs. See SETUP.md for the full guide."
    )


def _gsc_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_path = _gsc_credentials_path()
    credentials = service_account.Credentials.from_service_account_file(
        str(creds_path), scopes=GSC_SCOPES
    )
    return build("searchconsole", "v1", credentials=credentials)


def _gsc_query(service, site_url: str, start: str, end: str, dims: list[str], limit: int = 100) -> list[dict]:
    response = (
        service.searchanalytics()
        .query(siteUrl=site_url, body={
            "startDate": start,
            "endDate": end,
            "dimensions": dims,
            "rowLimit": limit,
        })
        .execute()
    )
    out = []
    for row in response.get("rows", []):
        r = {
            "clicks": row["clicks"],
            "impressions": row["impressions"],
            "ctr": round(row["ctr"] * 100, 2),
            "position": round(row["position"], 1),
        }
        for i, d in enumerate(dims):
            r[d] = row["keys"][i]
        out.append(r)
    return out


def _compare(current: list[dict], previous: list[dict], key: str) -> list[dict]:
    prev_map = {r[key]: r for r in previous}
    movers = []
    for r in current:
        p = prev_map.get(r[key])
        if p:
            movers.append({
                **r,
                "pos_change": round(p["position"] - r["position"], 1),
                "click_change": r["clicks"] - p["clicks"],
                "imp_change": r["impressions"] - p["impressions"],
                "is_new": False,
            })
        else:
            movers.append({
                **r,
                "pos_change": 0.0,
                "click_change": r["clicks"],
                "imp_change": r["impressions"],
                "is_new": True,
            })
    return movers


def pull_gsc() -> dict:
    """Pull the data Alex needs to reason about the week. Returns a dict."""
    site_url = env("GSC_SITE_URL")
    log(f"gsc: connecting to {site_url}")
    service = _gsc_service()

    today = datetime.now()
    end_cur = (today - timedelta(days=3)).strftime("%Y-%m-%d")
    start_cur = (today - timedelta(days=10)).strftime("%Y-%m-%d")
    end_prev = (today - timedelta(days=10)).strftime("%Y-%m-%d")
    start_prev = (today - timedelta(days=17)).strftime("%Y-%m-%d")

    log(f"  current:  {start_cur} → {end_cur}")
    log(f"  previous: {start_prev} → {end_prev}")

    current_kw = _gsc_query(service, site_url, start_cur, end_cur, ["query"], 100)
    prev_kw = _gsc_query(service, site_url, start_prev, end_prev, ["query"], 100)
    pages = _gsc_query(service, site_url, start_cur, end_cur, ["page"], 30)
    kw_page = _gsc_query(service, site_url, start_cur, end_cur, ["query", "page"], 40)
    devices = _gsc_query(service, site_url, start_cur, end_cur, ["device"], 10)
    daily = sorted(
        _gsc_query(service, site_url, start_cur, end_cur, ["date"], 10),
        key=lambda r: r["date"],
    )

    comparison = _compare(current_kw, prev_kw, "query")
    striking = sorted(
        [r for r in comparison if 5 <= r["position"] <= 20],
        key=lambda r: r["impressions"],
        reverse=True,
    )[:12]
    ctr_gaps = sorted(
        [r for r in comparison if r["impressions"] >= 5 and r["ctr"] < 3.0],
        key=lambda r: r["impressions"],
        reverse=True,
    )[:10]
    movers = sorted(
        [r for r in comparison if not r["is_new"] and abs(r["pos_change"]) >= 2],
        key=lambda r: abs(r["pos_change"]),
        reverse=True,
    )[:10]
    new_queries = [r for r in comparison if r["is_new"]][:15]

    total_clicks_cur = sum(r["clicks"] for r in current_kw)
    total_clicks_prev = sum(r["clicks"] for r in prev_kw)
    total_imp_cur = sum(r["impressions"] for r in current_kw)
    total_imp_prev = sum(r["impressions"] for r in prev_kw)

    return {
        "site_url": site_url,
        "window": {
            "current": {"start": start_cur, "end": end_cur},
            "previous": {"start": start_prev, "end": end_prev},
        },
        "totals": {
            "clicks": total_clicks_cur,
            "clicks_prev": total_clicks_prev,
            "click_delta": total_clicks_cur - total_clicks_prev,
            "impressions": total_imp_cur,
            "impressions_prev": total_imp_prev,
            "imp_delta": total_imp_cur - total_imp_prev,
        },
        "top_keywords": sorted(comparison, key=lambda r: r["impressions"], reverse=True)[:20],
        "striking_distance": striking,
        "ctr_gaps": ctr_gaps,
        "movers": movers,
        "new_queries": new_queries,
        "pages": pages[:15],
        "keyword_pages": kw_page[:25],
        "devices": devices,
        "daily": daily,
    }


# ─── Claude call ───────────────────────────────────────────────────────────────

DEFAULT_SYSTEM_PROMPT = """You are Alex, an SEO analyst.

You run every week. You produce one weekly SEO report and tight trend notes any downstream content agent can read.

Your tone is direct and specific. You make sharp calls. You never pad. You never recommend something generic. Every recommendation must be specific enough to act on tomorrow. You avoid em dashes entirely. No staccato fragments. No corporate language.

You have access to a web_search tool. Use it liberally to:
  - Check what similar brands are ranking for in this niche
  - Find Reddit, forum and community threads where the business could plausibly be mentioned
  - Spot Google autocomplete and "People also ask" queries around the topics that matter
  - Identify directories and gift-guide pages where the business might earn a backlink
  - Confirm any keyword is actually being searched before recommending it

Hard rules on outreach:
  - Drafts must sound like a real person, not an ad. Genuinely helpful first, business mention second. Short (two to three sentences).
  - Match community tone: Reddit casual, Mumsnet direct, niche forums match their conventions.
  - Don't post anywhere the brand context says is off-limits.

When you produce output, return ONE JSON object matching this schema exactly. No prose, no code fences:

{
  "gsc_summary": "2-3 sentence plain-English summary of the week's GSC numbers — what went up, what went down, what it means.",
  "what_to_celebrate": ["short bullet", ...],
  "what_to_worry_about": ["short bullet", ...],
  "keyword_opportunities": [
    {"keyword": "...", "why_it_matters": "...", "action": "...", "intent": "informational|transactional|navigational"}
  ],
  "striking_distance_plays": [
    {"keyword": "...", "current_position": 7.3, "recommended_move": "..."}
  ],
  "ctr_gap_fixes": [
    {"page": "/path", "current_meta_title": "...", "suggested_meta_title": "...", "current_meta_description": "...", "suggested_meta_description": "...", "why": "..."}
  ],
  "website_amendments": [
    {"location": "page or section", "current": "...", "suggested": "...", "why": "..."}
  ],
  "backlink_opportunities": [
    {"url": "https://...", "why_relevant": "...", "suggested_approach": "..."}
  ],
  "reddit_forum_threads": [
    {"url": "https://...", "summary": "what they're asking, one line", "draft_response": "two to three real sentences, no em dashes"}
  ],
  "trend_findings": [
    {"topic": "...", "angle": "specific story angle", "why_now": "search or cultural evidence"}
  ],
  "quick_wins": ["each under 15 minutes to action", ...]
}

Aim for 3-5 items in each list. Quality over volume. Every item should be specific and actionable, not generic.
"""


def load_system_prompt() -> str:
    custom = read_if_exists(CONFIG / "system-prompt.md", "")
    return custom.strip() if custom.strip() else DEFAULT_SYSTEM_PROMPT


def ask_claude(gsc: dict, direction: str, recent_trends: str) -> dict:
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed — run: pip install -r requirements.txt")

    brand = read_if_exists(CONFIG / "brand-voice.md",
                           "(brand-voice.md missing — fill in config/brand-voice.md to make recommendations match your tone)")[:4000]
    state = read_if_exists(CONFIG / "state.md",
                           "(state.md missing — fill in config/state.md so Alex understands current priorities)")[:4000]

    gsc_compact = json.dumps({
        "window": gsc["window"],
        "totals": gsc["totals"],
        "top_keywords": gsc["top_keywords"][:15],
        "striking_distance": gsc["striking_distance"][:10],
        "ctr_gaps": gsc["ctr_gaps"][:10],
        "movers": gsc["movers"][:10],
        "new_queries": gsc["new_queries"][:10],
        "pages": gsc["pages"][:10],
        "keyword_pages": gsc["keyword_pages"][:15],
        "daily": gsc["daily"],
    }, indent=2)

    user_message = f"""Today is {now_local().strftime('%A %d %B %Y')}.
Site: {gsc['site_url']}.

BRAND (condensed):
{brand}

BUSINESS STATE:
{state}

WEEKLY DIRECTION (from your strategy agent, if any — align SEO priorities with this):
{direction}

PREVIOUS WEEK'S TREND FINDINGS YOU POSTED (avoid repeating the same angles):
{recent_trends}

GSC DATA (pre-processed):
{gsc_compact}

Produce your weekly report as one JSON object. Use web_search when it would meaningfully improve a recommendation. Return JSON only."""

    client = anthropic.Anthropic(api_key=env("ANTHROPIC_API_KEY"))

    model = env("ANTHROPIC_MODEL", required=False, default="claude-sonnet-4-6")
    log(f"claude: calling {model} with web_search enabled")
    resp = client.messages.create(
        model=model,
        max_tokens=8000,
        system=load_system_prompt(),
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 8,
        }],
        messages=[{"role": "user", "content": user_message}],
    )

    text_parts: list[str] = []
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            text_parts.append(block.text)
    text = "".join(text_parts).strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise RuntimeError(f"Claude did not return valid JSON: {e}\n---\n{text[:1000]}")


# ─── Render ────────────────────────────────────────────────────────────────────

def render_full_report(analysis: dict, gsc: dict, business_name: str) -> str:
    out: list[str] = []
    date = today_key()
    out.append(f"# {business_name} — SEO week of {date}\n")
    out.append(f"*Alex. Window: {gsc['window']['current']['start']} → {gsc['window']['current']['end']}.*\n")

    t = gsc["totals"]
    click_sign = "+" if t["click_delta"] >= 0 else ""
    imp_sign = "+" if t["imp_delta"] >= 0 else ""
    out.append("## GSC dashboard\n")
    out.append("| Metric | This week | Previous | Change |")
    out.append("|--------|-----------|----------|--------|")
    out.append(f"| Clicks | {t['clicks']} | {t['clicks_prev']} | {click_sign}{t['click_delta']} |")
    out.append(f"| Impressions | {t['impressions']} | {t['impressions_prev']} | {imp_sign}{t['imp_delta']} |")
    out.append("")
    out.append(f"**Summary:** {analysis.get('gsc_summary', '')}\n")

    if analysis.get("what_to_celebrate"):
        out.append("### What to celebrate")
        out.extend(f"- {b}" for b in analysis["what_to_celebrate"])
        out.append("")

    if analysis.get("what_to_worry_about"):
        out.append("### What to worry about")
        out.extend(f"- {b}" for b in analysis["what_to_worry_about"])
        out.append("")

    out.append("## Top keywords (by impressions)\n")
    out.append("| Keyword | Clicks | Impressions | CTR | Position | Δ pos |")
    out.append("|---------|--------|-------------|-----|----------|-------|")
    for r in gsc["top_keywords"][:12]:
        flag = " (new)" if r.get("is_new") else ""
        pos_str = f"+{r['pos_change']}" if r["pos_change"] > 0 else str(r["pos_change"])
        out.append(f"| {r['query']}{flag} | {r['clicks']} | {r['impressions']} | {r['ctr']}% | {r['position']} | {pos_str} |")
    out.append("")

    if gsc["new_queries"]:
        out.append("## New queries this week\n")
        out.append("| Keyword | Impressions | Position |")
        out.append("|---------|-------------|----------|")
        for r in gsc["new_queries"][:10]:
            out.append(f"| {r['query']} | {r['impressions']} | {r['position']} |")
        out.append("")

    if analysis.get("keyword_opportunities"):
        out.append("## Keyword opportunities\n")
        out.append("| Keyword | Intent | Why it matters | Action |")
        out.append("|---------|--------|----------------|--------|")
        for k in analysis["keyword_opportunities"]:
            out.append(f"| {k.get('keyword','')} | {k.get('intent','')} | {k.get('why_it_matters','')} | {k.get('action','')} |")
        out.append("")

    if analysis.get("striking_distance_plays"):
        out.append("## Striking distance plays\n")
        out.append("| Keyword | Current position | Recommended move |")
        out.append("|---------|-----------------|------------------|")
        for k in analysis["striking_distance_plays"]:
            out.append(f"| {k.get('keyword','')} | {k.get('current_position','')} | {k.get('recommended_move','')} |")
        out.append("")

    if analysis.get("ctr_gap_fixes"):
        out.append("## CTR gap fixes (meta changes)\n")
        for f in analysis["ctr_gap_fixes"]:
            out.append(f"### {f.get('page','')}")
            out.append(f"- **Current title:** {f.get('current_meta_title','(unknown)')}")
            out.append(f"- **Suggested title:** {f.get('suggested_meta_title','')}")
            out.append(f"- **Current description:** {f.get('current_meta_description','(unknown)')}")
            out.append(f"- **Suggested description:** {f.get('suggested_meta_description','')}")
            out.append(f"- **Why:** {f.get('why','')}")
            out.append("")

    if analysis.get("website_amendments"):
        out.append("## Website amendments\n")
        for a in analysis["website_amendments"]:
            out.append(f"### {a.get('location','')}")
            out.append(f"- **Current:** {a.get('current','')}")
            out.append(f"- **Suggested:** {a.get('suggested','')}")
            out.append(f"- **Why:** {a.get('why','')}")
            out.append("")

    if analysis.get("backlink_opportunities"):
        out.append("## Backlink opportunities\n")
        for b in analysis["backlink_opportunities"]:
            out.append(f"- **{b.get('url','')}** — {b.get('why_relevant','')}")
            out.append(f"  - Approach: {b.get('suggested_approach','')}")
        out.append("")

    if analysis.get("reddit_forum_threads"):
        out.append("## Reddit & forum threads\n")
        for t in analysis["reddit_forum_threads"]:
            out.append(f"### {t.get('url','')}")
            out.append(f"**Summary:** {t.get('summary','')}\n")
            out.append("**Draft response (review before posting):**\n")
            out.append(f"> {t.get('draft_response','')}")
            out.append("")

    if analysis.get("trend_findings"):
        out.append("## Trend findings (for content)\n")
        for tr in analysis["trend_findings"]:
            out.append(f"- **{tr.get('topic','')}** — {tr.get('angle','')}")
            out.append(f"  - Why now: {tr.get('why_now','')}")
        out.append("")

    if analysis.get("quick_wins"):
        out.append("## Quick wins\n")
        out.extend(f"- {q}" for q in analysis["quick_wins"])
        out.append("")

    return "\n".join(out)


def render_blog_briefs(analysis: dict) -> str:
    date = today_key()
    out = [
        f"# Alex's content briefs — week of {date}\n",
        "Each brief below is ready to be turned into a draft.\n",
    ]
    opps = analysis.get("keyword_opportunities", [])
    if not opps:
        out.append("_No new briefs this week._\n")
        return "\n".join(out)

    for i, k in enumerate(opps, 1):
        out.append(f"## Brief {i}: {k.get('keyword','')}\n")
        out.append(f"- **Intent:** {k.get('intent','')}")
        out.append(f"- **Why it matters:** {k.get('why_it_matters','')}")
        out.append(f"- **Recommended action:** {k.get('action','')}")
        out.append("")
    return "\n".join(out)


def render_outreach_targets(analysis: dict) -> str:
    date = today_key()
    out = [
        f"# Alex's outreach targets — week of {date}\n",
        "Each target below is ready for outreach. Review every draft before sending.\n",
    ]
    backlinks = analysis.get("backlink_opportunities", [])
    threads = analysis.get("reddit_forum_threads", [])

    if backlinks:
        out.append("## Email outreach (backlinks & features)\n")
        for i, b in enumerate(backlinks, 1):
            out.append(f"### Target {i}: {b.get('url','')}\n")
            out.append(f"- **Why relevant:** {b.get('why_relevant','')}")
            out.append(f"- **Suggested approach:** {b.get('suggested_approach','')}")
            out.append("")

    if threads:
        out.append("## Reddit & forum threads\n")
        for i, t in enumerate(threads, 1):
            out.append(f"### Thread {i}: {t.get('url','')}\n")
            out.append(f"- **Summary:** {t.get('summary','')}")
            out.append(f"- **Draft response (review before posting):**")
            out.append("")
            out.append(f"  > {t.get('draft_response','')}")
            out.append("")

    if not backlinks and not threads:
        out.append("_No new outreach targets this week._\n")
    return "\n".join(out)


def render_trends_for_downstream(analysis: dict) -> str:
    date = today_key()
    out = [
        f"# Alex's trend findings — week of {date}\n",
        "Use these as raw material when planning content. Not scripts; angles.\n",
    ]
    trends = analysis.get("trend_findings", [])
    if not trends:
        out.append("_No new trend findings this week._\n")
    else:
        for tr in trends:
            out.append(f"## {tr.get('topic','')}\n")
            out.append(f"- **Angle:** {tr.get('angle','')}")
            out.append(f"- **Why now:** {tr.get('why_now','')}\n")

    kws = analysis.get("keyword_opportunities", [])
    if kws:
        out.append("## Search language to echo\n")
        out.append("How real people are phrasing these searches right now:")
        for k in kws[:5]:
            out.append(f"- \"{k.get('keyword','')}\" — {k.get('why_it_matters','')}")
        out.append("")
    return "\n".join(out)


def render_summary_for_upstream(analysis: dict, gsc: dict) -> str:
    date = today_key()
    t = gsc["totals"]
    out = [
        f"# Alex's report summary — week of {date}\n",
        f"- Clicks: **{t['clicks']}** ({t['click_delta']:+d} vs previous week)",
        f"- Impressions: **{t['impressions']}** ({t['imp_delta']:+d})",
        "",
        f"**What's working:** {'; '.join(analysis.get('what_to_celebrate', [])) or '—'}",
        f"**What's worrying:** {'; '.join(analysis.get('what_to_worry_about', [])) or '—'}",
        "",
        f"**Top keyword opportunity:** "
        + (analysis.get('keyword_opportunities', [{}])[0].get('keyword', '—')
           if analysis.get('keyword_opportunities') else '—'),
        f"**Top backlink opportunity:** "
        + (analysis.get('backlink_opportunities', [{}])[0].get('url', '—')
           if analysis.get('backlink_opportunities') else '—'),
        "",
        f"Full report: seo-reports/{date}.md",
    ]
    return "\n".join(out)


# ─── Station + email ───────────────────────────────────────────────────────────

@dataclass
class RunResult:
    date: str
    started_at: str
    gsc_ok: bool = False
    analysis_ok: bool = False
    files_written: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def fully_successful(self) -> bool:
        return self.gsc_ok and self.analysis_ok and not self.error


def write_station_report(run: RunResult) -> Path:
    ts = now_local().strftime("%Y-%m-%d-%H%M")
    path = REPORTS / f"alex-{ts}.json"
    path.parent.mkdir(exist_ok=True)

    if run.fully_successful:
        payload = {
            "agent": "alex",
            "agent_display": "Alex — SEO",
            "timestamp": now_local().strftime("%Y-%m-%dT%H:%M:%S"),
            "status": "needs_input",
            "headline": f"Alex's weekly SEO report is ready ({run.date})",
            "summary": (
                "GSC pulled, analysis done. Content briefs and outreach targets "
                "are ready for review."
            ),
            "actions_needed": [
                "Read the full report (~10 mins)",
                "Action the meta title and quick win fixes Alex flagged",
                "Review draft responses before posting anywhere",
            ],
            "files_created": run.files_written,
            "full_brief_path": f"seo-reports/{run.date}.md",
        }
    else:
        payload = {
            "agent": "alex",
            "agent_display": "Alex — SEO",
            "timestamp": now_local().strftime("%Y-%m-%dT%H:%M:%S"),
            "status": "needs_input",
            "headline": f"Alex's weekly run failed ({run.date})",
            "summary": run.error or "See run logs on GitHub Actions.",
            "actions_needed": [
                "Check the GitHub Actions run for full logs",
                "Re-run the workflow once fixed",
            ],
            "files_created": run.files_written,
        }
    path.write_text(json.dumps(payload, indent=2, default=str))
    log(f"  report written: {path.relative_to(ROOT)}")
    return path


def send_failure_email(run: RunResult) -> None:
    to_addr = env("FAILURE_EMAIL_TO", required=False)
    if not to_addr:
        log("  (email alert skipped — FAILURE_EMAIL_TO not set)")
        return
    host = env("FAILURE_EMAIL_SMTP_HOST", required=False, default="smtp.gmail.com")
    from_addr = env("FAILURE_EMAIL_FROM", required=False, default=to_addr)
    password = env("FAILURE_EMAIL_SMTP_PASS", required=False)
    if not password:
        log("  (email alert skipped — FAILURE_EMAIL_SMTP_PASS not set)")
        return

    run_url = (f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', '')}"
               f"/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}")

    body = [
        f"Alex's weekly SEO run hit a problem on {run.date}.",
        "",
        f"Error: {run.error}",
        "",
        f"GitHub Actions run: {run_url}",
    ]
    msg = EmailMessage()
    msg["Subject"] = f"Alex: weekly SEO run failed on {run.date}"
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content("\n".join(body))
    with smtplib.SMTP_SSL(host, 465, timeout=30) as smtp:
        smtp.login(from_addr, password)
        smtp.send_message(msg)
    log(f"  failure email sent to {to_addr}")


# ─── main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    run = RunResult(date=today_key(), started_at=now_local().isoformat())
    log(f"alex: weekly SEO run starting ({run.date})")

    business_name = env("BUSINESS_NAME", required=False, default="your business")

    try:
        gsc = pull_gsc()
        run.gsc_ok = True
    except Exception as e:
        traceback.print_exc()
        run.error = f"GSC pull failed: {e}"
        write_station_report(run)
        send_failure_email(run)
        return 1

    direction = read_if_exists(EXCHANGE / "cleo-direction-latest.md",
                               "(no weekly direction this week)")
    recent_trends = read_if_exists(EXCHANGE / "seo-trends-latest.md", "(none)")

    try:
        analysis = ask_claude(gsc, direction, recent_trends)
        run.analysis_ok = True
    except Exception as e:
        traceback.print_exc()
        run.error = f"Claude analysis failed: {e}"
        write_station_report(run)
        send_failure_email(run)
        return 1

    SEO_REPORTS.mkdir(exist_ok=True)
    report_path = SEO_REPORTS / f"{run.date}.md"
    report_path.write_text(render_full_report(analysis, gsc, business_name))
    run.files_written.append(str(report_path.relative_to(ROOT)))
    log(f"  full report: {report_path.relative_to(ROOT)}")

    EXCHANGE.mkdir(exist_ok=True)
    trends_path = EXCHANGE / "seo-trends-latest.md"
    trends_path.write_text(render_trends_for_downstream(analysis))
    run.files_written.append(str(trends_path.relative_to(ROOT)))
    log(f"  trends:      {trends_path.relative_to(ROOT)}")

    summary_path = EXCHANGE / "seo-report-latest.md"
    summary_path.write_text(render_summary_for_upstream(analysis, gsc))
    run.files_written.append(str(summary_path.relative_to(ROOT)))
    log(f"  summary:     {summary_path.relative_to(ROOT)}")

    BLOG_BRIEFS.mkdir(exist_ok=True)
    briefs_path = BLOG_BRIEFS / f"{run.date}.md"
    briefs_path.write_text(render_blog_briefs(analysis))
    run.files_written.append(str(briefs_path.relative_to(ROOT)))
    log(f"  blog briefs: {briefs_path.relative_to(ROOT)}")

    OUTREACH.mkdir(exist_ok=True)
    outreach_path = OUTREACH / f"{run.date}.md"
    outreach_path.write_text(render_outreach_targets(analysis))
    run.files_written.append(str(outreach_path.relative_to(ROOT)))
    log(f"  outreach:    {outreach_path.relative_to(ROOT)}")

    LOGS.mkdir(exist_ok=True)
    (LOGS / f"alex-gsc-{run.date}.json").write_text(json.dumps(gsc, indent=2, default=str))
    (LOGS / f"alex-analysis-{run.date}.json").write_text(json.dumps(analysis, indent=2, default=str))

    write_station_report(run)
    log("alex: done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
