"""
Section 08 – String & DateTime Operations
Run: pytest 08_strings_datetime/test_strings_datetime.py -v
"""
import pandas as pd
import numpy as np
import pytest


@pytest.fixture
def text_df():
    return pd.DataFrame({
        "email": ["alice@example.com", "BOB@TEST.ORG", "  charlie@dev.io  "],
        "full_name": ["Alice Smith", "Bob Jones", "Charlie Brown"],
        "code": ["A-001", "B-002", "C-003"],
    })


@pytest.fixture
def ts_df():
    dates = pd.date_range("2024-01-01", periods=6, freq="ME")
    return pd.DataFrame({
        "date": dates,
        "sales": [100, 150, 200, 130, 180, 220],
    })


# ── String tests ──────────────────────────────────────────────────────────────

def test_str_lower(text_df):
    # TODO: lowercase the "email" column
    result = None  # text_df["email"].str.lower()
    assert result.iloc[1] == "bob@test.org"


def test_str_strip(text_df):
    # TODO: strip whitespace from "email" column
    result = None  # text_df["email"].str.strip()
    assert result.iloc[2] == "charlie@dev.io"


def test_str_contains(text_df):
    # TODO: boolean mask where "email" contains "example"
    result = None  # text_df["email"].str.contains("example")
    assert result.tolist() == [True, False, False]


def test_str_split(text_df):
    # TODO: split "full_name" on " " and get first token (first name)
    result = None  # text_df["full_name"].str.split(" ").str[0]
    assert result.tolist() == ["Alice", "Bob", "Charlie"]


def test_str_extract(text_df):
    # TODO: extract the letter part before "-" in "code" with regex "([A-Z])-\d+"
    result = None  # text_df["code"].str.extract(r"([A-Z])-\d+")
    assert result.iloc[:, 0].tolist() == ["A", "B", "C"]


def test_str_replace(text_df):
    # TODO: replace "-" with "_" in "code" column
    result = None  # text_df["code"].str.replace("-", "_", regex=False)
    assert result.tolist() == ["A_001", "B_002", "C_003"]


# ── DateTime tests ────────────────────────────────────────────────────────────

def test_to_datetime():
    # TODO: parse ["2024-01-15", "2024-06-30"] to datetime with pd.to_datetime
    strings = ["2024-01-15", "2024-06-30"]
    result = None  # pd.to_datetime(strings)
    assert result[0].month == 1
    assert result[1].day == 30


def test_dt_accessor(ts_df):
    # TODO: extract month from ts_df["date"] using .dt.month
    result = None  # ts_df["date"].dt.month
    assert result.iloc[0] == 1
    assert result.iloc[5] == 6


def test_resample(ts_df):
    # TODO: set "date" as index, resample to quarterly ("QE"), sum "sales"
    df = ts_df.set_index("date")
    result = None  # df.resample("QE")["sales"].sum()
    assert len(result) == 2  # Q1 and Q2


def test_rolling(ts_df):
    # TODO: compute 3-period rolling mean on "sales"
    result = None  # ts_df["sales"].rolling(3).mean()
    assert pd.isna(result.iloc[0])  # first 2 are NaN
    assert round(result.iloc[2], 2) == 150.0  # (100+150+200)/3


def test_date_range():
    # TODO: create a DatetimeIndex from "2024-01-01" for 5 days with freq="D"
    result = None  # pd.date_range("2024-01-01", periods=5, freq="D")
    assert len(result) == 5
    assert result[0] == pd.Timestamp("2024-01-01")
