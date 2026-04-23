"""
Section 01 – Creating DataFrames
Copy each snippet from LEARN.md into the TODO blocks and run:
  pytest 01_creating/test_creating.py -v
"""
import pandas as pd
import numpy as np
import pytest

#    x  y
# 0  1  4
# 1  2  5
# 2  3  6
def test_from_dict():
    # TODO: create a DataFrame from a dict with keys "x" and "y", values [1,2,3] and [4,5,6]
    df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
    assert list(df.columns) == ["x", "y"]
    assert df.shape == (3, 2) # 3 rows, 2 collumns

#    a  b
# 0  1  2
# 1  3  4
def test_from_list_of_dicts():
    # TODO: create a DataFrame from a list of dicts [{"a":1,"b":2}, {"a":3,"b":4}]
    df = pd.DataFrame([{"a": 1, "b": 2}, {"a": 3, "b": 4}])
    assert df.shape == (2, 2)
    assert df["a"].tolist() == [1, 3]


def test_from_numpy():
    # TODO: create a 3x2 DataFrame from a numpy arange(6).reshape(3,2), columns=["c1","c2"]
    arr = np.arange(6).reshape(3, 2)
    df = pd.DataFrame(arr, columns=["c1", "c2"])
    assert df.shape == (3, 2)
    assert list(df.columns) == ["c1", "c2"]


def test_from_csv(tmp_path):
    # TODO: write a CSV then read it back with pd.read_csv
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text("name,score\nAlice,90\nBob,85\n")
    df = None  # replace with your code: pd.read_csv(csv_file)
    assert df.shape == (2, 2)
    assert df["score"].sum() == 175


def test_column_dtypes():
    # TODO: create a df with col "vals" = [1.0, 2.0, 3.0] and verify dtype is float64
    df = None  # replace with your code
    assert df["vals"].dtype == np.float64


def test_index_setting():
    # TODO: create df from {"city":["NY","LA"],"pop":[8,4]}, set "city" as index
    df = None  # replace with your code
    assert df.index.name == "city"
    assert df.loc["NY", "pop"] == 8
