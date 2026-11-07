"""Regression tests for the dashboard planner.

Run from the project root:
    python -m unittest discover tests -v
"""

import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.planner import plan_dashboard  # noqa: E402


def retail(discount_first=False, rows=60):
    rng = np.random.default_rng(7)
    data = {
        "Order ID": np.arange(1000, 1000 + rows),
        "Order Date": pd.date_range("2025-01-01", periods=rows, freq="D"),
        "Region": rng.choice(["North", "South", "East", "West"], rows),
        "Product": rng.choice(["A", "B", "C"], rows),
        "Postal Code": rng.integers(400001, 411999, rows),
        "Quantity": rng.integers(1, 9, rows),
        "Revenue": rng.uniform(100, 5000, rows).round(2),
        "Discount Amount": rng.uniform(0, 50, rows).round(2),
    }
    df = pd.DataFrame(data)
    if discount_first:
        cols = ["Discount Amount"] + [c for c in df.columns if c != "Discount Amount"]
        df = df[cols]
    return df


class PlannerTests(unittest.TestCase):
    def assert_clean_plan(self, plan):
        """Invariants that must hold for every dataset."""
        for label, value in plan["kpis"]:
            self.assertTrue(label.strip())
            self.assertTrue(value.strip())
            self.assertNotEqual(value, "N/A")
        self.assertLessEqual(len(plan["kpis"]), 4)
        self.assertGreaterEqual(len(plan["kpis"]), 1)
        self.assertNotIn(plan["metric"], plan["columns"]["identifiers"])
        self.assertNotIn(plan["category"], plan["columns"]["identifiers"])

    def test_retail_basic(self):
        plan = plan_dashboard(retail())
        self.assert_clean_plan(plan)
        self.assertEqual(plan["metric"], "Revenue")
        self.assertEqual(plan["date_column"], "Order Date")
        self.assertIsNotNone(plan["trend"])
        self.assertEqual(plan["domain"]["domain"], "Sales and Retail")

    def test_postal_code_and_order_id_never_become_measures(self):
        plan = plan_dashboard(retail())
        self.assertNotEqual(plan["metric"], "Postal Code")
        self.assertNotEqual(plan["metric"], "Order ID")
        self.assertIn("Postal Code", plan["columns"]["identifiers"])
        self.assertIn("Order ID", plan["columns"]["identifiers"])

    def test_revenue_beats_discount_regardless_of_column_order(self):
        plan = plan_dashboard(retail(discount_first=True))
        self.assertEqual(plan["metric"], "Revenue")

    def test_hr_dataset(self):
        rng = np.random.default_rng(3)
        n = 50
        df = pd.DataFrame({
            "Employee ID": np.arange(1, n + 1),
            "Department": rng.choice(["Sales", "IT", "HR", "Ops"], n),
            "Salary": rng.integers(30000, 120000, n),
            "Tenure": rng.integers(1, 15, n),
            "Attrition": rng.choice(["Yes", "No"], n),
        })
        plan = plan_dashboard(df)
        self.assert_clean_plan(plan)
        self.assertEqual(plan["domain"]["domain"], "Human Resources")
        self.assertEqual(plan["metric"], "Salary")
        self.assertIsNone(plan["trend"])

    def test_small_dataset(self):
        df = pd.DataFrame({
            "Product": ["A", "B", "A", "C", "B"],
            "Sales": [10.0, 20.0, 15.0, 30.0, 25.0],
        })
        plan = plan_dashboard(df)
        self.assert_clean_plan(plan)
        self.assertEqual(plan["metric"], "Sales")

    def test_identifier_heavy_dataset(self):
        n = 40
        df = pd.DataFrame({
            "Customer ID": np.arange(1, n + 1),
            "Account ID": np.arange(5000, 5000 + n),
            "Phone Number": np.arange(9000000000, 9000000000 + n),
            "ZIP Code": np.arange(10000, 10000 + n),
            "Amount": np.linspace(10, 500, n),
        })
        plan = plan_dashboard(df)
        self.assert_clean_plan(plan)
        self.assertEqual(plan["metric"], "Amount")

    def test_no_numeric_measure(self):
        df = pd.DataFrame({"City": ["Pune", "Mumbai", "Pune", "Delhi"] * 5})
        plan = plan_dashboard(df)
        self.assertIsNone(plan["metric"])
        self.assertIsNone(plan["trend"])
        self.assertGreaterEqual(len(plan["kpis"]), 1)

    def test_constant_date_gives_no_trend(self):
        df = retail()
        df["Order Date"] = pd.Timestamp("2025-03-01")
        plan = plan_dashboard(df)
        self.assertIsNone(plan["date_column"])
        self.assertEqual(plan["chart_roles"]["dates"], [])

    def test_nulls_and_infinite_values(self):
        df = retail()
        df.loc[3, "Revenue"] = np.inf
        df.loc[4, "Revenue"] = -np.inf
        df.loc[5:9, "Revenue"] = np.nan
        plan = plan_dashboard(df)
        self.assert_clean_plan(plan)
        self.assertEqual(plan["metric"], "Revenue")

    def test_source_dataframe_is_not_modified(self):
        df = retail()
        before = df.copy(deep=True)
        plan_dashboard(df)
        pd.testing.assert_frame_equal(df, before)


if __name__ == "__main__":
    unittest.main()
