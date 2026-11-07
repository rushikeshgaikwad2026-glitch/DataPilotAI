"""Automatic Plotly charts with one consistent, modern style."""

import pandas as pd
import numpy as np
import plotly.express as px

from columns import is_identifier, time_series, to_num

GRID = "#EDF1F7"


def _style(fig):
    fig.update_layout(
        template="plotly_white",
        height=370,
        margin=dict(l=24, r=20, t=56, b=30),
        font=dict(family="Inter, Arial, sans-serif", size=12, color="#334155"),
        title=dict(x=0.02, font=dict(size=15, color="#0F172A")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.1, x=1, xanchor="right"),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


def _grouped(df, category, metric, top):
    t = pd.DataFrame({
        category: df[category].astype("string").fillna("Unknown"),
        metric: to_num(df, metric).replace([np.inf, -np.inf], np.nan),
    }).dropna(subset=[metric])

    return (
        t.groupby(category)[metric].sum()
        .sort_values(ascending=False).head(top).reset_index()
    )


def create_charts(df, cols, colors, metric=None, category=None):
    """Return a list of {"title", "figure"} dicts (max 6)."""
    identifiers = set(cols.get("identifiers", ()))
    numeric = [
        column for column in cols.get("numeric", ())
        if column not in identifiers and not is_identifier(column)
    ]
    financial = [
        column for column in cols.get("financial", ())
        if column in numeric and column not in identifiers
    ]
    metric = metric or (financial or numeric or [None])[0]
    if metric in identifiers or is_identifier(metric):
        metric = None
    category = (
        category
        if category in cols.get("categorical", ())
        and category not in identifiers
        and not is_identifier(category)
        else None
    )
    charts = []

    def add(title, fig):
        charts.append({"title": title, "figure": _style(fig)})

    # 1. Trend over time
    if metric and cols["dates"]:
        ts = time_series(df, cols["dates"][0], metric)

        if len(ts) >= 2 and ts["Value"].nunique() >= 2:
            fig = px.line(
                ts, x="Period", y="Value", markers=True,
                title=f"{metric} over time",
                color_discrete_sequence=colors,
            )
            fig.update_traces(line_width=3)
            add("Performance trend", fig)

    # 2 & 3. Category ranking and share
    if metric and category:
        top = _grouped(df, category, metric, 12)

        if len(top) >= 2 and top[metric].nunique() >= 2:
            fig = px.bar(
                top, x=metric, y=category, orientation="h",
                title=f"{metric} by {category}",
                color_discrete_sequence=colors,
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            add("Category performance", fig)

        share = top.head(7)

        if len(share) >= 2 and share[metric].sum() > 0:
            fig = px.pie(
                share, names=category, values=metric, hole=0.55,
                title=f"Share of {metric} by {category}",
                color_discrete_sequence=colors,
            )
            fig.update_traces(textposition="inside", textinfo="percent")
            add("Contribution", fig)

    elif category:
        counts = df[category].astype("string").fillna("Unknown").value_counts()
        counts = counts.head(12).rename_axis(category).reset_index(name="Records")
        fig = px.bar(
            counts, x="Records", y=category, orientation="h",
            title=f"Records by {category}",
            color_discrete_sequence=colors,
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        add("Category breakdown", fig)

    # 4. Strongest relationship with the metric
    others = [c for c in numeric if c != metric]

    if metric and others:
        sub = pd.DataFrame(
            {
                c: to_num(df, c).replace([np.inf, -np.inf], np.nan)
                for c in [metric] + others[:7]
            }
        ).dropna(subset=[metric])
        corr = sub.corr()[metric].drop(metric).abs().dropna()

        if not corr.empty:
            partner = corr.idxmax()
            pair = sub[[partner, metric]].dropna()

            if (
                len(pair) >= 10
                and pair[partner].nunique() >= 3
                and pair[metric].nunique() >= 3
                and corr[partner] >= 0.3
            ):
                if len(pair) > 5000:
                    pair = pair.sample(5000, random_state=42)

                fig = px.scatter(
                    pair, x=partner, y=metric, opacity=0.6,
                    title=f"{partner} vs {metric}",
                    color_discrete_sequence=colors,
                )
                add("Relationship", fig)

    # 5. Distribution
    if metric:
        v = to_num(df, metric).replace([np.inf, -np.inf], np.nan).dropna()

        if len(v) >= 10 and v.nunique() >= 5:
            fig = px.histogram(
                x=v, nbins=25,
                title=f"Distribution of {metric}",
                color_discrete_sequence=colors,
            )
            fig.update_layout(
                xaxis_title=metric, yaxis_title="Records", bargap=0.05
            )
            add("Distribution", fig)

    # 6. Correlation matrix
    numeric_frame = pd.DataFrame({
        column: to_num(df, column).replace([np.inf, -np.inf], np.nan)
        for column in numeric
    })
    suitable = [
        column for column in numeric_frame.columns
        if numeric_frame[column].notna().sum() >= 10
        and numeric_frame[column].nunique(dropna=True) >= 3
    ]
    if len(suitable) >= 3:
        numeric_frame = numeric_frame[suitable]
        complete = numeric_frame.dropna()
        if len(complete) >= 10:
            corr = complete.corr()
            if corr.notna().all().all():
                fig = px.imshow(
                    corr, text_auto=".2f", aspect="auto",
                    color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                    title="Correlation matrix",
                )
                add("Correlations", fig)

    return charts[:6]


def missing_chart(df, colors):
    miss = df.isna().sum()
    miss = miss[miss > 0].sort_values(ascending=False).head(10)

    if miss.empty:
        return None

    data = pd.DataFrame({"Column": miss.index.astype(str), "Missing": miss.values})
    fig = px.bar(
        data, x="Missing", y="Column", orientation="h",
        title="Columns with the most missing values",
        color_discrete_sequence=[colors[0]],
    )
    fig.update_layout(yaxis=dict(autorange="reversed"))
    return _style(fig)
