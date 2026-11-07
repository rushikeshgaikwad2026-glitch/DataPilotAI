"""Chart assembly shared by the dashboard and every export."""

import plotly.graph_objects as go

from charts import create_charts, missing_chart


def build_interactive_charts(spec, colors):
    """Build consistently sized Plotly charts from the dashboard specification."""
    palette = list(colors) or ["#243B7A", "#6675E8"]
    charts = []

    for chart in spec["charts"]:
        figure = go.Figure()
        kind = chart["kind"]

        if kind == "line":
            figure.add_trace(go.Scatter(
                x=chart["x"],
                y=chart["y"],
                mode="lines+markers",
                name=chart["y_label"],
                line=dict(color=palette[0], width=3),
                marker=dict(color=palette[0], size=7),
                hovertemplate="%{x}<br>%{y:,.3g}<extra></extra>",
            ))
            if chart.get("y_smooth"):
                figure.add_trace(go.Scatter(
                    x=chart["x"],
                    y=chart["y_smooth"],
                    mode="lines",
                    name="3-period average",
                    line=dict(color=palette[1], width=2, dash="dash"),
                    connectgaps=False,
                    hovertemplate="%{x}<br>%{y:,.3g}<extra></extra>",
                ))
            figure.update_yaxes(title_text=chart["y_label"])
            figure.update_xaxes(title_text="Period")
            figure.update_layout(hovermode="x unified")

        elif kind == "bar":
            values = chart["values"]
            figure.add_trace(go.Bar(
                x=values,
                y=chart["labels"],
                orientation="h",
                marker_color=[palette[0]] + [palette[1]] * (len(values) - 1),
                text=[f"{value:,.4g}" for value in values],
                textposition="outside",
                cliponaxis=False,
                customdata=chart.get("shares"),
                hovertemplate=(
                    "%{y}<br>%{x:,.4g}"
                    "%{customdata:.1f}%<extra></extra>"
                    if chart.get("shares") is not None
                    else "%{y}<br>%{x:,.4g}<extra></extra>"
                ),
            ))
            figure.update_yaxes(
                title_text=None,
                categoryorder="array",
                categoryarray=list(reversed(chart["labels"])),
            )
            figure.update_xaxes(title_text=chart["value_label"], rangemode="tozero")
            figure.update_layout(bargap=0.28)

        elif kind == "hist":
            edges = chart["edges"]
            centers = [(left + right) / 2 for left, right in zip(edges, edges[1:])]
            widths = [right - left for left, right in zip(edges, edges[1:])]
            figure.add_trace(go.Bar(
                x=centers,
                y=chart["counts"],
                width=widths,
                name="Records",
                marker_color=palette[1],
                hovertemplate="%{x:,.4g}<br>%{y:,} records<extra></extra>",
            ))
            figure.add_vline(
                x=chart["median"],
                line_color=palette[0],
                line_dash="dash",
                annotation_text="Median",
                annotation_position="top",
            )
            if chart["mean"] != chart["median"]:
                figure.add_vline(
                    x=chart["mean"],
                    line_color="#F59E0B",
                    line_dash="dot",
                    annotation_text="Average",
                    annotation_position="top",
                )
            figure.update_xaxes(title_text=chart["x_label"])
            figure.update_yaxes(title_text="Records")
            figure.update_layout(bargap=0.04)

        elif kind == "scatter":
            figure.add_trace(go.Scatter(
                x=chart["x"],
                y=chart["y"],
                mode="markers",
                name="Records",
                marker=dict(color=palette[1], size=7, opacity=0.55),
                hovertemplate="%{x:,.4g}<br>%{y:,.4g}<extra></extra>",
            ))
            figure.add_trace(go.Scatter(
                x=[point[0] for point in chart["fit"]],
                y=[point[1] for point in chart["fit"]],
                mode="lines",
                name="Linear fit",
                line=dict(color=palette[0], width=2),
                hoverinfo="skip",
            ))
            figure.update_xaxes(title_text=chart["x_label"])
            figure.update_yaxes(title_text=chart["y_label"])
            figure.update_layout(hovermode="closest")

        else:
            raise ValueError(f"Unsupported dashboard chart type: {kind}")

        figure.update_layout(
            template="plotly_white",
            height=390 if chart["size"] == "wide" else 350,
            margin=dict(l=18, r=34, t=48, b=36),
            title=dict(
                text=chart["title"],
                x=0.02,
                xanchor="left",
                font=dict(size=15, color="#0F172A"),
            ),
            font=dict(family="Inter, Arial, sans-serif", size=11, color="#334155"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=1.12, x=1, xanchor="right"),
            showlegend=kind in {"line", "hist", "scatter"},
        )
        figure.update_xaxes(gridcolor="#EDF1F7", zeroline=False)
        figure.update_yaxes(gridcolor="#EDF1F7", zeroline=False)
        charts.append({
            "id": chart["id"],
            "title": chart["title"],
            "size": chart["size"],
            "takeaway": chart["takeaway"],
            "figure": figure,
        })

    return charts


def build_chart_set(df, plan, colors):
    """Return the dashboard's charts ({"title", "figure"} dicts) for a plan."""
    charts = create_charts(
        df,
        plan["chart_roles"],
        colors,
        metric=plan["metric"],
        category=plan["category"],
    )
    charts = [chart for chart in charts if chart["title"] != "Contribution"]

    missing_figure = missing_chart(df, colors)
    if missing_figure is not None:
        charts.append({"title": "Missing values", "figure": missing_figure})
    return charts


def explain_chart(title, plan):
    """One-sentence business explanation shown beneath a chart."""
    metric = plan["metric"]
    category = plan["category"]

    if title == "Performance trend":
        return f"Shows the sum of {metric} across {plan['date_column']} periods."
    if title == "Category performance":
        return f"Compares summed {metric} across the leading values of {category}."
    if title == "Category breakdown":
        return (
            f"Counts records in the leading values of {category}; "
            "no suitable numeric metric was detected."
        )
    if title == "Relationship":
        return (
            "Each point represents a record with non-missing values for the "
            "displayed numeric fields; the chart highlights their observed "
            "association, not causation."
        )
    if title == "Distribution":
        return (
            f"Groups observed {metric} values into bins to show their "
            "frequency distribution."
        )
    if title == "Correlations":
        return (
            "Shows pairwise Pearson correlations for the available numeric "
            "fields; correlation does not establish causation."
        )
    if title == "Missing values":
        return "Shows the columns with the highest counts of missing values."
    return "Interactive view of a pattern identified from the available dataset fields."
