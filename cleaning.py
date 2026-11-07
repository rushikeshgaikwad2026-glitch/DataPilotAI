"""Data cleaning. The original DataFrame is never modified."""

import pandas as pd

from columns import is_text

NUMERIC_STRATEGIES = ("Median", "Mean", "Leave missing")
CATEGORICAL_STRATEGIES = ("Unknown", "Most frequent", "Leave missing")
LOG_COLUMNS = ["Column", "Action", "Records affected"]


def clean_dataset(
    df,
    numeric="Median",
    categorical="Unknown",
    drop_duplicates=True,
    trim_text=True,
):
    """Return (cleaned_df, log_df)."""
    out = df.copy()
    log = []

    def note(column, action, count):
        log.append({
            "Column": str(column),
            "Action": action,
            "Records affected": int(count),
        })

    text_cols = [c for c in out.columns if is_text(out[c])]

    # 1. Tidy text: trim spaces, turn blank strings into real missing values.
    for col in text_cols:
        if isinstance(out[col].dtype, pd.CategoricalDtype):
            out[col] = out[col].astype(object)

        if trim_text:
            padded = out[col].map(
                lambda v: isinstance(v, str) and v != v.strip()
            ).astype(bool)

            if padded.any():
                out[col] = out[col].map(
                    lambda v: v.strip() if isinstance(v, str) else v
                )
                note(col, "Trimmed leading/trailing spaces", padded.sum())

        blank = out[col].map(
            lambda v: isinstance(v, str) and v.strip() == ""
        ).astype(bool)

        if blank.any():
            out.loc[blank, col] = pd.NA
            note(col, "Converted blank cells to missing", blank.sum())

    # 2. Remove duplicates first so they don't skew fill values.
    if drop_duplicates:
        before = len(out)
        out = out.drop_duplicates()
        if len(out) < before:
            note("Entire dataset", "Removed duplicate rows", before - len(out))

    # 3. Fill missing numbers.
    for col in out.select_dtypes(include="number").columns:
        missing = int(out[col].isna().sum())

        if not missing or numeric == "Leave missing":
            continue

        fill = out[col].median() if numeric == "Median" else out[col].mean()

        if pd.notna(fill):
            out[col] = out[col].fillna(fill)
            note(col, f"Filled missing values with {numeric.lower()}", missing)

    # 4. Fill missing categories / text.
    for col in text_cols:
        missing = int(out[col].isna().sum())

        if not missing or categorical == "Leave missing":
            continue

        if categorical == "Unknown":
            fill = "Unknown"
        else:
            modes = out[col].mode(dropna=True)
            if modes.empty:
                continue
            fill = modes.iloc[0]

        out[col] = out[col].fillna(fill)
        note(col, f"Filled missing values with {categorical.lower()}", missing)

    return out.reset_index(drop=True), pd.DataFrame(log, columns=LOG_COLUMNS)
