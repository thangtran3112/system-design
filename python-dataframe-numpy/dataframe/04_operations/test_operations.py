"""
Section 04 – Column Operations, Sorting, and Data Types
Run: pytest 04_operations/test_operations.py -v
"""
import pandas as pd
import numpy as np
import pytest


@pytest.fixture
def df():
    return pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie", "Diana"],
        "age": [25, 30, 35, 28],
        "salary": [70000, 90000, 85000, 95000],
        "dept": ["Eng", "Eng", "HR", "Eng"],
    })


def test_add_column(df):
    # TODO: add a "bonus" column = salary * 0.1
    df["bonus"] = None  # replace with your code
    assert "bonus" in df.columns
    assert df["bonus"].iloc[0] == 7000.0


def test_assign(df):
    # TODO: use .assign(tax=lambda x: x["salary"] * 0.2) to add "tax" column
    result = None  # replace with your code
    assert "tax" in result.columns
    assert result["tax"].iloc[1] == 18000.0


def test_drop_column(df):
    # TODO: drop the "dept" column
    result = None  # replace with your code
    assert "dept" not in result.columns


def test_rename_column(df):
    # TODO: rename "salary" to "compensation"
    result = None  # replace with your code
    assert "compensation" in result.columns
    assert "salary" not in result.columns


def test_sort_by_column(df):
    # TODO: sort by "salary" descending
    result = None  # replace with your code
    assert result.iloc[0]["name"] == "Diana"


def test_sort_by_multiple(df):
    # TODO: sort by "dept" ascending, then "salary" descending
    result = None  # replace with your code
    assert result.iloc[0]["dept"] == "Eng"


def test_astype(df):
    # TODO: cast "age" column to float
    df["age"] = None  # df["age"].astype(float)
    assert df["age"].dtype == np.float64


def test_categorical(df):
    # TODO: convert "dept" to Categorical dtype
    df["dept"] = None  # pd.Categorical(df["dept"])
    assert str(df["dept"].dtype) == "category"


def test_string_ops(df):
    # TODO: uppercase the "name" column using .str.upper()
    result = None  # df["name"].str.upper()
    assert result.iloc[0] == "ALICE"


def test_clip(df):
    # TODO: clip "age" between 26 and 32
    result = None  # df["age"].clip(26, 32)
    assert result.min() == 26
    assert result.max() == 32


def test_value_counts(df):
    # TODO: get value counts of "dept" column
    result = None  # df["dept"].value_counts()
    assert result["Eng"] == 3
    assert result["HR"] == 1
