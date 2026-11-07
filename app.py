"""DataPilot AI Streamlit application entry point."""

import io
import hashlib

import pandas as pd
import streamlit as st

from business_analyst import analyze_business_context
from cleaning import CATEGORICAL_STRATEGIES, NUMERIC_STRATEGIES, clean_dataset
from columns import profile_columns, primary_metric
from engine.dashboard import build_dashboard
from engine.planner import plan_dashboard
from engine.render_image import dashboard_jpg, dashboard_pdf, dashboard_png
from engine.visuals import build_interactive_charts
from insights import generate_insights
from reports import build_excel, build_html_report
from theme import (
    PALETTES,
    brand,
    credits,
    feature_grid,
    footer,
    hero,
    inject_css,
    insight_card,
    section,
    step,
)

NAVIGATION = (
    "Dataset Workspace",
    "Data Preparation",
    "Business Intelligence",
    "AI Business Insights",
    "Report Exports",
    "About DataPilot AI",
)

st.set_page_config(
    page_title="DataPilot AI | Business Intelligence",
    page_icon="📊",
    layout="wide",
)

with st.sidebar:
    brand()
    step("Workspace navigation")
    page = st.radio(
        "Navigate",
        NAVIGATION,
        label_visibility="collapsed",
        key="main_navigation",
    )
    st.divider()
    with st.expander("Appearance & cleaning controls", expanded=False):
        palette_name = st.selectbox(
            "Dashboard palette",
            list(PALETTES),
            key="dashboard_palette",
        )
        numeric_strategy = st.selectbox(
            "Fill missing numbers with",
            NUMERIC_STRATEGIES,
            index=0,
            key="numeric_strategy",
        )
        categorical_strategy = st.selectbox(
            "Fill missing text with",
            CATEGORICAL_STRATEGIES,
            index=0,
            key="categorical_strategy",
        )
        drop_duplicates = st.checkbox(
            "Remove duplicate rows",
            value=True,
            key="drop_duplicates",
        )
        trim_text = st.checkbox(
            "Trim text values",
            value=True,
            key="trim_text",
        )
    colors = PALETTES[palette_name]
    inject_css(colors)
    st.caption("CSV and .xlsx workbooks are supported.")

hero(
    "Business intelligence, made clear.",
    "A focused workspace to understand business data, improve its quality, "
    "and turn analysis into clear decisions.",
    ("Data understanding", "Business intelligence", "Dashboard exports"),
)

section(page)
with st.container(border=True):
    st.markdown("**Dataset workspace**")
    st.caption("Upload a CSV or Excel .xlsx workbook to begin or switch datasets.")
    uploaded_file = st.file_uploader(
        "Choose a dataset",
        type=["csv", "xlsx"],
        help="Legacy .xls files are not supported.",
        label_visibility="collapsed",
        key="dataset_upload",
    )

if uploaded_file is None:
    if page == "About DataPilot AI":
        section("Built for confident analysis")
        st.markdown(
            "DataPilot AI helps business analysts, consultants, recruiters, "
            "and enterprise teams move from raw tables to an understandable "
            "business view. Its current recommendations and domain cues are "
            "generated from the existing statistical and heuristic modules."
        )
        feature_grid([
            ("◫", "Understand data", "Review column roles, completeness, and sample values."),
            ("↗", "Explore performance", "Select business measures and inspect interactive charts."),
            ("⇩", "Share findings", "Export a complete dashboard as PDF, image, or interactive HTML."),
        ])
        credits()
    else:
        st.markdown(
            '<div class="dp-welcome"><div class="dp-welcome-mark">D</div>'
            '<div class="dp-welcome-title">A clearer view of your business data.</div>'
            '<div class="dp-welcome-copy">Upload a dataset above to start with '
            'a quality profile, then prepare and explore it in one workspace.</div></div>',
            unsafe_allow_html=True,
        )
        feature_grid([
            ("01", "Profile", "See data types, analytical roles, missing values, and sample records."),
            ("02", "Prepare", "Preview a cleaned copy with transparent choices for missing values."),
            ("03", "Discover", "Explore KPIs, charts, business insights, and downloadable dashboards."),
        ])
        st.caption("Supported formats: CSV and .xlsx. Your original uploaded data is kept unchanged.")
    footer()
    st.stop()

try:
    file_bytes = uploaded_file.getvalue()
    if uploaded_file.name.lower().endswith(".csv"):
        try:
            source_df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8")
        except UnicodeDecodeError:
            source_df = pd.read_csv(io.BytesIO(file_bytes), encoding="latin-1")
    else:
        source_df = pd.read_excel(io.BytesIO(file_bytes))
except Exception as error:
    st.error(f"Could not read {uploaded_file.name}: {error}")
    footer()
    st.stop()

if source_df.empty:
    st.error("The uploaded file contains no data rows.")
    footer()
    st.stop()

if len(source_df.columns) == 0:
    st.error("The uploaded file contains no columns.")
    footer()
    st.stop()

cleaning_signature = (
    hashlib.md5(file_bytes).hexdigest(),
    numeric_strategy,
    categorical_strategy,
    drop_duplicates,
    trim_text,
)
applied_cleaning = st.session_state.get("applied_cleaning")
if applied_cleaning and applied_cleaning["signature"] == cleaning_signature:
    cleaned_df = applied_cleaning["data"]
    cleaning_log = applied_cleaning["log"]
else:
    cleaned_df = source_df.copy()
    cleaning_log = pd.DataFrame(columns=["Column", "Action", "Records affected"])

if page == "Dataset Workspace":
    file_type = uploaded_file.name.rsplit(".", 1)[-1].upper()
    section(
        "Workspace overview",
        f"{uploaded_file.name} · {file_type} file",
    )
    overview_columns = st.columns(4)
    overview = (
        ("Records", f"{len(source_df):,}"),
        ("Columns", f"{len(source_df.columns):,}"),
        ("Missing cells", f"{int(source_df.isna().sum().sum()):,}"),
        ("Duplicate rows", f"{int(source_df.duplicated().sum()):,}"),
    )
    for column, (label, value) in zip(overview_columns, overview):
        with column:
            st.metric(label, value)

    column_roles = profile_columns(source_df)
    memory_mb = source_df.memory_usage(index=True, deep=True).sum() / (1024 ** 2)
    detail_columns = st.columns(3)
    with detail_columns[0]:
        st.metric("Numerical columns", len(column_roles["numeric"]))
        st.caption(", ".join(map(str, column_roles["numeric"])) or "None detected")
    with detail_columns[1]:
        st.metric("Categorical columns", len(column_roles["categorical"]))
        st.caption(", ".join(map(str, column_roles["categorical"])) or "None detected")
    with detail_columns[2]:
        st.metric("Memory usage", f"{memory_mb:.2f} MB")

    section("Data preview", "Inspect a configurable sample of the uploaded file.")
    preview_rows = st.number_input(
        "Rows to preview",
        min_value=1,
        max_value=max(1, min(500, len(source_df))),
        value=min(25, len(source_df)),
        step=5,
        key="workspace_preview_rows",
    )
    st.dataframe(
        source_df.head(int(preview_rows)),
        width="stretch",
        hide_index=True,
    )

    section("Column profile", "Types, completeness, uniqueness, and example values.")
    profile_rows = []
    for column in source_df.columns:
        series = source_df[column]
        profile_rows.append({
            "Column": str(column),
            "Data type": str(series.dtype),
            "Role": next(
                (
                    role
                    for role in (
                        "financial", "numeric", "categorical",
                        "dates", "identifiers", "text",
                    )
                    if column in column_roles[role]
                ),
                "unclassified",
            ),
            "Missing": int(series.isna().sum()),
            "Missing %": round(series.isna().mean() * 100, 1),
            "Unique": int(series.nunique(dropna=True)),
            "Sample values": ", ".join(
                series.dropna().astype(str).head(3).tolist()
            ),
        })
    st.dataframe(
        pd.DataFrame(profile_rows),
        width="stretch",
        hide_index=True,
    )

elif page == "Data Preparation":
    section(
        "Data preparation",
        "Review column quality, choose cleaning options in the sidebar, then explicitly apply them.",
    )
    missing_rows = pd.DataFrame({
        "Column": source_df.columns.astype(str),
        "Data type": source_df.dtypes.astype(str).values,
        "Missing values": source_df.isna().sum().values,
        "Missing %": (source_df.isna().mean() * 100).round(1).values,
    })
    section("Missing values by column")
    st.dataframe(missing_rows, width="stretch", hide_index=True)

    st.markdown("#### Apply selected cleaning")
    st.caption(
        f"Numerical: {numeric_strategy} · Categorical: {categorical_strategy} · "
        f"Remove duplicates: {'Yes' if drop_duplicates else 'No'} · "
        f"Trim text: {'Yes' if trim_text else 'No'}"
    )
    if st.button(
        "Apply Changes",
        type="primary",
        key="apply_cleaning_changes",
    ):
        cleaned_result, log_result = clean_dataset(
            source_df,
            numeric=numeric_strategy,
            categorical=categorical_strategy,
            drop_duplicates=drop_duplicates,
            trim_text=trim_text,
        )
        st.session_state["applied_cleaning"] = {
            "signature": cleaning_signature,
            "data": cleaned_result,
            "log": log_result,
        }
        st.rerun()

    if applied_cleaning and applied_cleaning["signature"] != cleaning_signature:
        st.info("Cleaning options changed. Apply Changes to create an updated cleaned dataset.")
    elif applied_cleaning and applied_cleaning["signature"] == cleaning_signature:
        st.success("Cleaning changes have been applied to a separate copy. The uploaded source is unchanged.")
    else:
        st.info("No cleaning changes have been applied yet. The preview below is still the uploaded source.")

    comparison_columns = st.columns(2)
    with comparison_columns[0]:
        section("Before")
        st.metric("Rows", f"{len(source_df):,}")
        st.metric("Missing values", f"{int(source_df.isna().sum().sum()):,}")
        st.metric("Duplicate rows", f"{int(source_df.duplicated().sum()):,}")
    with comparison_columns[1]:
        section("After")
        st.metric("Rows", f"{len(cleaned_df):,}")
        st.metric("Missing values", f"{int(cleaned_df.isna().sum().sum()):,}")
        st.metric("Duplicate rows", f"{int(cleaned_df.duplicated().sum()):,}")

    if not cleaning_log.empty:
        section("Cleaning activity")
        st.dataframe(cleaning_log, width="stretch", hide_index=True)

    section("Cleaned dataset preview")
    st.dataframe(cleaned_df.head(50), width="stretch", hide_index=True)
    if applied_cleaning and applied_cleaning["signature"] == cleaning_signature:
        excel_report = build_excel(cleaned_df, cleaning_log)
        if excel_report is not None:
            st.download_button(
                "Download cleaned Excel workbook",
                data=excel_report,
                file_name="DataPilot_Cleaned_Data.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                key="preparation_excel_download",
            )
        else:
            st.warning("The cleaned Excel workbook could not be generated.")

elif page in ("Business Intelligence", "AI Business Insights"):
    analysis_source = st.radio(
        "Analyze",
        ("Uploaded data", "Cleaned data"),
        horizontal=True,
        key="analysis_source",
    )
    analysis_df = source_df if analysis_source == "Uploaded data" else cleaned_df
    columns = profile_columns(analysis_df)
    metric_options = columns["financial"] or columns["numeric"]
    suggested_metric = primary_metric(columns)

    if page == "Business Intelligence":
        automatic_plan = plan_dashboard(analysis_df)
        controls = st.columns(2)
        with controls[0]:
            metric = st.selectbox(
                "Performance measure",
                options=[None, *automatic_plan["metrics"]],
                format_func=lambda value: (
                    "Automatic recommendation" if value is None else str(value)
                ),
                key="bi_metric",
            )
        with controls[1]:
            category = st.selectbox(
                "Comparison segment",
                options=[None, *automatic_plan["categories"]],
                format_func=lambda value: (
                    "Automatic recommendation" if value is None else str(value)
                ),
                key="bi_category",
            )

        plan = plan_dashboard(
            analysis_df,
            metric=metric,
            category=category,
        )
        dashboard = build_dashboard(
            analysis_df,
            plan,
            source_name=uploaded_file.name,
        )
        domain = plan["domain"]

        section(
            "Business overview",
            "A guided read of the selected data, with configurable measures and segments.",
        )
        overview_columns = st.columns([1, 2])
        with overview_columns[0]:
            with st.container(border=True):
                st.markdown("**Likely business domain**")
                st.markdown(f"### {domain['domain']}")
                st.caption(
                    f"{domain['confidence']} confidence · inferred from column names"
                )
                if domain["evidence"]:
                    st.caption("Signals: " + ", ".join(domain["evidence"]))
        with overview_columns[1]:
            with st.container(border=True):
                st.markdown("**Automatically detected fields**")
                st.caption(
                    "Numerical: "
                    + (", ".join(map(str, plan["columns"]["numeric"])) or "none detected")
                )
                st.caption(
                    "Categorical: "
                    + (", ".join(map(str, plan["columns"]["categorical"])) or "none detected")
                )
                st.caption(
                    "Date: "
                    + (", ".join(map(str, plan["columns"]["dates"])) or "none detected")
                )

        section(
            "Performance indicators",
            "Measures are aggregated as totals or averages according to their business meaning.",
        )
        if dashboard["kpis"]:
            for start in range(0, len(dashboard["kpis"]), 3):
                row = st.columns(min(3, len(dashboard["kpis"]) - start))
                for column, kpi in zip(
                    row, dashboard["kpis"][start:start + 3]
                ):
                    with column:
                        st.metric(
                            kpi["label"],
                            kpi["value"],
                            help=kpi["note"],
                        )
        else:
            st.info("No reliable performance indicators could be calculated for this dataset.")

        charts = build_interactive_charts(dashboard, colors)
        section(
            "Performance analysis",
            "Ranked comparisons, time trends, distributions, and relationships are shown only when supported by the data.",
        )
        if charts:
            chart_index = 0
            while chart_index < len(charts):
                chart = charts[chart_index]
                if chart["size"] == "wide":
                    with st.container(border=True):
                        st.plotly_chart(
                            chart["figure"],
                            width="stretch",
                            key=f"bi_chart_{chart_index}_{chart['id']}",
                        )
                        st.caption(chart["takeaway"])
                    chart_index += 1
                    continue

                row = st.columns(2)
                row_charts = charts[chart_index:chart_index + 2]
                for column, row_chart in zip(row, row_charts):
                    with column:
                        with st.container(border=True):
                            st.plotly_chart(
                                row_chart["figure"],
                                width="stretch",
                                key=f"bi_chart_{chart_index}_{row_chart['id']}",
                            )
                            st.caption(row_chart["takeaway"])
                chart_index += len(row_charts)
        else:
            st.info(
                "No chart met the minimum data-quality and sample-size checks. "
                "The available fields are still summarized above."
            )

        section(
            "Data quality",
            "Quality context for interpreting the figures and deciding what to clean next.",
        )
        quality = dashboard["quality"]
        quality_columns = st.columns(4)
        for column, (label, value) in zip(
            quality_columns,
            (
                ("Completeness", f"{quality['completeness']:.1f}%"),
                ("Missing cells", f"{quality['missing_cells']:,}"),
                ("Duplicate rows", f"{quality['duplicate_rows']:,}"),
                ("Records analysed", f"{dashboard['rows']:,}"),
            ),
        ):
            with column:
                st.metric(label, value)
        if quality["worst_columns"]:
            st.dataframe(
                pd.DataFrame(
                    quality["worst_columns"],
                    columns=["Column", "Missing cells", "Missing %"],
                ),
                width="stretch",
                hide_index=True,
            )
        else:
            st.success("No missing cells were detected.")

        section("Key observations", "Evidence-led findings and suggested next steps.")
        if dashboard["observations"]:
            for number, (finding, action) in enumerate(
                dashboard["observations"],
                start=1,
            ):
                st.markdown(
                    insight_card(number, finding, action),
                    unsafe_allow_html=True,
                )
        else:
            st.info("No additional observations were supported by this dataset.")
        with st.expander("How this dashboard was built"):
            for note in dashboard["notes"]:
                st.markdown(f"- {note}")

    else:
        section("AI Business Insights", "Evidence-led statistical findings and domain cues.")
        metric_options = columns["financial"] or columns["numeric"]
        controls = st.columns(2)
        with controls[0]:
            metric = st.selectbox(
                "Metric for insights",
                options=[None, *metric_options],
                index=0 if suggested_metric is None else metric_options.index(suggested_metric) + 1,
                format_func=lambda value: (
                    "No primary metric" if value is None else str(value)
                ),
                key="insight_metric",
            )
        with controls[1]:
            category_options = columns["categorical"]
            category = st.selectbox(
                "Segment for insights",
                options=[None, *category_options],
                format_func=lambda value: (
                    "No category" if value is None else str(value)
                ),
                key="insight_category",
            )
        insights = generate_insights(
            analysis_df,
            columns,
            metric=metric,
            category=category,
        )
        for number, (finding, action) in enumerate(insights, start=1):
            st.markdown(
                insight_card(number, finding, action),
                unsafe_allow_html=True,
            )

        context = analyze_business_context(analysis_df)
        domain = context["business_domain"]
        section("Business context", "Domain detection is a column-name heuristic.")
        with st.container(border=True):
            st.markdown(
                f"**Likely domain:** {domain['domain']} "
                f"({domain['confidence']} confidence)"
            )
            if domain["evidence"]:
                st.caption("Matched fields: " + ", ".join(domain["evidence"]))
            if context["analysis_plan"]:
                st.markdown("**Suggested analyses**")
                for item in context["analysis_plan"]:
                    st.markdown(
                        f"- **{item['analysis']}** — {item['purpose']} "
                        f"Relevant columns: "
                        f"{', '.join(map(str, item['relevant_columns']))}"
                    )
            else:
                st.caption("No specific analysis-plan items matched this dataset.")

elif page == "Report Exports":
    section("Download reports", "Choose which version of the dataset to export.")
    report_source = st.radio(
        "Report data",
        ("Uploaded data", "Cleaned data"),
        horizontal=True,
        key="report_source",
    )
    report_df = source_df if report_source == "Uploaded data" else cleaned_df

    automatic_report_plan = plan_dashboard(report_df)
    report_controls = st.columns(2)
    with report_controls[0]:
        report_metric = st.selectbox(
            "Performance measure",
            options=[None, *automatic_report_plan["metrics"]],
            format_func=lambda value: (
                "Automatic recommendation" if value is None else str(value)
            ),
            key="report_metric",
        )
    with report_controls[1]:
        report_category = st.selectbox(
            "Comparison segment",
            options=[None, *automatic_report_plan["categories"]],
            format_func=lambda value: (
                "Automatic recommendation" if value is None else str(value)
            ),
            key="report_category",
        )

    report_plan = plan_dashboard(
        report_df,
        metric=report_metric,
        category=report_category,
    )
    report_dashboard = build_dashboard(
        report_df,
        report_plan,
        source_name=uploaded_file.name,
    )
    report_charts = build_interactive_charts(report_dashboard, colors)
    report_kpis = [
        (kpi["label"], kpi["value"])
        for kpi in report_dashboard["kpis"]
    ]
    report_insights = report_dashboard["observations"]
    pdf_report = dashboard_pdf(report_dashboard, colors)
    png_report = dashboard_png(report_dashboard, colors)
    jpg_report = dashboard_jpg(report_dashboard, colors)

    section(
        "Full dashboard exports",
        "PDF and image downloads preserve the dashboard layout, charts, and credits.",
    )
    export_columns = st.columns(3)
    with export_columns[0]:
        with st.container(border=True):
            st.markdown("**Dashboard PDF**")
            st.caption("A complete, print-ready dashboard with charts and findings.")
            st.download_button(
                "Download dashboard PDF",
                data=pdf_report,
                file_name="DataPilot_Dashboard.pdf",
                mime="application/pdf",
                width="stretch",
            )
    with export_columns[1]:
        with st.container(border=True):
            st.markdown("**Dashboard PNG image**")
            st.caption("High-resolution image for slides, documents, and sharing.")
            st.download_button(
                "Download dashboard PNG",
                data=png_report,
                file_name="DataPilot_Dashboard.png",
                mime="image/png",
                width="stretch",
            )
    with export_columns[2]:
        with st.container(border=True):
            st.markdown("**Dashboard JPG image**")
            st.caption("A compact image format for quick previews and sharing.")
            st.download_button(
                "Download dashboard JPG",
                data=jpg_report,
                file_name="DataPilot_Dashboard.jpg",
                mime="image/jpeg",
                width="stretch",
            )

    export_columns = st.columns(3)
    with export_columns[0]:
        with st.container(border=True):
            st.markdown("**Interactive HTML dashboard**")
            st.caption("A standalone dashboard with interactive charts and insights.")
            st.download_button(
                "Download interactive HTML",
                data=build_html_report(
                    "DataPilot AI | Business Intelligence Dashboard",
                    uploaded_file.name,
                    report_kpis,
                    report_charts,
                    report_insights,
                    colors,
                ),
                file_name="DataPilot_Dashboard.html",
                mime="text/html",
                width="stretch",
            )
    with export_columns[1]:
        with st.container(border=True):
            st.markdown("**Cleaned Excel workbook**")
            st.caption("Includes cleaned data and its cleaning activity log.")
            excel_report = build_excel(cleaned_df, cleaning_log)
            if excel_report is not None:
                st.download_button(
                    "Download Excel",
                    data=excel_report,
                    file_name="DataPilot_Cleaned_Data.xlsx",
                    mime=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                    width="stretch",
                )
            else:
                st.warning("The cleaned Excel workbook could not be generated.")

elif page == "About DataPilot AI":
    section("DataPilot AI", "Your Autonomous AI Business Analyst")
    st.markdown(
        "A premium workspace for turning business datasets into clearer "
        "profiles, interactive analysis, and shareable reports. The current "
        "business insights and domain suggestions use the project’s existing "
        "statistical and heuristic analysis."
    )
    feature_grid([
        ("◫", "Dataset workspace", "Understand structure and data quality at a glance."),
        ("✦", "Business intelligence", "Explore KPIs, trends, category performance, and relationships."),
        ("⇩", "Report exports", "Download the complete dashboard as PDF, PNG, JPG, or interactive HTML."),
    ])
    credits()

footer()
