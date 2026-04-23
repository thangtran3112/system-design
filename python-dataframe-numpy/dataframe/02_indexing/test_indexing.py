"""
Section 02 – Indexing & Selection
Run: pytest 02_indexing/test_indexing.py -v
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


def test_select_column(df):
    # TODO: select the "age" column as a Series
    result = None  # replace with your code
    assert isinstance(result, pd.Series)
    assert result.tolist() == [25, 30, 35, 28]


def test_select_multiple_columns(df):
    # TODO: select columns ["name", "salary"] as a DataFrame
    result = None  # replace with your code
    assert list(result.columns) == ["name", "salary"]


def test_loc_by_label(df):
    # TODO: use .loc to get row at index 2 (Charlie's row) as a Series
    result = None  # replace with your code
    assert result["name"] == "Charlie"


def test_loc_slice(df):
    # TODO: use .loc[1:3] to get rows 1 through 3
    result = None  # replace with your code
    assert len(result) == 3


def test_iloc_by_position(df):
    # TODO: use .iloc[0, 1] to get the age of the first row
    result = None  # replace with your code
    assert result == 25


def test_iloc_slice(df):
    # TODO: use .iloc[:2, :2] to get first 2 rows and first 2 columns
    result = None  # replace with your code
    assert result.shape == (2, 2)


def test_boolean_indexing(df):
    # TODO: filter rows where age > 28
    result = None  # replace with your code
    assert len(result) == 2
    assert all(result["age"] > 28)


def test_query(df):
    # TODO: use .query("dept == 'Eng' and salary > 80000")
    result = None  # replace with your code
    assert len(result) == 2


def test_at_iat(df):
    # TODO: use .at[0, "name"] to get scalar value "Alice"
    result = None  # replace with your code
    assert result == "Alice"


def test_set_index_reset(df):
    # TODO: set "name" as index, then reset it back
    indexed = None  # df.set_index("name")
    reset = None    # indexed.reset_index()
    assert indexed.index.name == "name"
    assert "name" in reset.columns
