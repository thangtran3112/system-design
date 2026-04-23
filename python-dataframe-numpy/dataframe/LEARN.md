# Pandas DataFrame: Beginner to Advanced

## Setup (using uv — no global installs)

```bash
# 1. Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. From inside the dataframe/ folder, create a local venv and install deps
cd python-dataframe-numpy/dataframe
uv venv                          # creates .venv/
source .venv/bin/activate        # activate (Mac/Linux)
# .venv\Scripts\activate         # activate (Windows)

uv pip install -r requirements.txt
```

## How to use this guide

1. Activate the venv: `source .venv/bin/activate`
2. Open a test file (e.g. `01_creating/test_creating.py`)
3. Find the `# TODO` line in each test function
4. Copy the snippet from the matching section below, replacing `None`
5. Run `pytest 01_creating/test_creating.py -v` — green = you got it right
6. Move to the next section

---

## What is a DataFrame?

A **DataFrame** is a 2-dimensional table — like a spreadsheet or a SQL table — made of rows and columns.
Each column is a **Series** (a 1-D labeled array), and all columns share the same row index.

```
   name   age  salary  dept
0  Alice   25   70000   Eng   ← row 0
1  Bob     30   90000   Eng   ← row 1
2  Charlie 35   85000   HR    ← row 2
↑           ↑    ↑       ↑
index     columns (each is a Series)
```

The left-most numbers (0, 1, 2) are the **index** — pandas' built-in row labels.
You can replace the default integer index with any meaningful label (city name, date, ID, etc.).

---

## Section 01 – Creating DataFrames

### From a dict

The most common way. Dictionary **keys** become column names; dictionary **values** become the column data.
All lists must be the same length — one element per row.

```python
df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
```

Result:

```
   x  y
0  1  4
1  2  5
2  3  6
```

### From a list of dicts

When your data is already a list of records (common from JSON APIs), pass it directly.
Each dict becomes **one row**. Missing keys in a dict produce `NaN` in that cell.

```python
df = pd.DataFrame([{"a": 1, "b": 2}, {"a": 3, "b": 4}])
```

Result:

```
   a  b
0  1  2
1  3  4
```

### From a NumPy array

NumPy arrays store raw numbers in a grid. `np.arange(6)` produces `[0,1,2,3,4,5]`.
`.reshape(3, 2)` rearranges those 6 numbers into 3 rows × 2 columns.
The `columns` parameter labels each column — without it pandas just uses 0, 1.

```python
arr = np.arange(6).reshape(3, 2)
df = pd.DataFrame(arr, columns=["c1", "c2"])
```

Result:

```
   c1  c2
0   0   1
1   2   3
2   4   5
```

> **Why NumPy?** NumPy is the math engine underneath pandas. Operations on numeric
> DataFrames are actually NumPy operations under the hood, which is why they are fast.

### From CSV

CSV (Comma-Separated Values) is the most common flat-file format for data.
`pd.read_csv` reads the file, uses the first row as column names, and infers dtypes automatically.

```python
df = pd.read_csv(csv_file)            # basic — comma separator assumed
df = pd.read_csv(csv_file, sep=";")   # semicolon separator (common in Europe)
df = pd.read_csv(csv_file, nrows=100) # only load the first 100 rows (useful for large files)
```

> **Tip:** Always check `df.shape` and `df.head()` right after loading to make sure the file
> parsed correctly (right number of columns, no header row treated as data, etc.).

### Column dtypes

Every column has a **dtype** (data type). Pandas infers it automatically:

| Python type | Pandas dtype |
| ----------- | ------------ |
| integers | `int64` |
| floats | `float64` |
| strings/mixed | `object` |
| booleans | `bool` |
| datetimes | `datetime64[ns]` |

```python
df = pd.DataFrame({"vals": [1.0, 2.0, 3.0]})
print(df.dtypes)           # vals    float64
```

Knowing dtypes matters because:
- Arithmetic only works on numeric dtypes
- Memory usage depends on dtype (int32 uses half the memory of int64)
- Sorting and grouping behave differently on strings vs numbers

### Setting an index

The index is the row label — by default it is 0, 1, 2 … but you can promote any column.
Once a column is the index, you look up rows by that value instead of by position.

```python
df = pd.DataFrame({"city": ["NY", "LA"], "pop": [8, 4]})
df = df.set_index("city")
df.loc["NY", "pop"]        # 8 — look up row "NY", column "pop"
```

Result after `set_index`:

```
       pop
city
NY       8
LA       4
```

> **Note:** `set_index` returns a new DataFrame — it does not modify `df` in place
> unless you pass `inplace=True`. This pattern (returning a new object) is common in pandas.

### Quick info helpers

These are the first things to run whenever you get a new dataset:

```python
df.shape          # (rows, cols) — a tuple, e.g. (150, 5)
df.dtypes         # column name → dtype mapping
df.head(3)        # first 3 rows — confirms data loaded correctly
df.tail(3)        # last 3 rows — checks for trailing garbage rows
df.info()         # dtypes + non-null counts + memory usage in one shot
df.describe()     # count/mean/std/min/max/quartiles for every numeric column
```

`df.info()` is especially useful for spotting columns that have unexpected nulls
(non-null count less than total rows) before you start analysis.

---

## Section 02 – Indexing & Selection

### Select a single column (returns Series)

Square-bracket notation with a single string gives you one column as a **Series**.
A Series is like a single-column DataFrame but without the table structure — just a labeled 1-D array.

```python
s = df["age"]
# s is a pd.Series, same index as df
```

> **Series vs DataFrame:** `df["age"]` → Series. `df[["age"]]` (double brackets) → DataFrame with one column.
> The distinction matters because some methods only work on one or the other.

### Select multiple columns (returns DataFrame)

Pass a **list** of column names. The result is a DataFrame (not a Series), even if you pick one column.

```python
sub = df[["name", "salary"]]
```

The order of names in the list controls the column order in the result.

### `.loc` — label-based selection

`.loc` always works with **labels** (index values and column names), never with positions.

```python
df.loc[2]                    # entire row whose index label is 2
df.loc[1:3]                  # rows with labels 1, 2, 3 — NOTE: end is inclusive (unlike Python slices)
df.loc[0, "name"]            # single scalar: row label 0, column "name"
df.loc[:, "age":"salary"]    # all rows, columns from "age" through "salary"
```

> **Key rule:** `.loc` slices are **inclusive on both ends**. `df.loc[1:3]` returns rows 1, 2, AND 3.
> This is different from Python list slices where the end is exclusive.

### `.iloc` — position-based selection

`.iloc` works with **integer positions**, exactly like Python list slicing (0-based, end exclusive).

```python
df.iloc[0]          # first row (position 0)
df.iloc[0, 1]       # row at position 0, column at position 1
df.iloc[:2, :2]     # first 2 rows AND first 2 columns (end exclusive: positions 0 and 1)
```

> **When to use which:**
> - Use `.loc` when you know the label (e.g., `df.loc["Alice"]` or `df.loc[0, "name"]`)
> - Use `.iloc` when you want "the 3rd row" regardless of what the index says

### Boolean indexing

Pass a boolean Series (True/False per row) inside `[]` to keep only the `True` rows.
The boolean Series is produced by a comparison on a column.

```python
df[df["age"] > 28]
# Step 1: df["age"] > 28  → pd.Series([False, True, True, False, ...])
# Step 2: df[that_series] → keeps only the True rows
```

Combine conditions with `&` (and) or `|` (or). **Always use parentheses** around each condition
because `&` has higher precedence than `>`:

```python
df[(df["dept"] == "Eng") & (df["salary"] > 80000)]
```

### `.query` — readable filtering

`.query` lets you write filter conditions as a plain string — easier to read for complex filters.

```python
df.query("dept == 'Eng' and salary > 80000")
df.query("age > @threshold")   # @ prefix references a local Python variable
```

Internally it is the same as boolean indexing — just a cleaner syntax.

### Scalar access (fastest)

When you need a single value (not a row or column), `.at` and `.iat` are the fastest path:

```python
df.at[0, "name"]    # label-based: row label 0, column "name" → "Alice"
df.iat[0, 0]        # position-based: row 0, column 0 → "Alice"
```

They skip the overhead of constructing a Series or DataFrame and return the raw Python value.

### Set and reset index

```python
df2 = df.set_index("name")   # "name" column → becomes the index; column disappears
df3 = df2.reset_index()      # index → becomes a regular column again; index resets to 0,1,2…
```

> **Why set an index?** Lookups via `.loc` are O(1) hash lookups on the index.
> If you frequently filter by "name", making it the index speeds that up.

---

## Section 03 – Handling Missing Data

Real-world data always has gaps. Pandas represents missing values as `NaN`
(Not a Number — a special IEEE floating-point value). For object/string columns it can also be `None`.

### Detect nulls

```python
df.isnull()              # returns a boolean DataFrame — True where value is missing
df.isnull().sum()        # count of missing values per column (True counts as 1)
df.notnull()             # inverse of isnull — True where value IS present
```

> **Tip:** `df.isnull().sum()` is the fastest way to get a missing-value audit of an entire dataset.
> Any column showing a count > 0 needs a handling strategy before analysis.

### Drop rows with nulls

```python
df.dropna()                      # drop any row that has AT LEAST ONE null
df.dropna(how="all")             # drop rows only if EVERY value in the row is null
df.dropna(subset=["a"])          # drop rows where column "a" specifically is null
df.dropna(thresh=2)              # keep rows that have AT LEAST 2 non-null values
```

> **Warning:** `df.dropna()` can silently delete a lot of data. Always check
> `df.isnull().sum()` first so you know how many rows you will lose.

### Fill nulls

Instead of dropping, you can **impute** (fill in) missing values:

```python
df["a"].fillna(0)                    # replace NaN with a fixed scalar (0, "", "Unknown", etc.)
df["a"].ffill()                      # forward-fill: copy the last valid value downward
df["a"].bfill()                      # backward-fill: copy the next valid value upward
df["b"].fillna(df["b"].mean())       # fill with the column mean — common for numeric data
```

**Forward-fill example** — useful for time series where a sensor missed a reading:

```
Before ffill:     After ffill:
a                 a
1.0               1.0
NaN       →       1.0   ← copied from above
3.0               3.0
NaN       →       3.0   ← copied from above
5.0               5.0
```

### Interpolate

Linear interpolation fills gaps by drawing a straight line between the surrounding valid values.
It is more accurate than forward-fill when data changes gradually (temperature, prices, sensor readings).

```python
df["a"].interpolate()                              # linear (default)
df["a"].interpolate(method="polynomial", order=2)  # curve-fitting for non-linear trends
```

**Interpolation example:**

```
Before:     After interpolate():
1.0         1.0
NaN    →    2.0   ← midpoint between 1 and 3
3.0         3.0
```

---

## Section 04 – Column Operations, Sorting, and Data Types

### Add a column

Assign directly to a new column name. This **mutates** the original DataFrame.
The right side must be a scalar, a list of the same length, or a Series with a matching index.

```python
df["bonus"] = df["salary"] * 0.1
# Every row's bonus = its salary × 10%
```

### `.assign` — non-mutating column addition

`.assign` returns a **new** DataFrame with the added column, leaving the original untouched.
This is the preferred style when chaining operations, because it does not have side effects.

```python
result = df.assign(tax=lambda x: x["salary"] * 0.2)
# x is the DataFrame being piped — same as df here
```

> **Why lambda?** The `lambda x:` form is needed so the new column can reference
> other columns being assigned in the same `.assign` call. It also defers evaluation.

### Drop columns/rows

```python
df.drop(columns=["dept"])     # remove the "dept" column — returns new DataFrame
df.drop(index=[0, 2])         # remove rows at index labels 0 and 2
```

> **Important:** Like most pandas operations, `.drop` returns a new object.
> To actually remove from the original you need `df = df.drop(...)` or pass `inplace=True`.

### Rename columns

Pass a dict mapping old name → new name. Only listed columns are renamed; others are unchanged.

```python
df.rename(columns={"salary": "compensation"})
```

### Sort

```python
df.sort_values("salary", ascending=False)                        # highest salary first
df.sort_values(["dept", "salary"], ascending=[True, False])      # sort dept A→Z, then salary high→low within dept
df.sort_index()                                                   # restore original index order
```

Multi-column sort: the second column only breaks ties within groups defined by the first column.

### Cast types

Sometimes pandas infers the wrong dtype, or you want to shrink memory usage.
`.astype()` returns a new Series with the converted values.

```python
df["age"].astype(float)           # int64 → float64 (adds decimal point)
df["age"].astype("int32")         # int64 → int32 (half the memory, max value ~2 billion)
df["dept"].astype("category")     # string → Categorical (huge memory saving for repeated strings)
```

> **When to use int32/int16:** If a column holds values that fit in a smaller type
> (e.g., age is always < 150), downcasting saves memory. On a 1 million-row dataset,
> int32 vs int64 saves 4 MB per column.

### Categorical dtype

A Categorical column stores a lookup table of unique values + integer codes for each row.
This is far more memory-efficient than storing the full string "Engineering" millions of times.

```python
df["dept"] = pd.Categorical(df["dept"])
df["dept"].cat.categories        # shows the unique labels: Index(['Eng', 'HR'], dtype='object')
df["dept"].cat.codes             # shows the integer code per row: 0=Eng, 1=HR, etc.
```

> **Rule of thumb:** Convert any string column where the number of unique values is much smaller
> than the number of rows (e.g., department, country, status).

### String operations on a column

The `.str` accessor exposes string methods that work element-wise across the whole Series:

```python
df["name"].str.upper()   # "alice" → "ALICE"
df["name"].str.lower()   # "ALICE" → "alice"
df["name"].str.len()     # "Alice" → 5 (character count per value)
```

> These are vectorized — far faster than `df["name"].apply(lambda x: x.upper())`.

### Clip values

Clipping replaces values outside a range with the boundary value.
Useful for capping outliers without dropping the row.

```python
df["age"].clip(lower=26, upper=32)
# age=22 → 26 (clipped up to lower bound)
# age=35 → 32 (clipped down to upper bound)
# age=30 → 30 (unchanged, already within bounds)
```

### Value counts

Returns how many times each unique value appears — sorted by frequency descending by default.

```python
df["dept"].value_counts()
# Eng    3
# HR     1

df["dept"].value_counts(normalize=True)   # proportions instead of counts
# Eng    0.75
# HR     0.25
```

---

## Section 05 – GroupBy & Aggregation

GroupBy follows the **split → apply → combine** pattern:

1. **Split** — divide the DataFrame into groups by the values in one or more columns
2. **Apply** — run a function on each group independently
3. **Combine** — assemble the per-group results into a single output

```
Original df:          Split by "dept":       Apply mean salary:
dept  salary          Eng: [70000,90000,60000]  → 73333
Eng   70000           HR:  [85000,95000]         → 90000
Eng   90000
HR    85000           Combine → Series indexed by dept
HR    95000
Eng   60000
```

### Basic groupby + aggregation

```python
df.groupby("dept")["salary"].mean()
# Returns a Series: dept → mean salary

df.groupby("dept")["salary"].agg(["min", "max", "mean"])
# Returns a DataFrame: dept → (min, max, mean) columns
```

### Multiple column aggregation

Apply different functions to different columns in one call:

```python
df.groupby("dept").agg({"salary": ["mean", "sum"], "age": ["mean"]})
# Result has MultiIndex columns: (salary, mean), (salary, sum), (age, mean)
```

### Named aggregation (pandas >= 0.25, preferred)

The clearest syntax — you explicitly name the output columns:

```python
df.groupby("dept").agg(
    avg_sal=("salary", "mean"),     # new column "avg_sal" = mean of "salary"
    headcount=("name", "count"),    # new column "headcount" = count of "name"
)
```

This produces a flat DataFrame with columns `avg_sal` and `headcount` — no MultiIndex.

### Group size

```python
df.groupby("dept").size()
# Counts ALL rows per group (including nulls) — returns a Series
```

> `.size()` vs `.count()`: `.size()` counts every row; `.count()` counts only non-null values per column.

### Filter groups

`.filter` removes entire groups that fail a condition. Unlike boolean indexing (which filters rows),
this keeps or discards whole groups.

```python
# Keep only departments that have more than 2 employees
df.groupby("dept").filter(lambda g: len(g) > 2)
# If "HR" has 2 employees, every HR row is removed from the result
```

### Transform — broadcast result back to original shape

`.transform` runs an aggregation but instead of collapsing the group into one row,
it **broadcasts** the result back so every row in a group gets the group's value.
The output has the same number of rows and the same index as the original DataFrame.

```python
df["dept_avg"] = df.groupby("dept")["salary"].transform("mean")
# Every Eng employee row now has "dept_avg" = 73333
# Every HR  employee row now has "dept_avg" = 90000
```

This is perfect for computing "how much does this person earn vs. their department average?"
(`df["salary"] - df["dept_avg"]`) without losing the row-level detail.

### Apply — custom function per group

`.apply` gives you the most flexibility — your function receives each group as a full DataFrame
and can return anything. It is slower than the built-in aggregations, so use it only when
the built-ins cannot do what you need.

```python
# Return the row of the top earner in each department
df.groupby("dept").apply(lambda g: g.loc[g["salary"].idxmax()])
# g is the sub-DataFrame for one department
# g["salary"].idxmax() is the row index of the maximum salary in that group
```

### Common agg functions

| Function | Description |
| -------- | ----------- |
| `sum` | sum |
| `mean` | arithmetic mean |
| `median` | median |
| `std` / `var` | standard deviation / variance |
| `min` / `max` | extremes |
| `count` | non-null count |
| `nunique` | distinct count |
| `first` / `last` | first/last in group |

---

## Section 06 – Merging, Joining & Concatenating

### pd.merge (SQL-style)

`pd.merge` is the pandas equivalent of a SQL JOIN. It aligns rows from two DataFrames
on a **key column** (or index).

```
employees:          departments:
emp_id  dept_id     dept_id  dept_name
1       10          10       Engineering
2       10          20       HR
3       20          40       Finance
4       30
```

**Inner join** — only rows where the key exists in BOTH tables:

```python
pd.merge(employees, departments, on="dept_id", how="inner")
# emp_ids 1,2,3 matched — emp 4 (dept 30) excluded, Finance (dept 40) excluded
```

**Left join** — all rows from the LEFT table, `NaN` where there is no right-side match:

```python
pd.merge(employees, departments, on="dept_id", how="left")
# All 4 employees kept; emp 4 gets NaN for dept_name
```

**Outer join** — all rows from BOTH tables, `NaN` where no match:

```python
pd.merge(employees, departments, on="dept_id", how="outer")
# All employees + Finance row (no employees); gaps filled with NaN
```

**Different key names:**

```python
pd.merge(left, right, left_on="lid", right_on="rid")
# When the key column has different names in each DataFrame
```

### pd.concat

`pd.concat` stacks DataFrames either vertically (more rows) or horizontally (more columns).
It does NOT require a key — it just concatenates by position.

```python
# Append rows from df2 below df1 (like SQL UNION ALL)
pd.concat([df1, df2], ignore_index=True)
# ignore_index=True gives a fresh 0,1,2… index instead of preserving originals

# Stick df2 columns to the right of df1 (must have same index)
pd.concat([df1, df2], axis=1)

# Add a label for each source — creates a MultiIndex on rows
pd.concat([df1, df2], keys=["first", "second"])
```

### DataFrame.join (index-based)

`.join` is a shorthand for merging on the index. Both DataFrames must be indexed on the key.

```python
emp.set_index("dept_id").join(dept.set_index("dept_id"), how="inner")
```

### Merge vs Concat vs Join

| Operation | When to use |
| --------- | ----------- |
| `merge` | SQL-like joins on columns or index |
| `concat` | Stack DataFrames (rows or columns) |
| `join` | Index-to-index merging shorthand |

---

## Section 07 – Reshaping

Reshaping transforms the *layout* of data without changing the values.
The two most common shapes are **wide** and **long**:

```
Wide format (one row per student):    Long format (one row per observation):
name   math  science                  name     subject  score
Alice   90     85                     Alice    math     90
Bob     80     75                     Alice    science  85
                                      Bob      math     80
                                      Bob      science  75
```

Long format is preferred for plotting libraries (seaborn, ggplot) and for GroupBy operations.
Wide format is preferred for reading by humans and for pivot tables.

### Melt (wide → long)

`pd.melt` unpivots a wide DataFrame into a long one.
`id_vars` are the columns that stay as-is (they identify the row).
All other columns become rows, with their column name stored in `var_name`
and their value stored in `value_name`.

```python
pd.melt(wide_df, id_vars=["name"], var_name="subject", value_name="score")
```

### Pivot (long → wide)

`pivot` is the inverse of melt — it rotates unique values in one column into new column headers.

```python
long_df.pivot(index="name", columns="subject", values="score")
# "name" → row labels
# "subject" unique values → column headers
# "score" → cell values
```

> **Requirement:** Each combination of `index` + `columns` must be unique.
> If there are duplicates, use `pivot_table` instead.

### Pivot table (with aggregation)

Like Excel pivot tables. When the index/column combinations are not unique,
`pivot_table` aggregates the values (default is `mean`).

```python
pd.pivot_table(df, values="score", index="name", columns="subject",
               aggfunc="mean", fill_value=0)
# fill_value=0 replaces NaN (combinations with no data) with 0
```

### Stack and Unstack

`stack` rotates the column labels into a new inner index level — the DataFrame becomes narrower and taller.
`unstack` does the reverse.

```python
stacked = df.stack()            # columns → inner index level → produces a Series
unstacked = stacked.unstack()   # inner index level → columns → back to DataFrame
```

This is useful when you have a MultiIndex and need to swap what is a "row" vs a "column."

### Crosstab

A frequency table counting how often combinations of two categorical variables co-occur.

```python
pd.crosstab(df["dept"], df["gender"])
# Rows = dept values, Columns = gender values, Cells = count of co-occurrences

pd.crosstab(df["dept"], df["gender"], normalize="index")
# normalize="index" → each row sums to 1.0 (shows proportions within dept)
```

---

## Section 08 – String & DateTime Operations

### String accessor `.str`

The `.str` accessor makes string methods available on a whole Series at once —
no loop or apply needed. Every method is vectorized (runs at C speed internally).

```python
s.str.lower()                       # "Hello" → "hello"
s.str.upper()                       # "hello" → "HELLO"
s.str.strip()                       # "  hello  " → "hello" (removes leading/trailing whitespace)
s.str.len()                         # "hello" → 5 (character count)
s.str.contains("pattern")           # True/False per element — supports regex by default
s.str.startswith("A")               # True if string begins with "A"
s.str.endswith(".com")              # True if string ends with ".com"
s.str.split(" ").str[0]             # split on space, then grab the first token
s.str.extract(r"([A-Z])-\d+")       # capture group from regex — e.g. "A-001" → "A"
s.str.replace("-", "_", regex=False) # literal replace (regex=False treats "-" as plain text)
s.str.slice(0, 3)                   # first 3 characters of each string
```

> **Regex reminder:** `r"([A-Z])-\d+"` means: one uppercase letter (captured), a dash, then one-or-more digits.
> The `r` prefix makes it a raw string so `\d` is not interpreted by Python before reaching the regex engine.

### DateTime parsing

Pandas stores dates as `datetime64[ns]` — a 64-bit integer counting nanoseconds since 1970-01-01.
`pd.to_datetime` converts strings or integers into this type.

```python
pd.to_datetime(["2024-01-15", "2024-06-30"])
# Recognizes ISO 8601 format automatically

pd.to_datetime(df["date_col"], format="%Y-%m-%d")
# Explicit format is faster and avoids ambiguity (e.g. 01/02/03 could be many dates)
```

### DateTime accessor `.dt`

Once a column is `datetime64`, the `.dt` accessor exposes date/time components:

```python
s.dt.year           # 2024
s.dt.month          # 1–12
s.dt.day            # 1–31
s.dt.dayofweek      # 0=Monday … 6=Sunday
s.dt.hour           # 0–23
s.dt.date           # Python date object (strips time component)
s.dt.strftime("%Y-%m")  # format as string: "2024-01"
```

### Date ranges

`pd.date_range` creates a sequence of evenly-spaced dates — useful for building time-series DataFrames
or reindexing an existing one.

```python
pd.date_range("2024-01-01", periods=12, freq="ME")   # 12 month-end dates
pd.date_range("2024-01-01", "2024-12-31", freq="W")  # every week between two dates
pd.date_range("2024-01-01", periods=5, freq="D")     # 5 consecutive days
```

Common `freq` aliases: `"D"` = day, `"W"` = week, `"ME"` = month-end,
`"QE"` = quarter-end, `"YE"` = year-end, `"h"` = hour, `"min"` = minute.

### Resample (time-series groupby)

`resample` is like `groupby` but specifically for time-series data.
It groups rows into time buckets and aggregates within each bucket.
The DataFrame must have a `datetime64` index first.

```python
df.set_index("date").resample("QE")["sales"].sum()    # total sales per quarter
df.set_index("date").resample("W")["sales"].mean()    # average weekly sales
```

### Rolling windows

A rolling window calculates a statistic over the last N observations — the window slides forward one row at a time.
The first N-1 rows produce `NaN` because there are not enough preceding rows to fill the window.

```python
df["sales"].rolling(3).mean()    # average of current row + 2 previous rows
df["sales"].rolling(7).sum()     # sum of last 7 rows
df["sales"].rolling(3).std()     # standard deviation of last 3 rows
```

**Sliding window visualization (window=3):**

```
row   value   rolling(3).mean()
0     100     NaN   ← only 1 value so far
1     150     NaN   ← only 2 values so far
2     200     150.0 ← (100+150+200)/3
3     130     160.0 ← (150+200+130)/3
4     180     170.0 ← (200+130+180)/3
```

### Expanding windows (cumulative)

An expanding window starts at row 0 and grows to include every row seen so far.
It is useful for cumulative statistics.

```python
df["sales"].expanding().mean()   # cumulative mean up to each row
df["sales"].expanding().max()    # running maximum
```

---

## Section 09 – apply, map, and Vectorized Operations

### `.apply` on rows (axis=1)

`axis=1` means "pass each row as a Series to the function."
Use this when the calculation needs values from multiple columns in the same row.

```python
df.apply(lambda row: row["salary"] / row["years"], axis=1)
# For each row: divide salary by years-of-experience
# "row" is a pd.Series with index = column names
```

> `.apply(axis=1)` iterates row-by-row in Python — it is 10–100× slower than vectorized ops.
> Only use it when you cannot express the logic with NumPy or column arithmetic.

### `.apply` on columns (axis=0)

`axis=0` (default) passes each **column** as a Series to the function.

```python
df[["salary", "years"]].apply(max)    # max value within each column
df[["salary", "years"]].apply(np.sum) # sum of each column
```

### `.map` on a Series

`.map` applies a function or dict lookup to every element in a Series:

```python
df["name"].map({"Alice": "A", "Bob": "B"})   # dict lookup — "Alice" → "A"
df["salary"].map(lambda x: x * 1.1)          # function — each salary × 1.1
```

> `.map` with a dict is very fast (hash table lookup). Values not in the dict become `NaN`.

### Vectorized operations (always prefer over apply)

Pandas inherits NumPy's vectorized arithmetic — operations on whole columns at once,
implemented in C, without any Python-level loop.

```python
df["bonus"] = df["salary"] * 0.1         # one C-level multiply over all rows
df["tax"]   = df["salary"] * 0.2

# Conditional assignment — np.where(condition, value_if_true, value_if_false)
np.where(df["years"] >= 4, "Senior", "Junior")
```

`np.where` checks the condition for every row at once. It is the vectorized equivalent of:

```python
# SLOW — do not do this:
[("Senior" if y >= 4 else "Junior") for y in df["years"]]
```

### `.assign` with lambda

You can chain multiple column additions in one `.assign` call.
Each lambda receives the DataFrame **as it exists at that point**, including columns added earlier in the call.

```python
df.assign(
    level=lambda x: np.where(x["years"] >= 4, "Senior", "Junior"),
    bonus=lambda x: x["salary"] * 0.1,
)
```

### `.pipe` — chaining functions cleanly

`.pipe(func)` calls `func(df)` and passes the result to the next operation.
It lets you chain transformation functions in a readable left-to-right sequence
without nesting function calls.

```python
def add_bonus(frame, rate=0.1):
    return frame.assign(bonus=frame["salary"] * rate)

def add_tax(frame, rate=0.2):
    return frame.assign(tax=frame["salary"] * rate)

result = df.pipe(add_bonus).pipe(add_tax)
# Equivalent to: add_tax(add_bonus(df))  — but much more readable
```

### Performance rule of thumb

| Approach | Speed | Use when |
| -------- | ----- | -------- |
| Vectorized (`df["a"] * 2`) | Fastest | Always for numeric ops |
| `np.where` / `np.select` | Fast | Conditional assignments |
| `.map` (dict) | Fast | Label mapping |
| `.apply` (axis=1) | Slow | Complex row logic only |

---

## Section 10 – Advanced Topics

### MultiIndex creation

A MultiIndex (hierarchical index) lets you have multiple levels of row or column labels.
Think of it as grouping rows without losing individual access to each row.

```python
arrays = [["Eng", "Eng", "HR", "HR"], ["Q1", "Q2", "Q1", "Q2"]]
idx = pd.MultiIndex.from_arrays(arrays, names=["dept", "quarter"])
df = pd.DataFrame({"revenue": [100, 200, 150, 180]}, index=idx)
```

Result:

```
              revenue
dept quarter
Eng  Q1           100
     Q2           200
HR   Q1           150
     Q2           180
```

This structure is natural for any data that has two dimensions of grouping (department × quarter,
country × city, user × session, etc.).

### Selecting from MultiIndex

```python
df.loc["Eng"]                        # all rows where outer level = "Eng" (returns a DataFrame)
df.loc[("Eng", "Q2"), "revenue"]     # single scalar — outer "Eng", inner "Q2"
df.xs("Q1", level="quarter")         # cross-section: all rows where quarter = "Q1"
                                     # regardless of what "dept" is
```

`.xs` (cross-section) is useful when you want to slice on an inner level without
specifying the outer level.

### Exponentially Weighted Mean (EWM)

A regular rolling mean weights all N observations equally.
An **EWM** gives higher weight to more recent observations — the weight decays exponentially as you go back.
This makes the result more responsive to recent changes.

```python
s.ewm(span=2).mean()       # span controls how fast weights decay: smaller span = more weight on recent values
s.ewm(halflife=3).mean()   # halflife: after 3 periods, a value's weight is halved
```

> EWM is widely used in finance (stock price smoothing), monitoring (response-time smoothing),
> and any domain where recent data is more relevant than old data.

### Memory efficiency

Pandas defaults to 64-bit types for everything. On large datasets this wastes memory.

```python
df.memory_usage(deep=True)       # bytes used per column — use this to find heavy columns
df["dept"].astype("category")    # strings with few unique values: can be 10–100× smaller
df["id"].astype("int32")         # IDs that fit in 32 bits: half the memory of int64
df.dtypes                        # review all dtypes before optimizing
```

**Typical savings on a 1 million-row dataset:**

| Column | Before | After | Saving |
| ------ | ------ | ----- | ------ |
| `dept` (string, 3 values) | ~60 MB | ~1 MB | 98% |
| `age` int64 → int16 | 8 MB | 2 MB | 75% |

### Explicit copy (avoid SettingWithCopyWarning)

Pandas sometimes returns a **view** (a window into the original DataFrame's memory)
instead of a **copy** (independent data). Modifying a view may or may not modify the original —
this ambiguity causes the dreaded `SettingWithCopyWarning`.

The fix: always call `.copy()` when you want an independent DataFrame.

```python
df_copy = df.copy()      # guaranteed independent copy — changes to df_copy never affect df
df_view = df[:]          # looks like a copy but may still share memory — avoid
```

### Chunked reading for large files

If a CSV file is larger than your RAM, you cannot load it all at once.
`chunksize` turns `pd.read_csv` into an **iterator** that yields one chunk at a time.

```python
chunks = pd.read_csv("large.csv", chunksize=10_000)
result = pd.concat(chunks)    # load all chunks then combine (still needs enough RAM for total)

# Memory-efficient: process and discard each chunk
for chunk in pd.read_csv("large.csv", chunksize=10_000):
    process(chunk)            # aggregate, filter, write output — never hold all chunks at once
```

### IO cheat sheet

Different file formats trade off human readability, speed, and dtype preservation:

```python
# CSV — universal, human-readable, no dtype preservation
df.to_csv("out.csv", index=False)    # index=False avoids writing the 0,1,2 row numbers
pd.read_csv("out.csv")

# JSON — good for nested/API data
df.to_json("out.json", orient="records")   # orient="records" → list of row dicts
pd.read_json("out.json")

# Parquet — fast binary format, preserves dtypes exactly, compressed automatically
# Best choice for saving/loading processed DataFrames in a pipeline
df.to_parquet("out.parquet")
pd.read_parquet("out.parquet")

# Excel — for sharing with non-technical stakeholders
df.to_excel("out.xlsx", index=False)
pd.read_excel("out.xlsx")
```

> **Format recommendation:** Use CSV for interoperability, Parquet for performance/storage in pipelines,
> Excel only when a human needs to open the file in Excel.

### Useful one-liners

```python
df.duplicated()                          # True for rows that are exact duplicates of an earlier row
df.drop_duplicates(subset=["email"])     # keep only the first occurrence of each email
df.sample(n=5, random_state=42)          # random sample of 5 rows (random_state makes it reproducible)
df.nlargest(3, "salary")                 # top 3 rows by salary — faster than sort + head
df.nsmallest(3, "age")                   # bottom 3 rows by age
df.between_time("09:00", "17:00")        # filter by time-of-day (requires DatetimeIndex)
pd.get_dummies(df["dept"])               # one-hot encode: "Eng" → Eng=1, HR=0
df.corr()                                # Pearson correlation matrix between all numeric columns
```

---

## Running all tests

```bash
# from inside the dataframe/ folder
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt

# run everything
pytest -v

# run one section
pytest 01_creating/ -v

# run with coverage
pytest --cov=. -v
```

---

## Learning path

| Section | Concepts | Difficulty |
| ------- | -------- | ---------- |
| 01 | Creating DataFrames | ⭐ |
| 02 | Indexing & Selection | ⭐⭐ |
| 03 | Missing Data | ⭐⭐ |
| 04 | Column ops, sort, dtypes | ⭐⭐ |
| 05 | GroupBy & Aggregation | ⭐⭐⭐ |
| 06 | Merge / Join / Concat | ⭐⭐⭐ |
| 07 | Reshaping | ⭐⭐⭐ |
| 08 | Strings & DateTime | ⭐⭐⭐ |
| 09 | apply, map, pipe | ⭐⭐⭐⭐ |
| 10 | MultiIndex, perf, IO | ⭐⭐⭐⭐⭐ |
