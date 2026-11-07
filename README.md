# DataPilot AI

DataPilot AI is a Streamlit workspace for turning CSV and Excel datasets into
clear business intelligence. It profiles data quality, prepares a separate
cleaned copy, selects business measures and segments, builds evidence-led
charts and observations, and exports complete dashboards.

## Features

- Dataset overview, column profiles, missing-value checks, and duplicate checks
- Configurable data preparation that leaves the uploaded source unchanged
- Suggested business domain, measures, comparison segments, and KPIs
- Trend, segment, distribution, and relationship charts when the data supports them
- Full-dashboard PDF, PNG, and JPG exports, plus interactive HTML
- Cleaned Excel workbook with a cleaning activity log

## Run locally

Use Python 3.10 or later:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed by Streamlit and upload a CSV or `.xlsx` workbook.
Legacy `.xls` workbooks are not supported.

## Run tests

```powershell
python -m unittest discover tests -v
```

## Project layout

```text
app.py                 Streamlit application and page wiring
business_analyst.py    Business-context and domain heuristics
charts.py              Supporting Plotly chart builders
cleaning.py            Dataset cleaning operations
columns.py             Column profiling and type helpers
engine/
  dashboard.py         Shared dashboard specification and business measures
  planner.py           Metric, category, KPI, and insight selection
  render_image.py      Consistent full-dashboard PDF and image renderer
  visuals.py           Interactive Plotly charts from the dashboard spec
tests/                 Dashboard and planner regression tests
```

## Data and privacy

DataPilot AI analyzes the file supplied to the running Streamlit app. Avoid
uploading confidential or personal data to an app hosted by a third party
unless its hosting, retention, and access controls are appropriate for that
data. Local datasets, credentials, generated exports, virtual environments,
and historical source copies are excluded from Git by default.

Business-domain labels are inferred from column names, and findings are
statistical recommendations rather than guarantees of causation.

## Website direction

The current application is a working Streamlit web app. A separate custom
website can be added later without replacing the analysis engine: keep the
dashboard and data-analysis logic reusable, and introduce a dedicated web UI
or API as a separate layer when its design and hosting requirements are known.

## Credits

Designed and developed by **Rushikesh Gaikwad**  
B.E. + MBA in Marketing  
[rushikeshgaikwad2026@gmail.com](mailto:rushikeshgaikwad2026@gmail.com) ·
[+91 73876 79330](tel:+917387679330)
