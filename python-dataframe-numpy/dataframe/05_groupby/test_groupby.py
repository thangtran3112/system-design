"""
Section 05 – GroupBy & Aggregation
Run: pytest 05_groupby/test_groupby.py -v
"""
import pandas as pd
import numpy as np
import pytest


@pytest.fixture
def df():
    return pd.DataFrame({
        "dept": ["Eng", "Eng", "HR", "HR", "Eng"],
        "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
        "salary": [70000, 90000, 85000, 95000, 60000],
        "age": [25, 30, 35, 28, 22],
    })


def test_groupby_mean(df):
    # TODO: groupby "dept" and get mean salary
    result = None  # df.groupby("dept")["salary"].mean()
    assert round(result["Eng"]) == 73333
    assert result["HR"] == 90000.0


def test_groupby_agg(df):
    # TODO: groupby "dept", agg salary with min and max
    result = None  # df.groupby("dept")["salary"].agg(["min", "max"])
    assert result.loc["Eng", "min"] == 60000
    assert result.loc["Eng", "max"] == 90000


def test_groupby_multiple_agg(df):
    # TODO: groupby "dept", agg salary=["mean","sum"] and age=["mean"]
    result = None  # df.groupby("dept").agg({"salary": ["mean","sum"], "age": ["mean"]})
    assert ("salary", "sum") in result.columns


def test_groupby_size(df):
    # TODO: get the count of employees per dept
    result = None  # df.groupby("dept").size()
    assert result["Eng"] == 3
    assert result["HR"] == 2


def test_groupby_filter(df):
    # TODO: keep only depts with more than 2 employees using groupby.filter
    result = None  # df.groupby("dept").filter(lambda g: len(g) > 2)
    assert len(result) == 3
    assert all(result["dept"] == "Eng")


def test_groupby_transform(df):
    # TODO: add a "dept_avg_salary" column using groupby transform
    df["dept_avg"] = None  # df.groupby("dept")["salary"].transform("mean")
    assert df.loc[df["dept"] == "HR", "dept_avg"].iloc[0] == 90000.0


def test_groupby_apply(df):
    # TODO: use apply to get the top earner per dept (idxmax on salary)
    result = None  # df.groupby("dept").apply(lambda g: g.loc[g["salary"].idxmax()])
    assert result.loc["HR", "name"] == "Diana"


def test_named_aggregation(df):
    # TODO: use named agg: groupby dept, avg_sal=("salary","mean"), headcount=("name","count")
    result = None  # df.groupby("dept").agg(avg_sal=("salary","mean"), headcount=("name","count"))
    assert "avg_sal" in result.columns
    assert result.loc["Eng", "headcount"] == 3
