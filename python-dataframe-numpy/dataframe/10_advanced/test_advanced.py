"""
Section 10 – Advanced: MultiIndex, window functions, performance, IO
Run: pytest 10_advanced/test_advanced.py -v
"""
import pandas as pd
import numpy as np
import pytest


# ── MultiIndex ────────────────────────────────────────────────────────────────

def test_multiindex_creation():
    # TODO: create a MultiIndex DataFrame with levels ["Eng","HR"] x ["Q1","Q2"]
    arrays = [["Eng", "Eng", "HR", "HR"], ["Q1", "Q2", "Q1", "Q2"]]
    idx = None  # pd.MultiIndex.from_arrays(arrays, names=["dept", "quarter"])
    df = pd.DataFrame({"revenue": [100, 200, 150, 180]}, index=idx)
    assert df.loc["Eng"].shape == (2, 1)


def test_multiindex_loc():
    arrays = [["Eng", "Eng", "HR", "HR"], ["Q1", "Q2", "Q1", "Q2"]]
    idx = pd.MultiIndex.from_arrays(arrays, names=["dept", "quarter"])
    df = pd.DataFrame({"revenue": [100, 200, 150, 180]}, index=idx)
    # TODO: select Eng, Q2 using .loc[("Eng", "Q2")]
    result = None  # df.loc[("Eng", "Q2"), "revenue"]
    assert result == 200


def test_multiindex_xs():
    arrays = [["Eng", "Eng", "HR", "HR"], ["Q1", "Q2", "Q1", "Q2"]]
    idx = pd.MultiIndex.from_arrays(arrays, names=["dept", "quarter"])
    df = pd.DataFrame({"revenue": [100, 200, 150, 180]}, index=idx)
    # TODO: cross-section all Q1 rows using .xs("Q1", level="quarter")
    result = None  # df.xs("Q1", level="quarter")
    assert len(result) == 2
    assert result.loc["Eng", "revenue"] == 100


# ── Window functions ──────────────────────────────────────────────────────────

def test_expanding():
    s = pd.Series([1, 2, 3, 4, 5])
    # TODO: compute expanding cumulative mean
    result = None  # s.expanding().mean()
    assert result.iloc[0] == 1.0
    assert result.iloc[4] == 3.0


def test_ewm():
    s = pd.Series([1.0, 2.0, 3.0, 4.0])
    # TODO: compute exponentially-weighted mean with span=2
    result = None  # s.ewm(span=2).mean()
    assert result.iloc[0] == 1.0
    assert result.iloc[-1] > 3.0  # weighted toward recent values


# ── Performance ───────────────────────────────────────────────────────────────

def test_memory_usage():
    df = pd.DataFrame({"a": range(1000), "b": range(1000)})
    # TODO: call .memory_usage(deep=True) and assert total > 0
    mem = None  # df.memory_usage(deep=True)
    assert mem.sum() > 0


def test_copy_vs_view():
    df = pd.DataFrame({"x": [1, 2, 3]})
    # TODO: create an explicit copy of df
    df_copy = None  # df.copy()
    df_copy["x"] = 99
    assert df["x"].iloc[0] == 1  # original unchanged


def test_chunked_read(tmp_path):
    csv_file = tmp_path / "big.csv"
    pd.DataFrame({"a": range(100), "b": range(100)}).to_csv(csv_file, index=False)
    # TODO: read csv in chunks of 30 rows, collect into list, concat
    chunks = None  # list(pd.read_csv(csv_file, chunksize=30))
    result = pd.concat(chunks)
    assert len(result) == 100


# ── IO ────────────────────────────────────────────────────────────────────────

def test_to_from_csv(tmp_path):
    df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
    path = tmp_path / "out.csv"
    # TODO: write df to csv (no index), then read it back
    df.to_csv(None, index=False)   # fill in path
    result = pd.read_csv(None)     # fill in path
    assert result.shape == (3, 2)


def test_to_from_json(tmp_path):
    df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
    path = tmp_path / "out.json"
    # TODO: write to json orient="records", read back with pd.read_json
    df.to_json(None, orient="records")  # fill in path
    result = pd.read_json(None)         # fill in path
    assert set(result.columns) == {"x", "y"}
