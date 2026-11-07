"""Dashboard specification builder.

Turns a dataset plus its plan into a plain-data "spec": KPI cards, charts with
a one-line business takeaway each, observations and data-quality notes.

Pure pandas/numpy. No plotting or UI imports, so the same spec feeds the
on-screen Plotly dashboard, the HTML export and the PDF/PNG/JPG exports.
"""

from datetime import datetime

import numpy as np
import pandas as pd

from columns import _has, _tokens, to_datetime, to_num
from insights import format_value

MAX_CATEGORY_BARS = 8
MIN_ROWS_FOR_DISTRIBUTION = 20
MIN_ROWS_FOR_RELATIONSHIP = 20
MIN_CORRELATION = 0.5

# Words that make a measure "average-able" rather than "sum-able".
AVERAGE_WORDS = {
    "avg", "average", "mean", "per", "price", "rate", "salary", "age", "score",
    "rating", "percent", "percentage", "ratio", "margin", "tenure", "duration",
    "balance", "temperature", "experience", "satisfaction", "gpa", "cgpa",
    "hours", "years", "weight", "height",
}
ADDITIVE_WORDS = {
    "revenue", "sales", "profit", "amount", "cost", "income", "expense",
    "spend", "payment", "turnover", "quantity", "units", "orders", "volume",
    "budget", "fee", "tax", "discount", "loss", "claims", "total",
}


def aggregation_for(column):
    """'sum' for additive measures (revenue), 'mean' for rates/levels (salary)."""
    _, tokens = _tokens(column)
    if _has(tokens, {"avg", "average", "mean", "per"}):
        return "mean"
    if "total" in tokens:
        return "sum"
    if _has(tokens, AVERAGE_WORDS):
        return "mean"
    if _has(tokens, ADDITIVE_WORDS):
        return "sum"
    return "mean"


def measure_label(metric, agg):
    return f"{'Total' if agg == 'sum' else 'Average'} {metric}"


def _clean_numbers(df, column):
    return to_num(df, column).replace([np.inf, -np.inf], np.nan)


def _short(text, limit=26):
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _signed_pct(change):
    return f"{change:+.1f}%"


def _move(change):
    """'up 9.3%' / 'down 9.3%' / 'flat' for a percentage change."""
    if abs(change) < 0.05:
        return "flat"
    return f"{'up' if change > 0 else 'down'} {abs(change):.1f}%"


# --------------------------------------------------------------------------
# Time series
# --------------------------------------------------------------------------

def _period_label(period, freq):
    if freq == "Q":
        return f"Q{period.quarter} {period.year}"
    if freq == "M":
        return period.start_time.strftime("%b %Y")
    return period.start_time.strftime("%d %b %Y")


def _period_series(df, date_column, metric, agg):
    """Aggregate the metric by a sensible period. Returns a dict or None."""
    frame = pd.DataFrame({
        "d": to_datetime(df[date_column]),
        "v": _clean_numbers(df, metric),
    }).dropna()
    if len(frame) < 3:
        return None

    span_days = (frame["d"].max() - frame["d"].min()).days
    if span_days <= 45:
        freq, unit = "D", "day"
    elif span_days <= 180:
        freq, unit = "W", "week"
    elif span_days <= 1500:
        freq, unit = "M", "month"
    else:
        freq, unit = "Q", "quarter"

    grouped = frame.groupby(frame["d"].dt.to_period(freq))["v"].agg(
        "sum" if agg == "sum" else "mean"
    )
    periods = list(grouped.index)
    values = [float(v) for v in grouped.values]
    notes = []

    # A partly-covered first/last period makes a *sum* look like a dip.
    if agg == "sum" and freq in ("M", "Q") and len(periods) > 3:
        def coverage(period, start, end):
            total_days = (period.end_time.normalize() - period.start_time.normalize()).days + 1
            return ((end - start).days + 1) / total_days

        last_cov = coverage(
            periods[-1], periods[-1].start_time.normalize(), frame["d"].max().normalize()
        )
        if last_cov < 0.8:
            notes.append(
                f"The latest {unit} ({_period_label(periods[-1], freq)}) is only "
                "partly covered by the data, so it is excluded from the trend."
            )
            periods, values = periods[:-1], values[:-1]

        first_cov = coverage(
            periods[0], frame["d"].min().normalize(), periods[0].end_time.normalize()
        )
        if first_cov < 0.8 and len(periods) > 3:
            notes.append(
                f"The first {unit} ({_period_label(periods[0], freq)}) is only "
                "partly covered by the data, so it is excluded from the trend."
            )
            periods, values = periods[1:], values[1:]

    if len(periods) < 3 or len(set(round(v, 9) for v in values)) < 2:
        return None

    return {
        "freq": freq,
        "unit": unit,
        "periods": periods,
        "labels": [_period_label(p, freq) for p in periods],
        "values": values,
        "notes": notes,
        "start": frame["d"].min(),
        "end": frame["d"].max(),
    }


def _trend_chart(series, metric, agg):
    values = series["values"]
    labels = series["labels"]
    peak_index = int(np.argmax(values))

    half = len(values) // 2
    first = float(np.mean(values[:half]))
    second = float(np.mean(values[len(values) - half:]))
    if first:
        change = (second - first) / abs(first) * 100
        if abs(change) < 3:
            direction = f"{metric} was broadly flat across the period."
        else:
            direction = (
                f"The second half of the period averaged {abs(change):.1f}% "
                f"{'higher' if change > 0 else 'lower'} than the first half."
            )
    else:
        direction = ""

    word = "total" if agg == "sum" else "average"
    smooth = None
    if len(values) >= 8:
        smooth = (
            pd.Series(values).rolling(3, min_periods=3).mean()
            .where(lambda s: s.notna(), None).tolist()
        )
        smooth = [None if (v is None or pd.isna(v)) else float(v) for v in smooth]

    return {
        "id": "trend",
        "kind": "line",
        "size": "wide",
        "title": f"How is {metric} changing over time?",
        "subtitle": f"{word.capitalize()} {metric} by {series['unit']}",
        "takeaway": (
            f"Highest {series['unit']}: {labels[peak_index]} "
            f"({format_value(values[peak_index])}). {direction}"
        ).strip(),
        "x": labels,
        "y": values,
        "y_smooth": smooth,
        "y_label": f"{word.capitalize()} {metric}",
    }


# --------------------------------------------------------------------------
# Categories
# --------------------------------------------------------------------------

def _category_chart(df, category, metric, agg, chart_id):
    labels_all = df[category].astype("string").fillna("Unknown")

    if metric is None:
        counts = labels_all.value_counts().head(MAX_CATEGORY_BARS)
        if len(counts) < 2:
            return None
        share = counts / max(1, len(df)) * 100
        return {
            "id": chart_id,
            "kind": "bar",
            "size": "half",
            "title": f"Which {category} values are most common?",
            "subtitle": f"Number of records by {category}",
            "takeaway": (
                f"{counts.index[0]} is the most frequent {category} "
                f"({share.iloc[0]:.0f}% of records)."
            ),
            "labels": [_short(x) for x in counts.index],
            "values": [float(x) for x in counts.values],
            "shares": [float(x) for x in share.values],
            "value_label": "Records",
        }

    frame = pd.DataFrame({"c": labels_all, "v": _clean_numbers(df, metric)}).dropna(subset=["v"])
    if frame.empty:
        return None

    grouped = frame.groupby("c")["v"].agg(["sum" if agg == "sum" else "mean", "count"])
    value_col = "sum" if agg == "sum" else "mean"
    if agg == "mean":
        # Averages over one-off records are misleading.
        reliable = grouped[grouped["count"] >= 2]
        if len(reliable) >= 2:
            grouped = reliable

    ranked = grouped[value_col].sort_values(ascending=False)
    if len(ranked) < 2 or ranked.nunique() < 2:
        return None
    top = ranked.head(MAX_CATEGORY_BARS)

    total = float(frame["v"].sum())
    shares = None
    if agg == "sum" and total > 0 and (ranked >= 0).all():
        shares = [float(v / total * 100) for v in top.values]

    if agg == "sum":
        lead = f"{top.index[0]} leads with {format_value(top.iloc[0])}"
        if shares:
            lead += f" ({shares[0]:.0f}% of total {metric})"
            top3 = sum(shares[:3])
            if len(top) > 3:
                lead += f"; the top 3 together account for {top3:.0f}%"
        takeaway = lead + "."
        subtitle = f"Total {metric} by {category} (top {len(top)})"
        question = f"Which {category} drives the most {metric}?"
    else:
        takeaway = (
            f"{top.index[0]} has the highest average {metric} "
            f"({format_value(top.iloc[0])}); {ranked.index[-1]} has the lowest "
            f"({format_value(ranked.iloc[-1])})."
        )
        subtitle = f"Average {metric} by {category} (top {len(top)})"
        question = f"How does {metric} differ across {category}?"

    return {
        "id": chart_id,
        "kind": "bar",
        "size": "half",
        "title": question,
        "subtitle": subtitle,
        "takeaway": takeaway,
        "labels": [_short(x) for x in top.index],
        "values": [float(v) for v in top.values],
        "shares": shares,
        "value_label": measure_label(metric, agg),
    }


# --------------------------------------------------------------------------
# Distribution and relationship
# --------------------------------------------------------------------------

def _distribution_chart(df, metric):
    values = _clean_numbers(df, metric).dropna()
    if len(values) < MIN_ROWS_FOR_DISTRIBUTION or values.nunique() < 5:
        return None

    low, high = float(values.quantile(0.005)), float(values.quantile(0.995))
    if not high > low:
        low, high = float(values.min()), float(values.max())
    shown = values[(values >= low) & (values <= high)]
    outside = len(values) - len(shown)
    bins = int(np.clip(np.sqrt(len(shown)), 8, 24))
    counts, edges = np.histogram(shown, bins=bins, range=(low, high))

    mean, median = float(values.mean()), float(values.median())
    takeaway = f"A typical record has a {metric} of about {format_value(median)} (median)."
    if median and abs(mean - median) / abs(median) > 0.15:
        pull = "up" if mean > median else "down"
        takeaway += (
            f" The average ({format_value(mean)}) is pulled {pull} by a minority "
            "of unusually "
            f"{'large' if mean > median else 'small'} values."
        )
    if outside:
        takeaway += f" {outside:,} extreme values fall outside the range shown."

    return {
        "id": "distribution",
        "kind": "hist",
        "size": "half",
        "title": f"What does a typical {metric} value look like?",
        "subtitle": f"Number of records by {metric} range",
        "takeaway": takeaway,
        "edges": [float(e) for e in edges],
        "counts": [int(c) for c in counts],
        "median": median,
        "mean": mean,
        "x_label": metric,
    }


def _relationship_chart(df, metric, partners):
    base = _clean_numbers(df, metric)
    best = None
    for partner in partners:
        if partner == metric:
            continue
        pair = pd.DataFrame({"x": _clean_numbers(df, partner), "y": base}).dropna()
        if (
            len(pair) < MIN_ROWS_FOR_RELATIONSHIP
            or pair["x"].nunique() < 5
            or pair["y"].nunique() < 5
        ):
            continue
        r = pair["x"].corr(pair["y"])
        if pd.notna(r) and abs(r) >= MIN_CORRELATION and (best is None or abs(r) > abs(best[1])):
            best = (partner, float(r), pair)
    if best is None:
        return None

    partner, r, pair = best
    if len(pair) > 1500:
        pair = pair.sample(1500, random_state=42)
    slope, intercept = np.polyfit(pair["x"], pair["y"], 1)
    x0, x1 = float(pair["x"].min()), float(pair["x"].max())

    strength = "strong" if abs(r) >= 0.8 else "moderate"
    sign = "positive" if r > 0 else "negative"
    tendency = "higher" if r > 0 else "lower"
    return {
        "id": "relationship",
        "kind": "scatter",
        "size": "half",
        "title": f"Does {partner} move with {metric}?",
        "subtitle": f"Each dot is one record (correlation r = {r:+.2f})",
        "takeaway": (
            f"There is a {strength} {sign} relationship: records with higher "
            f"{partner} tend to have {tendency} {metric}. This shows association, "
            "not proof of cause."
        ),
        "x": [float(v) for v in pair["x"]],
        "y": [float(v) for v in pair["y"]],
        "fit": [[x0, float(slope * x0 + intercept)], [x1, float(slope * x1 + intercept)]],
        "x_label": partner,
        "y_label": metric,
        "r": r,
    }


# --------------------------------------------------------------------------
# KPIs, observations, notes
# --------------------------------------------------------------------------

def _build_kpis(df, plan, series, charts, quality):
    metric, category = plan["metric"], plan["category"]
    agg = aggregation_for(metric) if metric else None
    kpis = [{
        "label": "Total records",
        "value": f"{len(df):,}",
        "note": f"{df.shape[1]} columns analysed",
    }]

    if metric:
        values = _clean_numbers(df, metric).dropna()
        if not values.empty:
            if agg == "sum":
                kpis.append({
                    "label": measure_label(metric, agg),
                    "value": format_value(values.sum()),
                    "note": f"Average {format_value(values.mean())} per record",
                })
            else:
                kpis.append({
                    "label": measure_label(metric, agg),
                    "value": format_value(values.mean()),
                    "note": f"Median {format_value(values.median())}",
                })

    if series is not None:
        values = series["values"]
        peak = int(np.argmax(values))
        kpis.append({
            "label": f"Best {series['unit']}",
            "value": format_value(values[peak]),
            "note": series["labels"][peak],
        })

    top_chart = next((c for c in charts if c["id"] == "cat_primary"), None)
    if top_chart:
        share = top_chart["shares"][0] if top_chart.get("shares") else None
        if metric and agg == "mean":
            note = f"Highest average {metric}"
        elif share is not None:
            note = f"{share:.0f}% of " + (f"total {metric}" if metric else "records")
        else:
            note = f"Leading {category}"
        kpis.append({
            "label": f"Top {category}",
            "value": top_chart["labels"][0],
            "note": note,
        })

    if series is not None and len(series["values"]) >= 3 and series["values"][-2]:
        last, prev = series["values"][-1], series["values"][-2]
        change = (last - prev) / abs(prev) * 100
        arrow = "▲" if change > 0 else ("▼" if change < 0 else "■")
        kpis.append({
            "label": f"Latest {series['unit']} change",
            "value": f"{arrow} {abs(change):.1f}%",
            "note": f"{series['labels'][-1]} vs {series['labels'][-2]}",
        })

    kpis.append({
        "label": "Data completeness",
        "value": f"{quality['completeness']:.1f}%",
        "note": (
            f"{quality['missing_cells']:,} missing cells · "
            f"{quality['duplicate_rows']:,} duplicate rows"
        ),
    })
    return kpis[:6]


def _quality(df):
    missing = int(df.isna().sum().sum())
    by_column = df.isna().sum()
    by_column = by_column[by_column > 0].sort_values(ascending=False)
    return {
        "completeness": 100 * (1 - missing / max(1, df.size)),
        "missing_cells": missing,
        "duplicate_rows": int(df.duplicated().sum()),
        "worst_columns": [
            (str(c), int(n), float(n / max(1, len(df)) * 100))
            for c, n in by_column.head(5).items()
        ],
    }


def _observations(plan, charts, series, quality):
    """Short findings with a suggested action, drawn from the computed charts."""
    metric = plan["metric"]
    out = []

    top = next((c for c in charts if c["id"] == "cat_primary"), None)
    if top and top.get("shares"):
        share = top["shares"][0]
        if share >= 50:
            out.append((
                f"{top['labels'][0]} contributes {share:.0f}% of total {metric}, "
                "which concentrates the result in one segment.",
                "Check how dependent the business is on this segment and whether others can grow.",
            ))
        else:
            out.append((
                f"{metric} is spread across segments: the largest, "
                f"{top['labels'][0]}, holds {share:.0f}%.",
                "Compare the leading and trailing segments to find what separates them.",
            ))
    elif top and metric:
        out.append((top["takeaway"], "Investigate what sets the leading segment apart."))

    if series is not None and len(series["values"]) >= 3 and series["values"][-2]:
        last, prev = series["values"][-1], series["values"][-2]
        change = (last - prev) / abs(prev) * 100
        out.append((
            f"{metric} in {series['labels'][-1]} is {_move(change)} compared "
            f"with {series['labels'][-2]}.",
            "Look for the segments or events behind the change before reacting.",
        ))

    for finding, action in plan["insights"]:
        lowered = finding.lower()
        if "outside the normal range" in lowered or (
            "averages" in lowered and "median" in lowered
        ):
            out.append((finding, action))

    relation = next((c for c in charts if c["id"] == "relationship"), None)
    if relation:
        out.append((
            f"{relation['x_label']} and {metric} tend to move together "
            f"(r = {relation['r']:+.2f}).",
            f"Check whether {relation['x_label']} is something you can influence, "
            f"or only moves alongside {metric}.",
        ))

    if quality["missing_cells"] or quality["duplicate_rows"]:
        out.append((
            f"Data quality: {quality['missing_cells']:,} missing cells and "
            f"{quality['duplicate_rows']:,} duplicate rows.",
            "Use the Data Preparation page, then re-run the dashboard on the cleaned data.",
        ))
    return out[:6]


def _notes(df, plan, agg, series_notes, quality):
    notes = []
    if plan["metric"]:
        how = "summed" if agg == "sum" else "averaged"
        notes.append(
            f"Primary measure chosen automatically: {plan['metric']} (values are {how} "
            "because that is the meaningful way to combine this kind of measure)."
        )
    else:
        notes.append(
            "No suitable numeric business measure was found, so charts show record counts."
        )
    notes.extend(series_notes)
    if len(df) < 30:
        notes.append("The dataset is small (fewer than 30 records); treat patterns as indicative only.")
    for column, count, pct in quality["worst_columns"]:
        if pct >= 20:
            notes.append(f"'{column}' is missing in {pct:.0f}% of records; results using it may be unreliable.")
    identifiers = plan["columns"]["identifiers"]
    if identifiers:
        notes.append(
            "Identifier fields were excluded from analysis: "
            + ", ".join(map(str, identifiers[:6]))
            + ("…" if len(identifiers) > 6 else "")
            + "."
        )
    return notes


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------

def build_dashboard(df, plan, source_name="Dataset"):
    """Return the full dashboard spec for a dataframe and its plan."""
    metric = plan["metric"]
    category = plan["category"]
    agg = aggregation_for(metric) if metric else None
    skipped = []

    def attempt(label, builder):
        try:
            return builder()
        except Exception as error:  # one broken chart must not break the page
            skipped.append(f"The '{label}' chart was skipped ({type(error).__name__}).")
            return None

    series = None
    if metric and plan["date_column"]:
        series = attempt("trend", lambda: _period_series(df, plan["date_column"], metric, agg))

    charts = []
    if series is not None:
        trend = attempt("trend", lambda: _trend_chart(series, metric, agg))
        if trend:
            charts.append(trend)

    if category:
        chart = attempt("category", lambda: _category_chart(df, category, metric, agg, "cat_primary"))
        if chart:
            charts.append(chart)

    others = [c for c in plan.get("categories", []) if c != category]
    if others:
        chart = attempt("second category", lambda: _category_chart(df, others[0], metric, agg, "cat_secondary"))
        if chart:
            charts.append(chart)

    if metric:
        chart = attempt("distribution", lambda: _distribution_chart(df, metric))
        if chart:
            charts.append(chart)
        chart = attempt(
            "relationship",
            lambda: _relationship_chart(df, metric, plan.get("metrics", [])),
        )
        if chart:
            charts.append(chart)

    quality = _quality(df)
    date_range = None
    if plan["date_column"]:
        dates = to_datetime(df[plan["date_column"]]).dropna()
        if not dates.empty:
            date_range = f"{dates.min():%d %b %Y} – {dates.max():%d %b %Y}"

    domain = plan["domain"]
    domain_name = domain["domain"]
    title = (
        "Business Performance Dashboard"
        if domain_name.startswith("General")
        else f"{domain_name} Dashboard"
    )

    return {
        "title": title,
        "source_name": source_name,
        "domain": domain_name,
        "confidence": domain["confidence"],
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "date_range": date_range,
        "metric": metric,
        "aggregation": agg,
        "generated": datetime.now().strftime("%d %B %Y, %H:%M"),
        "kpis": _build_kpis(df, plan, series, charts, quality),
        "charts": charts,
        "observations": _observations(plan, charts, series, quality),
        "notes": _notes(df, plan, agg, (series or {}).get("notes", []), quality) + skipped,
        "quality": quality,
    }
