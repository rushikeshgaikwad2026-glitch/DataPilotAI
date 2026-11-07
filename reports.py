"""Downloadable interactive reports and cleaned Excel workbooks."""

import html
import io
from datetime import datetime

import pandas as pd
from plotly.offline import get_plotlyjs

import project_info as info

HTML_CSS = """
*{box-sizing:border-box}
body{margin:0;padding:32px;background:#F5F7FB;color:#0F172A;
     font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif}
.wrap{max-width:1400px;margin:auto}
.hero{background:linear-gradient(120deg,ACCENT,ACCENT2);color:#fff;padding:32px 36px;
      border-radius:22px;margin-bottom:8px}
.hero h1{margin:0 0 6px;font-size:30px;letter-spacing:-.02em}
.hero p{margin:3px 0;opacity:.9;font-size:14px}
h2{margin:32px 0 14px;font-size:19px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px}
.kpi{background:#fff;border:1px solid #E5EAF2;border-left:4px solid ACCENT;
     border-radius:14px;padding:18px 20px}
.kl{font-size:12px;font-weight:600;color:#64748B}
.kv{font-size:25px;font-weight:800;margin-top:10px;overflow-wrap:anywhere}
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:16px}
.card{background:#fff;border:1px solid #E5EAF2;border-radius:16px;padding:16px;min-width:0}
.takeaway{margin:4px 2px 0;color:#475569;font-size:13px;line-height:1.55}
ol{padding-left:20px;line-height:1.6}
li{margin-bottom:14px}
li span{color:#475569;font-size:14px}
.foot{margin:34px 0 6px;text-align:center;color:#94A3B8;font-size:12px}
@media(max-width:560px){.charts{grid-template-columns:1fr}body{padding:12px}}
"""


def _e(value):
    return html.escape(str(value))


def build_html_report(title, filename, kpis, charts, insights, colors):
    css = HTML_CSS.replace("ACCENT2", colors[1]).replace("ACCENT", colors[0])
    config = {"displaylogo": False, "responsive": True}

    kpi_html = "".join(
        f'<div class="kpi"><div class="kl">{_e(l)}</div><div class="kv">{_e(v)}</div></div>'
        for l, v in kpis
    )
    chart_html = "".join(
        f'<div class="card">'
        f'{c["figure"].to_html(full_html=False, include_plotlyjs=False, config=config)}'
        f'<p class="takeaway">{_e(c.get("takeaway", ""))}</p></div>'
        for c in charts
    )
    insight_html = "".join(
        f"<li><b>{_e(f)}</b><br><span>→ {_e(a)}</span></li>" for f, a in insights
    )

    page = (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{_e(title)}</title><style>{css}</style>"
        f"<script>{get_plotlyjs()}</script></head><body><div class='wrap'>"
        f"<div class='hero'><h1>{_e(title)}</h1>"
        f"<p>Source: {_e(filename)}</p>"
        f"<p>Generated {datetime.now():%d %B %Y, %H:%M} by DataPilot AI</p></div>"
        f"<h2>Key metrics</h2><div class='kpis'>{kpi_html}</div>"
        f"<h2>Visual analysis</h2><div class='charts'>{chart_html}</div>"
        f"<h2>Insights &amp; recommended actions</h2><ol>{insight_html}</ol>"
        "<div class='foot'>DataPilot AI · Validate findings before making "
        "important decisions.<br>"
        f"{_e(info.CREDIT_LINE)} · {_e(info.AUTHOR_QUALIFICATION)}<br>"
        f"{_e(info.AUTHOR_EMAIL)} · {_e(info.AUTHOR_PHONE)}</div>"
        "</div></body></html>"
    )
    return page.encode("utf-8")


def build_excel(cleaned, log):
    for engine in ("xlsxwriter", "openpyxl"):
        try:
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine=engine) as writer:
                cleaned.to_excel(writer, sheet_name="Cleaned Data", index=False)
                log.to_excel(writer, sheet_name="Cleaning Log", index=False)
            return out.getvalue()
        except ImportError:
            continue
    return None
