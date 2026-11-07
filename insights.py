"""KPI catalogue and plain-English business insights."""

import numpy as np
import pandas as pd

from columns import time_series, to_num


def format_value(value):
    if isinstance(value, str):
        return value

    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)

    if not np.isfinite(v):
        return "N/A"

    a = abs(v)

    if a >= 1e9:
        return f"{v / 1e9:,.2f}B"
    if a >= 1e6:
        return f"{v / 1e6:,.2f}M"
    if a >= 1e4:
        return f"{v:,.0f}"
    if v == int(v):
        return f"{int(v):,}"
    return f"{v:,.2f}"


def build_kpis(df, cols):
    """Return {label: value} for every KPI the data can support."""
    missing = int(df.isna().sum().sum())

    k = {
        "Total Records": len(df),
        "Total Columns": df.shape[1],
        "Data Completeness": f"{100 * (1 - missing / max(1, df.size)):.1f}%",
        "Missing Values": missing,
        "Duplicate Rows": int(df.duplicated().sum()),
    }

    for c in cols["numeric"]:
        v = to_num(df, c).replace([np.inf, -np.inf], np.nan).dropna()

        if v.empty:
            continue

        k[f"{c} — Total"] = v.sum()
        k[f"{c} — Average"] = v.mean()
        k[f"{c} — Median"] = v.median()
        k[f"{c} — Maximum"] = v.max()
        k[f"{c} — Minimum"] = v.min()

    for c in cols["categorical"]:
        counts = df[c].value_counts(dropna=True)
        k[f"{c} — Unique Categories"] = len(counts)

        if not counts.empty:
            k[f"{c} — Largest Category"] = str(counts.index[0])

    status = next(
        (c for c in df.columns
         if any(w in str(c).lower().replace("_", " ")
                for w in ("loan status", "default"))),
        None,
    )

    if status is not None:
        flag = (
            df[status].astype(str).str.lower()
            .str.contains("default|charged off", regex=True, na=False)
        )
        if flag.any():
            k["Loan Default Rate"] = f"{flag.mean() * 100:.1f}%"

    return k


def default_kpis(catalog, metric=None):
    wanted = ["Total Records"]

    if metric:
        wanted += [f"{metric} — Total", f"{metric} — Average"]

    wanted += ["Data Completeness", "Missing Values", "Duplicate Rows"]

    return [w for w in wanted if w in catalog][:4]


def generate_insights(df, cols, metric=None, category=None):
    """Return a list of (finding, recommended_action) tuples."""
    out = []
    rows, ncols = df.shape
    missing = int(df.isna().sum().sum())
    dups = int(df.duplicated().sum())

    # 1. Data quality
    if missing or dups:
        pct = missing / max(1, df.size) * 100
        action = "Use the Data Preparation page to fix these before relying on the numbers."

        if missing:
            worst = df.isna().sum().idxmax()
            action = f"Start with '{worst}', which has the most gaps. " + action

        out.append((
            f"{rows:,} records across {ncols} columns, with {missing:,} "
            f"missing cells ({pct:.1f}%) and {dups:,} duplicate rows.",
            action,
        ))
    else:
        out.append((
            f"{rows:,} records across {ncols} columns, with no missing "
            "cells and no duplicate rows.",
            "Keep running the same checks on future imports.",
        ))

    if metric:
        v = to_num(df, metric).replace([np.inf, -np.inf], np.nan).dropna()

        # 2. Average vs median
        if len(v) >= 2:
            mean, med = v.mean(), v.median()
            skew = ""

            if med and abs(mean - med) / abs(med) > 0.15:
                skew = ", a gap that points to a skewed distribution"

            out.append((
                f"{metric} averages {format_value(mean)} with a median of "
                f"{format_value(med)}{skew}.",
                "Prefer the median when a few extreme records distort the average.",
            ))

        # 3. Outliers
        if len(v) >= 10:
            q1, q3 = v.quantile(0.25), v.quantile(0.75)
            iqr = q3 - q1

            if iqr > 0:
                n_out = int(((v < q1 - 1.5 * iqr) | (v > q3 + 1.5 * iqr)).sum())

                if n_out:
                    out.append((
                        f"{n_out:,} records in {metric} fall outside the "
                        "normal range (1.5 × IQR).",
                        "Check whether they are genuine exceptional events "
                        "or data-entry errors.",
                    ))

        # 4. Leading segment
        if category:
            grouped = (
                v.groupby(df.loc[v.index, category].astype(str))
                .sum().sort_values(ascending=False)
            )

            if len(grouped) >= 2 and grouped.sum() != 0:
                share = grouped.iloc[0] / grouped.sum() * 100
                out.append((
                    f"{grouped.index[0]} is the largest {category} segment, "
                    f"contributing {share:.1f}% of total {metric}.",
                    "Find out what drives the leader and whether it can be "
                    "replicated elsewhere.",
                ))

        # 5. Latest trend
        if cols["dates"]:
            ts = time_series(df, cols["dates"][0], metric)

            if len(ts) >= 3 and ts["Value"].iloc[-2]:
                last, prev = ts["Value"].iloc[-1], ts["Value"].iloc[-2]
                change = (last - prev) / abs(prev) * 100
                label = ts["Period"].iloc[-1].strftime("%b %Y")

                out.append((
                    f"{metric} in the latest period ({label}) is "
                    f"{change:+.1f}% versus the period before. "
                    "The latest period may be incomplete.",
                    "Confirm the latest period is complete before reading "
                    "too much into the change.",
                ))

        # 6. Strongest relationship
        others = [c for c in cols["numeric"] if c != metric][:7]

        if others:
            corr = (
                df[[metric] + others]
                .apply(pd.to_numeric, errors="coerce")
                .replace([np.inf, -np.inf], np.nan)
                .corr()[metric].drop(metric).dropna()
            )

            if not corr.empty:
                best = corr.abs().idxmax()
                out.append((
                    f"{metric} and {best} have a correlation of "
                    f"{corr[best]:.2f}. Correlation does not prove causation.",
                    "Validate the relationship with business context before "
                    "acting on it.",
                ))

    if rows < 30:
        out.append((
            "The dataset is small, so findings are exploratory.",
            "Collect more observations before making major decisions.",
        ))

    return out[:7]
