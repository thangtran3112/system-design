"""
Section 07 – Reshaping: pivot, melt, stack, unstack
Run: pytest 07_reshaping/test_reshaping.py -v
"""
import pandas as pd
import numpy as np
import pytest


@pytest.fixture
def wide_df():
    return pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie"],
        "math": [90, 80, 70],
        "science": [85, 75, 95],
        "history": [70, 88, 60],
    })


@pytest.fixture
def long_df():
    return pd.DataFrame({
        "name": ["Alice", "Alice", "Bob", "Bob"],
        "subject": ["math", "science", "math", "science"],
        "score": [90, 85, 80, 75],
    })


def test_melt(wide_df):
    # TODO: melt wide_df, id_vars=["name"], var_name="subject", value_name="score"
    result = None  # pd.melt(wide_df, id_vars=["name"], var_name="subject", value_name="score")
    assert len(result) == 9  # 3 names * 3 subjects
    assert set(result.columns) == {"name", "subject", "score"}


def test_pivot(long_df):
    # TODO: pivot long_df: index="name", columns="subject", values="score"
    result = None  # long_df.pivot(index="name", columns="subject", values="score")
    assert result.loc["Alice", "math"] == 90
    assert result.shape == (2, 2)


def test_pivot_table(wide_df):
    # TODO: create a pivot_table from wide_df with values=["math","science"],
    #        index="name", aggfunc="mean"
    result = None  # pd.pivot_table(wide_df, values=["math","science"], index="name", aggfunc="mean")
    assert "math" in result.columns
    assert result.loc["Alice", "math"] == 90.0


def test_stack_unstack():
    df = pd.DataFrame(
        {"math": [90, 80], "science": [85, 75]},
        index=["Alice", "Bob"]
    )
    # TODO: stack df so columns become an inner index level
    stacked = None  # df.stack()
    assert isinstance(stacked, pd.Series)
    assert stacked["Alice", "math"] == 90

    # TODO: unstack stacked back to original shape
    unstacked = None  # stacked.unstack()
    assert unstacked.shape == (2, 2)


def test_crosstab():
    df = pd.DataFrame({
        "dept": ["Eng", "Eng", "HR", "HR", "Eng"],
        "gender": ["M", "F", "M", "F", "M"],
    })
    # TODO: pd.crosstab(df["dept"], df["gender"])
    result = None  # replace with your code
    assert result.loc["Eng", "M"] == 2
    assert result.loc["HR", "F"] == 1
