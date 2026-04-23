"""
Section 03 – Handling Missing Data
Run: pytest 03_missing_data/test_missing.py -v
"""
import pandas as pd
import numpy as np
import pytest


@pytest.fixture
def df():
    return pd.DataFrame({
        "a": [1.0, np.nan, 3.0, np.nan, 5.0],
        "b": [np.nan, 2.0, np.nan, 4.0, 5.0],
        "c": ["x", None, "z", None, "w"],
    })


def test_detect_nulls(df):
    # TODO: use .isnull() to get boolean DataFrame of missing values
    result = None  # replace with your code
    assert result.shape == df.shape
    assert result["a"].sum() == 2


def test_count_nulls(df):
    # TODO: use .isnull().sum() to count nulls per column
    result = None  # replace with your code
    assert result["a"] == 2
    assert result["b"] == 2


def test_dropna_any(df):
    # TODO: drop rows that have ANY null value
    result = None  # replace with your code
    assert len(result) == 1  # only row index 4 has no nulls


def test_dropna_all(df):
    # TODO: drop rows only when ALL values are null
    result = None  # replace with your code
    assert len(result) == 5  # no fully-null rows


def test_dropna_subset(df):
    # TODO: drop rows where column "a" is null
    result = None  # replace with your code
    assert len(result) == 3


def test_fillna_scalar(df):
    # TODO: fill all NaN in column "a" with 0
    result = None  # df["a"].fillna(0)
    assert result.isnull().sum() == 0
    assert result[1] == 0.0


def test_fillna_forward(df):
    # TODO: forward-fill column "a" (ffill)
    result = None  # df["a"].ffill()
    assert result[1] == 1.0  # filled from previous value


def test_fillna_mean(df):
    # TODO: fill NaN in "b" with the mean of "b"
    mean_b = df["b"].mean()
    result = None  # df["b"].fillna(mean_b)
    assert result.isnull().sum() == 0


def test_interpolate(df):
    # TODO: use .interpolate() on column "a"
    result = None  # df["a"].interpolate()
    assert result.isnull().sum() == 0
    assert result[1] == 2.0  # midpoint between 1 and 3
