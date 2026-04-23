"""
Section 09 – apply, map, and vectorized operations
Run: pytest 09_apply/test_apply.py -v
"""
import pandas as pd
import numpy as np
import pytest


@pytest.fixture
def df():
    return pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie"],
        "salary": [70000, 90000, 85000],
        "years": [2, 5, 3],
    })


def test_apply_row(df):
    # TODO: use .apply(axis=1) to compute salary/years (salary per year of experience)
    result = None  # df.apply(lambda row: row["salary"] / row["years"], axis=1)
    assert result.iloc[0] == 35000.0
    assert result.iloc[1] == 18000.0


def test_apply_column(df):
    # TODO: use .apply(axis=0) to get the max of each numeric column
    result = None  # df[["salary", "years"]].apply(max)
    assert result["salary"] == 90000
    assert result["years"] == 5


def test_map_series(df):
    # TODO: use .map() on "name" with dict {"Alice":"A","Bob":"B","Charlie":"C"}
    mapping = {"Alice": "A", "Bob": "B", "Charlie": "C"}
    result = None  # df["name"].map(mapping)
    assert result.tolist() == ["A", "B", "C"]


def test_map_function(df):
    # TODO: use .map(lambda x: x * 1.1) on "salary" to apply 10% raise
    result = None  # df["salary"].map(lambda x: x * 1.1)
    assert result.iloc[0] == 77000.0


def test_vectorized_vs_apply(df):
    # Vectorized (preferred for performance)
    # TODO: compute salary * 0.2 as a bonus without apply (direct arithmetic)
    bonus_vectorized = None  # df["salary"] * 0.2
    # Apply version (equivalent but slower)
    bonus_apply = df["salary"].apply(lambda x: x * 0.2)
    pd.testing.assert_series_equal(bonus_vectorized, bonus_apply)


def test_assign_with_lambda(df):
    # TODO: use .assign() with a lambda to add "level" col:
    #        "Senior" if years >= 4 else "Junior"
    result = None  # df.assign(level=lambda x: np.where(x["years"] >= 4, "Senior", "Junior"))
    assert result.loc[result["name"] == "Bob", "level"].iloc[0] == "Senior"
    assert result.loc[result["name"] == "Alice", "level"].iloc[0] == "Junior"


def test_pipe(df):
    def add_bonus(frame, rate=0.1):
        return frame.assign(bonus=frame["salary"] * rate)

    def add_tax(frame, rate=0.2):
        return frame.assign(tax=frame["salary"] * rate)

    # TODO: use .pipe() to chain add_bonus then add_tax
    result = None  # df.pipe(add_bonus).pipe(add_tax)
    assert "bonus" in result.columns
    assert "tax" in result.columns
    assert result["bonus"].iloc[0] == 7000.0
