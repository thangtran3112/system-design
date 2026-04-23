import pandas as pd
import numpy as np
import pytest


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
        "age": [25, 30, 35, 28, 22],
        "salary": [70000, 90000, 85000, 95000, 60000],
        "department": ["Eng", "Eng", "HR", "Eng", "HR"],
        "active": [True, True, False, True, True],
    })


@pytest.fixture
def sales_df():
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=12, freq="ME")
    return pd.DataFrame({
        "date": dates,
        "region": ["North", "South"] * 6,
        "sales": np.random.randint(1000, 9000, 12),
        "units": np.random.randint(10, 100, 12),
    })
