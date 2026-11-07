"""Dashboard planning: the single place that decides what to analyse.

`plan_dashboard(df)` chooses the primary metric, the category, the date field,
the KPIs and the insights. The Business Intelligence page and every export use
this same plan, so they can never disagree with each other.

This module has no UI and no plotting dependencies.
"""

import numpy as np
import pandas as pd

from business_analyst import analyze_business_context
from columns import _has, _tokens, is_identifier, profile_columns, time_series
from insights import build_kpis, format_value, generate_insights

MAX_KPIS = 4

# Measures that describe a side-effect of a sale rather than business performance.
INCIDENTAL_TOKENS = {
    "discount", "tax", "shipping", "freight", "fee", "refund",
    "rebate", "tip", "coupon", "postage",
}
# Measures that usually represent the main business outcome.
PRIMARY_TOKENS = {
    "revenue", "sales", "profit", "income", "salary", "turnover",
    "spend", "expense", "cost", "balance", "payment", "budget",
}


def _is_incidental(column):
    return _has(_tokens(column)[1], INCIDENTAL_TOKENS)


def _is_primary(column):
    return _has(_tokens(column)[1], PRIMARY_TOKENS)


def _metric_candidates(df, columns, planned_columns):
    """Numeric business measures, best first. Identifiers are excluded."""
    identifiers = set(columns["identifiers"])
    numeric = [
        column
        for column in dict.fromkeys(columns["financial"] + columns["numeric"])
        if column not in identifiers and not is_identifier(column)
    ]

    usable = []
    for column in numeric:
        values = pd.to_numeric(df[column], errors="coerce")
        finite = values.loc[np.isfinite(values)]
        if len(finite) >= 2 and finite.nunique() >= 2:
            usable.append(column)

    usable.sort(
        key=lambda column: (
            not _is_incidental(column),
            column in planned_columns,
            _is_primary(column),
            column in columns["financial"],
        ),
        reverse=True,
    )
    return usable


def _category_candidates(df, columns, planned_columns):
    """Low-cardinality categorical fields, best first."""
    identifiers = set(columns["identifiers"])
    max_values = min(12, max(2, len(df) // 2))

    usable = [
        column
        for column in columns["categorical"]
        if column not in identifiers
        and not is_identifier(column)
        and 2 <= df[column].nunique(dropna=True) <= max_values
    ]
    usable.sort(
        key=lambda column: (
            column in planned_columns,
            4 <= df[column].nunique(dropna=True) <= 10,
            -abs(df[column].nunique(dropna=True) - 6),
        ),
        reverse=True,
    )
    return usable


def _date_candidates(df, columns, metric, planned_columns):
    """(date_column, trend_frame) pairs that can support a trend chart."""
    if metric is None:
        return []

    found = []
    for date_column in columns["dates"]:
        trend = time_series(df, date_column, metric)
        if len(trend) >= 2 and trend["Value"].nunique() >= 2:
            found.append((date_column, trend))

    found.sort(key=lambda item: item[0] in planned_columns, reverse=True)
    return found


def _select_kpis(df, columns, domain, metric, category):
    """Pick up to MAX_KPIS (label, formatted value) pairs."""
    catalog = build_kpis(df, columns)

    wanted = ["Total Records"]
    if domain["domain"] == "Loan and Credit Risk" and "Loan Default Rate" in catalog:
        wanted.append("Loan Default Rate")
    if metric is not None:
        wanted.extend([f"{metric} — Total", f"{metric} — Average"])
    if category is not None:
        wanted.append(f"{category} — Largest Category")
    wanted.extend([
        "Data Completeness", "Missing Values", "Duplicate Rows", "Total Columns",
    ])

    pairs, seen = [], set()
    for name in wanted:
        if name in seen or name not in catalog:
            continue
        label = str(name).strip()
        value = format_value(catalog[name]).strip()
        if not label or not value or value == "N/A":
            continue
        pairs.append((label, value))
        seen.add(name)
        if len(pairs) == MAX_KPIS:
            break
    return pairs


def plan_dashboard(df, metric=None, category=None):
    """Return everything the dashboard and exports need, as plain data.

    Optional metric and category values let a user override the automatic
    recommendations without allowing identifier or unusable fields.
    """
    columns = profile_columns(df)
    context = analyze_business_context(df)
    domain = context["business_domain"]

    planned_columns = {
        column
        for item in context["analysis_plan"]
        for column in item["relevant_columns"]
    }

    metrics = _metric_candidates(df, columns, planned_columns)
    metric = metric if metric in metrics else (metrics[0] if metrics else None)

    categories = _category_candidates(df, columns, planned_columns)
    category = (
        category
        if category in categories
        else (categories[0] if categories else None)
    )

    dates = _date_candidates(df, columns, metric, planned_columns)
    date_column = dates[0][0] if dates else None
    trend = dates[0][1] if dates else None

    chart_roles = dict(columns)
    chart_roles["dates"] = [date_column] if date_column else []

    return {
        "columns": columns,
        "domain": domain,
        "analysis_plan": context["analysis_plan"],
        "metric": metric,
        "category": category,
        "date_column": date_column,
        "trend": trend,
        "chart_roles": chart_roles,
        "metrics": metrics,
        "categories": categories,
        "kpis": _select_kpis(df, columns, domain, metric, category),
        "insights": generate_insights(df, columns, metric=metric, category=category),
    }
