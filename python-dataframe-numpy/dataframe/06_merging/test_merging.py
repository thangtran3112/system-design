"""
Section 06 – Merging, Joining & Concatenating
Run: pytest 06_merging/test_merging.py -v
"""
import pandas as pd
import numpy as np
import pytest


@pytest.fixture
def employees():
    return pd.DataFrame({
        "emp_id": [1, 2, 3, 4],
        "name": ["Alice", "Bob", "Charlie", "Diana"],
        "dept_id": [10, 10, 20, 30],
    })


@pytest.fixture
def departments():
    return pd.DataFrame({
        "dept_id": [10, 20, 40],
        "dept_name": ["Engineering", "HR", "Finance"],
    })


def test_inner_merge(employees, departments):
    # TODO: inner merge employees and departments on "dept_id"
    result = None  # pd.merge(employees, departments, on="dept_id", how="inner")
    assert len(result) == 3  # Diana (dept 30) excluded
    assert "dept_name" in result.columns


def test_left_merge(employees, departments):
    # TODO: left merge employees onto departments on "dept_id"
    result = None  # pd.merge(employees, departments, on="dept_id", how="left")
    assert len(result) == 4  # all employees kept
    assert result.loc[result["name"] == "Diana", "dept_name"].isna().all()


def test_outer_merge(employees, departments):
    # TODO: outer merge — keep all rows from both
    result = None  # pd.merge(employees, departments, on="dept_id", how="outer")
    assert len(result) == 5  # 4 employees + Finance (no employees)


def test_merge_different_keys(employees, departments):
    # TODO: merge where left key is "dept_id" and right key is "dept_id" (same name here,
    #        but practice using left_on/right_on syntax)
    result = None  # pd.merge(employees, departments, left_on="dept_id", right_on="dept_id")
    assert len(result) == 3


def test_concat_rows():
    # TODO: concat two DataFrames vertically (axis=0), reset index
    df1 = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    df2 = pd.DataFrame({"a": [5, 6], "b": [7, 8]})
    result = None  # pd.concat([df1, df2], ignore_index=True)
    assert len(result) == 4
    assert result.iloc[2]["a"] == 5


def test_concat_columns():
    # TODO: concat two DataFrames horizontally (axis=1)
    df1 = pd.DataFrame({"a": [1, 2]})
    df2 = pd.DataFrame({"b": [3, 4]})
    result = None  # pd.concat([df1, df2], axis=1)
    assert list(result.columns) == ["a", "b"]


def test_join_on_index(employees, departments):
    # TODO: set dept_id as index on both, then use .join()
    emp = employees.set_index("dept_id")
    dept = departments.set_index("dept_id")
    result = None  # emp.join(dept, how="inner")
    assert "dept_name" in result.columns
    assert len(result) == 3
