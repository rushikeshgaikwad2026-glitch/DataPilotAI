"""Render a dashboard spec as one complete, high-resolution page.

Used for the PDF, PNG and JPG downloads. Needs only matplotlib (and Pillow
for JPG). No browser, Kaleido or Streamlit involved, so it works anywhere the
app runs. Figures are built with matplotlib's object API (no pyplot), which is
thread-safe inside Streamlit.
"""

import io
import math
import textwrap
import threading

import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle
from matplotlib.ticker import FuncFormatter

import project_info as info

INK = "#0F172A"
BODY = "#334155"
MUTED = "#64748B"
LINE = "#E2E8F0"
PAGE = "#F5F7FC"
CARD = "#FFFFFF"
NAVY = "#111B36"

PAGE_W = 16.0
MARGIN = 0.6
GAP = 0.3
CONTENT_W = PAGE_W - 2 * MARGIN

HEADER_H = 2.0
KPI_H = 1.3
KPI_GAP = 0.25
SECTION_H = 0.55
WIDE_H = 5.2
HALF_H = 5.2
FOOTER_H = 1.35


def compact(value):
    """Short axis/label number: 1.2K, 3.4M."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    a = abs(v)
    if a >= 1e9:
        return f"{v / 1e9:.1f}B"
    if a >= 1e6:
        return f"{v / 1e6:.1f}M"
    if a >= 1e4:
        return f"{v / 1e3:.0f}K"
    if a >= 1e3:
        return f"{v / 1e3:.1f}K"
    if v == int(v):
        return f"{int(v)}"
    return f"{v:.2f}"


def _wrap(text, width_in, fontsize):
    chars = max(12, int(width_in / (fontsize * 0.0088)))
    return textwrap.wrap(str(text), chars) or [""]


def _lines_capped(text, width_in, fontsize, max_lines):
    lines = _wrap(text, width_in, fontsize)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .,;") + "…"
    return lines


# ---------------------------------------------------------------------------
# Layout measurement
# ---------------------------------------------------------------------------

def _chart_rows(charts):
    """Group charts into rows: wide ones alone, half-width ones in pairs."""
    rows, pending = [], []
    for chart in charts:
        if chart["size"] == "wide":
            if pending:
                rows.append(pending)
                pending = []
            rows.append([chart])
        else:
            pending.append(chart)
            if len(pending) == 2:
                rows.append(pending)
                pending = []
    if pending:
        rows.append(pending)
    return rows


def _insight_block_heights(spec, left_w, right_w):
    left = 0.95
    for finding, action in spec["observations"]:
        left += (
            0.19 * len(_wrap(finding, left_w - 0.9, 10))
            + 0.17 * len(_wrap("→ " + action, left_w - 0.9, 9))
            + 0.3
        )
    if not spec["observations"]:
        left += 0.5

    q = spec["quality"]
    right = 0.95 + 0.34 * 3
    if q["worst_columns"]:
        right += 0.3 + 0.24 * min(3, len(q["worst_columns"]))
    right += 0.5
    for note in spec["notes"]:
        right += 0.17 * len(_wrap("• " + note, right_w - 0.5, 8.5)) + 0.08
    return max(left, right, 2.6)


def _measure(spec):
    kpi_rows = math.ceil(len(spec["kpis"]) / 3)
    height = HEADER_H + 0.4
    height += SECTION_H + kpi_rows * KPI_H + (kpi_rows - 1) * KPI_GAP + 0.3
    rows = _chart_rows(spec["charts"])
    height += SECTION_H
    height += (sum(WIDE_H if r[0]["size"] == "wide" else HALF_H for r in rows)
               + GAP * max(0, len(rows) - 1)) if rows else 1.2
    height += 0.3 + SECTION_H
    left_w = CONTENT_W * 0.58 - GAP / 2
    right_w = CONTENT_W - left_w - GAP
    height += _insight_block_heights(spec, left_w, right_w)
    height += 0.5 + FOOTER_H
    return height, rows


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def _rounded(ax, x, y, w, h, fc, ec="none", lw=0.9, r=0.14, alpha=1.0, z=1):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
        fc=fc, ec=ec, lw=lw, alpha=alpha, zorder=z,
    ))


def _text(ax, x, y, s, size=10, color=INK, weight="normal", ha="left", va="top", **kw):
    return ax.text(x, y, s, fontsize=size, color=color, fontweight=weight,
                   ha=ha, va=va, zorder=5, **kw)


def _section_title(ax, y, label):
    _text(ax, MARGIN, y + 0.05, label.upper(), size=9.5, color=MUTED, weight="bold")
    ax.add_patch(Rectangle((MARGIN, y + 0.36), 0.5, 0.045, fc=ACCENT[0], ec="none", zorder=3))


def _style_axes(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(LINE)
    ax.tick_params(axis="both", labelsize=8, colors=MUTED, length=0, pad=4)
    ax.set_facecolor("none")


ACCENT = ["#243B7A", "#6675E8", "#91A3F4", "#B9C9FA"]


# ---------------------------------------------------------------------------
# Chart drawers (one per chart kind)
# ---------------------------------------------------------------------------

def _draw_line(ax, chart):
    x = np.arange(len(chart["x"]))
    y = np.array(chart["y"], dtype=float)
    ax.plot(x, y, color=ACCENT[0], lw=2.4, marker="o", ms=4, zorder=3)
    if chart.get("y_smooth"):
        smooth = np.array([np.nan if v is None else v for v in chart["y_smooth"]], dtype=float)
        ax.plot(x, smooth, color=ACCENT[1], lw=1.8, ls="--", zorder=2, label="3-period average")
        ax.legend(frameon=False, fontsize=8, loc="upper left", labelcolor=MUTED)
    bottom = 0 if y.min() >= 0 else y.min() * 1.1
    top = y.max() * 1.18 if y.max() > 0 else 1
    ax.set_ylim(bottom, top)
    ax.fill_between(x, y, bottom, color=ACCENT[0], alpha=0.08, zorder=1)
    step = max(1, math.ceil(len(x) / 8))
    ax.set_xticks(x[::step])
    ax.set_xticklabels([chart["x"][i] for i in x[::step]])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: compact(v)))
    ax.grid(axis="y", color=LINE, lw=0.8)
    ax.set_axisbelow(True)
    peak = int(np.argmax(y))
    ax.annotate(
        f"Peak {compact(y[peak])}", xy=(peak, y[peak]), xytext=(0, 9),
        textcoords="offset points", ha="center", fontsize=8,
        color=ACCENT[0], fontweight="bold",
    )
    _style_axes(ax)


def _draw_bar(ax, chart):
    labels = chart["labels"]
    values = np.array(chart["values"], dtype=float)
    n = len(values)
    ypos = np.arange(n)[::-1]
    colors = [ACCENT[0]] + [ACCENT[1]] * (n - 1)
    ax.barh(ypos, values, color=colors, height=0.62, zorder=3)
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels)
    ax.set_xticks([])
    top = values.max() if values.max() > 0 else 1
    ax.set_xlim(min(0, values.min() * 1.1), top * 1.32)
    shares = chart.get("shares")
    for i, v in enumerate(values):
        text = compact(v) + (f"  ·  {shares[i]:.0f}%" if shares else "")
        ax.text(v + top * 0.02, ypos[i], text, va="center", fontsize=8,
                color=BODY, fontweight="bold")
    _style_axes(ax)
    ax.spines["bottom"].set_visible(False)
    ax.tick_params(axis="y", labelsize=8.5, colors=BODY)


def _draw_hist(ax, chart):
    edges = np.array(chart["edges"])
    counts = np.array(chart["counts"])
    ax.bar(edges[:-1], counts, width=np.diff(edges), align="edge",
           color=ACCENT[1], edgecolor="white", lw=0.6, zorder=3)
    ax.axvline(chart["median"], color=ACCENT[0], lw=2, ls="--", zorder=4,
               label=f"Median {compact(chart['median'])}")
    if abs(chart["mean"] - chart["median"]) > 1e-12:
        ax.axvline(chart["mean"], color="#F59E0B", lw=2, ls=":", zorder=4,
                   label=f"Average {compact(chart['mean'])}")
    ax.legend(frameon=False, fontsize=8, loc="upper right", labelcolor=BODY)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: compact(v)))
    ax.set_xlabel(chart["x_label"], fontsize=8.5, color=MUTED)
    ax.set_ylabel("Records", fontsize=8.5, color=MUTED)
    ax.grid(axis="y", color=LINE, lw=0.8)
    ax.set_axisbelow(True)
    _style_axes(ax)


def _draw_scatter(ax, chart):
    ax.scatter(chart["x"], chart["y"], s=14, color=ACCENT[1], alpha=0.5,
               edgecolors="none", zorder=3)
    (x0, y0), (x1, y1) = chart["fit"]
    ax.plot([x0, x1], [y0, y1], color=ACCENT[0], lw=2.2, zorder=4)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: compact(v)))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: compact(v)))
    ax.set_xlabel(chart["x_label"], fontsize=8.5, color=MUTED)
    ax.set_ylabel(chart["y_label"], fontsize=8.5, color=MUTED)
    ax.grid(color=LINE, lw=0.8)
    ax.set_axisbelow(True)
    _style_axes(ax)


_DRAWERS = {"line": _draw_line, "bar": _draw_bar, "hist": _draw_hist, "scatter": _draw_scatter}


# ---------------------------------------------------------------------------
# Page sections
# ---------------------------------------------------------------------------

def _draw_header(bg, spec):
    _rounded(bg, 0, 0, PAGE_W, HEADER_H, ACCENT[0], r=0.0, z=1)
    glow = Circle((PAGE_W - 1.2, 0.2), 2.6, fc=ACCENT[1], ec="none", alpha=0.35, zorder=2)
    bg.add_patch(glow)
    glow.set_clip_path(Rectangle((0, 0), PAGE_W, HEADER_H, transform=bg.transData))
    _text(bg, MARGIN, 0.42, info.PRODUCT_NAME.upper() + "  ·  BUSINESS INTELLIGENCE REPORT",
          size=9, color="#DCE4FF", weight="bold")
    _text(bg, MARGIN, 0.78, spec["title"], size=27, color="white", weight="bold")
    bits = [spec["source_name"], f"{spec['rows']:,} records", f"{spec['columns']} columns"]
    if spec.get("date_range"):
        bits.append(spec["date_range"])
    _text(bg, MARGIN, 1.43, "   ·   ".join(bits), size=10.5, color="#E6EBFF")
    _text(bg, MARGIN, 1.69,
          f"Detected domain: {spec['domain']} ({spec['confidence']} confidence)   ·   "
          f"Generated {spec['generated']}",
          size=9, color="#C7D2FE")


def _draw_kpis(bg, spec, y):
    card_w = (CONTENT_W - 2 * GAP) / 3
    for i, kpi in enumerate(spec["kpis"]):
        row, col = divmod(i, 3)
        x = MARGIN + col * (card_w + GAP)
        cy = y + row * (KPI_H + KPI_GAP)
        _rounded(bg, x, cy, card_w, KPI_H, CARD, ec=LINE, z=2)
        bg.add_patch(Rectangle((x, cy + 0.22), 0.07, KPI_H - 0.44, fc=ACCENT[0], ec="none", zorder=3))
        _text(bg, x + 0.3, cy + 0.2, kpi["label"].upper(), size=8.5, color=MUTED, weight="bold")
        value = str(kpi["value"])
        size = 24 if len(value) <= 12 else (18 if len(value) <= 20 else 13)
        _text(bg, x + 0.3, cy + 0.46, value, size=size, color=INK, weight="bold")
        _text(bg, x + 0.3, cy + KPI_H - 0.3, kpi["note"], size=8.5, color=MUTED)


def _draw_chart_card(fig, bg, chart, x, y, w, h, page_h):
    _rounded(bg, x, y, w, h, CARD, ec=LINE, z=2)
    pad = 0.28
    inner = w - 2 * pad
    title = textwrap.shorten(chart["title"], width=max(20, int(inner / (12.5 * 0.0088))), placeholder="…")
    _text(bg, x + pad, y + 0.22, title, size=12.5, color=INK, weight="bold")
    subtitle = textwrap.shorten(chart["subtitle"], width=max(20, int(inner / (9 * 0.0088))), placeholder="…")
    _text(bg, x + pad, y + 0.55, subtitle, size=9, color=MUTED)

    plot_top, plot_bottom = y + 0.95, y + h - 1.5
    ax = fig.add_axes([
        (x + pad + 0.35) / PAGE_W,
        1 - plot_bottom / page_h,
        (inner - 0.35 - 0.05) / PAGE_W,
        (plot_bottom - plot_top) / page_h,
    ])
    _DRAWERS[chart["kind"]](ax, chart)

    box_y = y + h - 1.05
    box_h = 0.85
    _rounded(bg, x + pad, box_y, inner, box_h, ACCENT[0], r=0.1, alpha=0.07, z=3)
    bg.add_patch(Rectangle((x + pad, box_y + 0.1), 0.05, box_h - 0.2, fc=ACCENT[0], ec="none", zorder=4))
    lines = _lines_capped(chart["takeaway"], inner - 0.35, 9.5, 3)
    _text(bg, x + pad + 0.2, box_y + 0.1, "\n".join(lines), size=9.5, color=BODY,
          linespacing=1.35)


def _draw_charts(fig, bg, rows, y, page_h):
    if not rows:
        _rounded(bg, MARGIN, y, CONTENT_W, 1.0, CARD, ec=LINE, z=2)
        _text(bg, MARGIN + 0.3, y + 0.35,
              "No chart could be built reliably from this dataset's fields.",
              size=11, color=MUTED)
        return y + 1.2
    for ri, row in enumerate(rows):
        h = WIDE_H if row[0]["size"] == "wide" else HALF_H
        if row[0]["size"] == "wide":
            _draw_chart_card(fig, bg, row[0], MARGIN, y, CONTENT_W, h, page_h)
        else:
            w = (CONTENT_W - GAP) / 2
            for ci, chart in enumerate(row):
                _draw_chart_card(fig, bg, chart, MARGIN + ci * (w + GAP), y, w, h, page_h)
        y += h + (GAP if ri < len(rows) - 1 else 0)
    return y


def _draw_insights(bg, spec, y, height):
    left_w = CONTENT_W * 0.58 - GAP / 2
    right_w = CONTENT_W - left_w - GAP

    _rounded(bg, MARGIN, y, left_w, height, CARD, ec=LINE, z=2)
    _text(bg, MARGIN + 0.3, y + 0.25, "Key observations", size=13, weight="bold")
    _text(bg, MARGIN + 0.3, y + 0.58, "What stands out, and what to do about it", size=9, color=MUTED)
    cy = y + 1.0
    if not spec["observations"]:
        _text(bg, MARGIN + 0.3, cy, "No notable findings were detected.", size=10, color=MUTED)
    for n, (finding, action) in enumerate(spec["observations"], 1):
        bg.add_patch(Circle((MARGIN + 0.5, cy + 0.14), 0.17, fc=ACCENT[0], ec="none", alpha=0.14, zorder=3))
        _text(bg, MARGIN + 0.5, cy + 0.14, str(n), size=9, color=ACCENT[0], weight="bold", ha="center", va="center")
        lines = _wrap(finding, left_w - 0.9, 10)
        _text(bg, MARGIN + 0.85, cy, "\n".join(lines), size=10, color=INK, weight="bold", linespacing=1.3)
        cy += 0.19 * len(lines) + 0.04
        alines = _wrap("→ " + action, left_w - 0.9, 9)
        _text(bg, MARGIN + 0.85, cy, "\n".join(alines), size=9, color=MUTED, linespacing=1.3)
        cy += 0.17 * len(alines) + 0.26

    rx = MARGIN + left_w + GAP
    _rounded(bg, rx, y, right_w, height, CARD, ec=LINE, z=2)
    _text(bg, rx + 0.3, y + 0.25, "Data quality", size=13, weight="bold")
    q = spec["quality"]
    ry = y + 0.75
    for label, value in (
        ("Completeness", f"{q['completeness']:.1f}%"),
        ("Missing cells", f"{q['missing_cells']:,}"),
        ("Duplicate rows", f"{q['duplicate_rows']:,}"),
    ):
        _text(bg, rx + 0.3, ry, label, size=9.5, color=MUTED)
        _text(bg, rx + right_w - 0.3, ry, value, size=10, color=INK, weight="bold", ha="right")
        ry += 0.34
    if q["worst_columns"]:
        ry += 0.04
        _text(bg, rx + 0.3, ry, "Most gaps:", size=8.5, color=MUTED, weight="bold")
        ry += 0.26
        for column, count, pct in q["worst_columns"][:3]:
            _text(bg, rx + 0.3, ry, textwrap.shorten(column, 28, placeholder="…"), size=8.5, color=BODY)
            _text(bg, rx + right_w - 0.3, ry, f"{pct:.0f}% missing", size=8.5, color=BODY, ha="right")
            ry += 0.24
    ry += 0.3
    _text(bg, rx + 0.3, ry, "Notes", size=11, weight="bold")
    ry += 0.38
    for note in spec["notes"]:
        lines = _wrap("• " + note, right_w - 0.5, 8.5)
        _text(bg, rx + 0.3, ry, "\n".join(lines), size=8.5, color=BODY, linespacing=1.3)
        ry += 0.17 * len(lines) + 0.08


def _draw_footer(bg, spec, y):
    bg.add_patch(Rectangle((0, y), PAGE_W, FOOTER_H + 0.5, fc=NAVY, ec="none", zorder=1))
    cx = PAGE_W / 2
    _text(bg, cx, y + 0.22, f"{info.CREDIT_LINE}   ·   {info.AUTHOR_QUALIFICATION}",
          size=11, color="white", weight="bold", ha="center")
    _text(bg, cx, y + 0.55, f"{info.AUTHOR_EMAIL}     |     {info.AUTHOR_PHONE}",
          size=9.5, color="#C7D2FE", ha="center")
    _text(bg, cx, y + 0.88,
          f"Generated by {info.PRODUCT_NAME} on {spec['generated']}.  Validate findings before making important decisions.",
          size=8, color="#8C9ACB", ha="center")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_RENDER_LOCK = threading.Lock()


def render_dashboard(spec, colors):
    """Return a matplotlib Figure containing the full dashboard.

    Drawing reads the module-level ACCENT palette, so building is serialised
    to stay correct when several Streamlit sessions render at the same time.
    """
    with _RENDER_LOCK:
        return _build_figure(spec, colors)


def _build_figure(spec, colors):
    global ACCENT
    ACCENT = list(colors) + ["#B9C9FA"] * max(0, 4 - len(colors))

    page_h, rows = _measure(spec)
    fig = Figure(figsize=(PAGE_W, page_h), facecolor=PAGE)
    bg = fig.add_axes([0, 0, 1, 1])
    bg.set_xlim(0, PAGE_W)
    bg.set_ylim(page_h, 0)
    bg.axis("off")

    _draw_header(bg, spec)
    y = HEADER_H + 0.4
    _section_title(bg, y, "Key performance indicators")
    y += SECTION_H
    _draw_kpis(bg, spec, y)
    kpi_rows = math.ceil(len(spec["kpis"]) / 3)
    y += kpi_rows * KPI_H + (kpi_rows - 1) * KPI_GAP + 0.3

    _section_title(bg, y, "Performance analysis")
    y += SECTION_H
    y = _draw_charts(fig, bg, rows, y, page_h)

    y += 0.3
    _section_title(bg, y, "Insights and data quality")
    y += SECTION_H
    left_w = CONTENT_W * 0.58 - GAP / 2
    right_w = CONTENT_W - left_w - GAP
    block_h = _insight_block_heights(spec, left_w, right_w)
    _draw_insights(bg, spec, y, block_h)
    y += block_h + 0.5

    _draw_footer(bg, spec, y)
    return fig


def dashboard_png(spec, colors, dpi=150):
    buffer = io.BytesIO()
    render_dashboard(spec, colors).savefig(buffer, format="png", dpi=dpi, facecolor=PAGE)
    return buffer.getvalue()


def dashboard_jpg(spec, colors, dpi=150, quality=92):
    from PIL import Image

    image = Image.open(io.BytesIO(dashboard_png(spec, colors, dpi))).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def dashboard_pdf(spec, colors):
    buffer = io.BytesIO()
    render_dashboard(spec, colors).savefig(
        buffer,
        format="pdf",
        facecolor=PAGE,
        metadata={
            "Title": f"{spec['title']} — {spec['source_name']}",
            "Author": info.AUTHOR_NAME,
            "Creator": info.PRODUCT_NAME,
        },
    )
    return buffer.getvalue()
