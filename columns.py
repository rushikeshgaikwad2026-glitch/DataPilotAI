"""Single source of truth for understanding what each column means."""

import re
import warnings

import numpy as np
import pandas as pd

ID_TOKENS = {
    "id", "uuid", "guid", "sku", "phone", "mobile",
    "pincode", "postcode", "postal", "zip", "index",
}
ID_PHRASES = (
    "account number", "customer number", "order number",
    "row number", "invoice number", "reference number",
)
FINANCIAL_TOKENS = {
    "sales", "revenue", "profit", "amount", "price", "cost", "income",
    "salary", "balance", "payment", "expense", "turnover", "fee",
    "spend", "budget", "value",
}
DATE_TOKENS = {"date", "time", "timestamp", "month", "year", "period", "day"}
CALENDAR_TOKENS = {"year", "month", "day", "quarter", "week"}


def _tokens(name):
    """Split a column name into lowercase words (handles snake_case and CamelCase)."""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(name))
    text = text.lower().replace("_", " ")
    return text, set(re.split(r"[^a-z0-9]+", text)) - {""}


def _has(tokens, words):
    return any(w in tokens or w + "s" in tokens for w in words)


def is_identifier(name):
    """Return whether a column name explicitly describes an identifier."""
    text, tokens = _tokens(name)
    return _has(tokens, ID_TOKENS) or any(phrase in text for phrase in ID_PHRASES)


def is_text(series):
    return (
        pd.api.types.is_object_dtype(series)
        or pd.api.types.is_string_dtype(series)
        or isinstance(series.dtype, pd.CategoricalDtype)
    )


def to_datetime(series):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            return pd.to_datetime(series, errors="coerce", format="mixed")
        except (TypeError, ValueError):
            return pd.to_datetime(series, errors="coerce")


def to_num(df, column):
    return pd.to_numeric(df[column], errors="coerce")


def profile_columns(df):
    """Group columns by analytical role."""
    out = {k: [] for k in (
        "numeric", "financial", "categorical", "dates", "identifiers", "text"
    )}
    n_rows = len(df)

    for col in df.columns:
        s = df[col]
        nonnull = s.dropna()

        if nonnull.empty:
            continue

        _, tokens = _tokens(col)
        nunique = nonnull.nunique()

        if is_identifier(col):
            out["identifiers"].append(col)
            continue

        if pd.api.types.is_datetime64_any_dtype(s):
            out["dates"].append(col)
            continue

        if pd.api.types.is_bool_dtype(s):
            out["categorical"].append(col)
            continue

        if pd.api.types.is_numeric_dtype(s):
            converted = nonnull
        else:
            converted = pd.to_numeric(nonnull, errors="coerce")

        if converted.notna().mean() >= 0.8:
            converted = converted.dropna()

            if converted.nunique() <= 1:
                continue

            if nunique <= 2 or (_has(tokens, CALENDAR_TOKENS) and nunique <= 40):
                out["categorical"].append(col)
                continue

            if (
                n_rows > 20
                and nunique / len(nonnull) > 0.98
                and converted.is_monotonic_increasing
                and (converted % 1 == 0).all()
                and not _has(tokens, FINANCIAL_TOKENS)
                and converted.diff().dropna().eq(1).all()
            ):
                out["identifiers"].append(col)
                continue

            out["numeric"].append(col)
            if _has(tokens, FINANCIAL_TOKENS):
                out["financial"].append(col)
            continue

        # Non-numeric columns: dates, categories or free text.
        hint = _has(tokens, DATE_TOKENS)
        parsed_share = to_datetime(nonnull.head(300).astype(str)).notna().mean()

        if parsed_share >= (0.5 if hint else 0.85):
            out["dates"].append(col)
        elif nunique <= 40 and (len(nonnull) <= 30 or nunique / len(nonnull) <= 0.5):
            out["categorical"].append(col)
        else:
            out["text"].append(col)

    return out


def primary_metric(cols):
    return (cols["financial"] or cols["numeric"] or [None])[0]


def time_series(df, date_col, metric):
    """Aggregate a metric over time (monthly for long spans, daily otherwise)."""
    t = pd.DataFrame({
        "d": to_datetime(df[date_col]),
        "v": to_num(df, metric).replace([np.inf, -np.inf], np.nan),
    }).dropna()

    if len(t) < 3:
        return pd.DataFrame(columns=["Period", "Value"])

    freq = "M" if (t["d"].max() - t["d"].min()).days > 120 else "D"
    t["Period"] = t["d"].dt.to_period(freq).dt.to_timestamp()

    return (
        t.groupby("Period", as_index=False)["v"].sum()
        .rename(columns={"v": "Value"})
    )
