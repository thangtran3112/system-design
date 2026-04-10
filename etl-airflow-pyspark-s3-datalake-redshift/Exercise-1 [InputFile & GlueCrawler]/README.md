# Exercise 1 — Bronze Layer: Input Files & Glue Crawler

## Overview

This folder represents the **Bronze layer** — raw, unprocessed data as it lands from source systems. Data is uploaded to S3 as CSV files and cataloged by a Glue Crawler before being processed into the Silver layer.

---

## Files

| File | Type | Description |
|------|------|-------------|
| `raw_customers.csv` | Static | 50 customers — dimension data, loaded once |
| `raw_products.csv` | Static | 50 products — dimension data, loaded once |
| `raw_transactions.csv` | Historical | Transactions from 2024-01-15 to 2024-01-24 (IDs 1001–1050) |
| `raw_transactions_2024-01-25.csv` | Daily | Sample next-day file — transactions for 2024-01-25 (IDs 1051–1055) |

---

## CSV-Per-Day Pattern

Instead of appending new rows to a single file, each day's transactions land as a **separate dated file**. This is the standard pattern used in production pipelines.

### Why CSV-Per-Day?

- **Idempotency** — re-uploading a day's file doesn't corrupt history
- **Debuggability** — easy to identify which day had bad data
- **Parallelism** — multiple days can be processed concurrently
- **Auditability** — raw source files are preserved as-is, never modified

### Naming Convention

```
raw_transactions_YYYY-MM-DD.csv
```

### S3 Folder Structure

```
s3://my-data-bucket/
└── bronze/
    ├── customers/
    │   └── raw_customers.csv
    ├── products/
    │   └── raw_products.csv
    └── transactions/
        ├── raw_transactions.csv              ← historical (Jan 15–24)
        ├── raw_transactions_2024-01-25.csv   ← day 1 new file
        ├── raw_transactions_2024-01-26.csv   ← day 2 new file
        └── ...
```

> **Note:** Customers and products are dimension tables — they don't need daily files unless there are updates (new customers, price changes, etc.).

---

## Step 1 — Upload Daily File to S3

Each day, upload the new transactions file to the S3 bronze prefix:

```bash
aws s3 cp raw_transactions_2024-01-25.csv \
  s3://my-data-bucket/bronze/transactions/raw_transactions_2024-01-25.csv
```

---

## Step 2 — Glue Crawler

The Glue Crawler scans the S3 prefix and registers/updates the table in the **AWS Glue Data Catalog**.

**What the Crawler does:**
- Detects all CSV files under `bronze/transactions/`
- Infers schema (column names and types)
- Creates or updates the table `db_etl_sql.raw_transactions` in the Glue Catalog
- New files are automatically included — no manual schema updates needed

**After crawling, Glue Catalog sees:**
```
Table: db_etl_sql.raw_transactions
Location: s3://my-data-bucket/bronze/transactions/
Columns:
  transaction_id    bigint
  customer_id       bigint
  product_id        bigint
  transaction_date  string
  quantity          bigint
  unit_price        double
  payment_method    string
```

---

## Step 3 — How Data Flows into the Silver Layer

Once cataloged, the **Glue Job (Exercise 2)** reads from the Bronze catalog table and writes cleaned data into Hudi tables on S3 (Silver layer).

```
Bronze (S3 CSV files)
        │
        │  Glue Crawler registers schema
        ▼
Glue Data Catalog
  db_etl_sql.raw_transactions
        │
        │  Glue Job reads, cleans, deduplicates
        ▼
Silver (S3 Hudi tables)
s3://my-data-bucket/output/hudi/data-lake/transactions/
    transaction_date=2024-01-24/
        part-00000-abc.parquet.gz
    transaction_date=2024-01-25/    ← new partition after next-day file processed
        part-00000-xyz.parquet.gz
```

**What the Glue Job does during Bronze → Silver:**
- Casts `transaction_date` from string to timestamp
- Deduplicates on `transaction_id` (safe to reprocess the same file)
- Partitions data by `transaction_date`
- Writes as a Hudi table (supports upserts, time travel)

---

## Full Daily Pipeline Flow

```
1. New CSV uploaded to S3 bronze prefix
        ↓
2. Glue Crawler runs → updates Glue Catalog
        ↓
3. Glue Job (Exercise 2) → Bronze to Silver
   Reads all CSVs, writes new Hudi partition:
   transaction_date=YYYY-MM-DD/
        ↓
4. EMR Job (Exercise 3) → Silver to Gold
   Reads all Silver partitions, recalculates aggregates,
   writes new Gold partition: process_date=YYYY-MM-DD/
        ↓
5. Redshift (Exercise 4) → Gold to Reporting
   Queries Gold Hudi tables via Redshift Spectrum
```

In Exercise 5, this entire flow is orchestrated automatically by an **Apache Airflow DAG on MWAA** — triggered daily, so dropping a new CSV to S3 kicks off the whole pipeline end-to-end.

---

## Sample Data Schema

### raw_transactions

| Column | Type | Example |
|--------|------|---------|
| transaction_id | int | 1051 |
| customer_id | int | 15 |
| product_id | int | 103 |
| transaction_date | datetime | 2024-01-25 09:30:00 |
| quantity | int | 1 |
| unit_price | float | 799.99 |
| payment_method | string | credit_card |

### raw_customers (static)

| Column | Type | Example |
|--------|------|---------|
| customer_id | int | 15 |
| first_name | string | Thomas |
| last_name | string | Schmidt |
| email | string | tschmidt@email.net |
| country | string | Germany |
| city | string | Munich |
| registration_date | date | 2024-01-09 |

### raw_products (static)

| Column | Type | Example |
|--------|------|---------|
| product_id | int | 103 |
| product_name | string | Smart 4K TV 55" |
| category | string | Electronics |
| subcategory | string | TVs |
| price | float | 799.99 |
| supplier_id | int | 503 |
