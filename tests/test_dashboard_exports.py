"""Tests for dashboard selection, charts, and full-dashboard exports."""

import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.dashboard import build_dashboard  # noqa: E402
from engine.planner import plan_dashboard  # noqa: E402
from engine.render_image import dashboard_jpg, dashboard_pdf, dashboard_png  # noqa: E402
from engine.visuals import build_interactive_charts  # noqa: E402
from project_info import (  # noqa: E402
    AUTHOR_EMAIL,
    AUTHOR_NAME,
    AUTHOR_PHONE,
    AUTHOR_QUALIFICATION,
)
from reports import build_html_report  # noqa: E402


def retail_dataset(rows=60):
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "Order Date": pd.date_range("2025-01-01", periods=rows, freq="D"),
        "Region": rng.choice(["North", "South", "East", "West"], rows),
        "Product": rng.choice(["A", "B", "C"], rows),
        "Revenue": rng.uniform(100, 5000, rows).round(2),
        "Quantity": rng.integers(1, 9, rows),
    })


class DashboardExportTests(unittest.TestCase):
    def test_metric_and_category_overrides_are_respected(self):
        df = retail_dataset()

        plan = plan_dashboard(df, metric="Quantity", category="Product")

        self.assertEqual(plan["metric"], "Quantity")
        self.assertEqual(plan["category"], "Product")

    def test_interactive_charts_follow_the_dashboard_spec(self):
        df = retail_dataset()
        plan = plan_dashboard(df)
        dashboard = build_dashboard(df, plan, source_name="retail.csv")

        charts = build_interactive_charts(
            dashboard,
            ["#243B7A", "#6675E8", "#91A3F4", "#B9C9FA"],
        )

        self.assertEqual(
            [chart["id"] for chart in charts],
            [chart["id"] for chart in dashboard["charts"]],
        )
        self.assertTrue(all(chart["figure"].layout.height for chart in charts))

    def test_dashboard_exports_have_expected_file_signatures(self):
        df = retail_dataset()
        dashboard = build_dashboard(df, plan_dashboard(df), "retail.csv")
        colors = ["#243B7A", "#6675E8", "#91A3F4", "#B9C9FA"]

        self.assertTrue(dashboard_pdf(dashboard, colors).startswith(b"%PDF"))
        self.assertTrue(dashboard_png(dashboard, colors).startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertTrue(dashboard_jpg(dashboard, colors).startswith(b"\xff\xd8"))

    def test_interactive_html_includes_author_credits(self):
        df = retail_dataset()
        dashboard = build_dashboard(df, plan_dashboard(df), "retail.csv")
        charts = build_interactive_charts(
            dashboard,
            ["#243B7A", "#6675E8", "#91A3F4", "#B9C9FA"],
        )
        html = build_html_report(
            "Business Intelligence Dashboard",
            "retail.csv",
            [(kpi["label"], kpi["value"]) for kpi in dashboard["kpis"]],
            charts,
            dashboard["observations"],
            ["#243B7A", "#6675E8", "#91A3F4", "#B9C9FA"],
        ).decode("utf-8")

        self.assertIn(AUTHOR_NAME, html)
        self.assertIn(AUTHOR_EMAIL, html)
        self.assertIn(AUTHOR_PHONE, html)
        self.assertIn(AUTHOR_QUALIFICATION, html)


if __name__ == "__main__":
    unittest.main()
