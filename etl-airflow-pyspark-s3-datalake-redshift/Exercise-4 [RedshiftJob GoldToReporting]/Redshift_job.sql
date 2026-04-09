/*
The redshift SQL job will create 5 snapshot tables by reading 2 tables from analytics (GOLD) layer which was generated in the last step by EMR job.
Create an external schema pointing to the glue catalog first.

Kindly replace your IAM Role ARN in the sql command below

Some hardcoded values are used like schema name, databasename, tablename. You can parameterize or customise it as per your requirement.
*/


CREATE EXTERNAL SCHEMA db_etl_sql_ext
FROM DATA CATALOG 
DATABASE 'db_etl_sql' 
IAM_ROLE '<IAM_ROLE_ARN>'
CREATE EXTERNAL DATABASE IF NOT EXISTS;


select * from db_etl_sql_ext.customers;

create schema sch_reporting;

CREATE TABLE sch_reporting.customer_segment_value (
    customer_segment character varying(12) ENCODE zstd distkey,
    customer_count bigint ENCODE zstd,
    avg_spent double precision ENCODE zstd,
    avg_transactions bigint ENCODE zstd,
    spst_date date default CURRENT_DATE
)
DISTSTYLE KEY;

CREATE TABLE sch_reporting.customer_activity_analysis (
    total_customers bigint ENCODE zstd,
    active_90_days bigint ENCODE zstd,
    inactive_90_days bigint ENCODE zstd,
    avg_customer_lifespan bigint ENCODE zstd,
    spst_date date default CURRENT_DATE
)
DISTSTYLE EVEN;

CREATE TABLE sch_reporting.category_performance_analysis  (
    category character varying(100) ENCODE zstd distkey,
    category_revenue double precision ENCODE zstd,
    category_units bigint ENCODE zstd,
    total_customers bigint ENCODE zstd,
    category_avg_price double precision ENCODE zstd,
    revenue_per_customer double precision ENCODE zstd,
    spst_date date default CURRENT_DATE
)
DISTSTYLE KEY;



CREATE TABLE sch_reporting.top_performing_subcategories  (
    category character varying(100) ENCODE zstd distkey,
    subcategory character varying(100) ENCODE zstd,
    total_revenue double precision ENCODE zstd,
    total_units_sold bigint ENCODE zstd,
    category_revenue_share double precision ENCODE zstd,
    spst_date date default CURRENT_DATE
)
DISTSTYLE KEY;




CREATE TABLE sch_reporting.customer_purchase_frequency  (
    frequency_segment character varying(29) ENCODE zstd distkey,
    customer_count bigint ENCODE zstd,
    avg_total_spent double precision ENCODE zstd,
    avg_transaction_value double precision ENCODE zstd,
    spst_date date default CURRENT_DATE
)
DISTSTYLE KEY;



INSERT INTO sch_reporting.customer_segment_value
--customer_segment_value
WITH customer_segments AS (
    SELECT 
        CASE 
            WHEN total_spent >= 1000 THEN 'High Value'
            WHEN total_spent >= 500 THEN 'Medium Value'
            ELSE 'Low Value'
        END as customer_segment,
        COUNT(*) as customer_count,
        AVG(total_spent) as avg_spent,
        AVG(total_transactions) as avg_transactions
    FROM db_etl_sql_ext.customer_metrics
    GROUP BY 
        CASE 
            WHEN total_spent >= 1000 THEN 'High Value'
            WHEN total_spent >= 500 THEN 'Medium Value'
            ELSE 'Low Value'
        END
)
SELECT * FROM customer_segments
ORDER BY avg_spent DESC;


/* this timestamp conversion is required as timestamp is by default stored in number format in Hudi tables */

INSERT INTO sch_reporting.customer_activity_analysis
--customer_activity_analysis
SELECT 
    COUNT(*) as total_customers,
    COUNT(CASE WHEN DATEDIFF('day',TIMESTAMP 'epoch' + last_purchase / 1000000 * INTERVAL '1 second' , CURRENT_DATE) <= 90 THEN 1 END) as active_90_days,
    COUNT(CASE WHEN DATEDIFF('day', TIMESTAMP 'epoch' + last_purchase / 1000000 * INTERVAL '1 second', CURRENT_DATE) > 90 THEN 1 END) as inactive_90_days,
    AVG(DATEDIFF('day', TIMESTAMP 'epoch' + first_purchase / 1000000 * INTERVAL '1 second', TIMESTAMP 'epoch' + last_purchase / 1000000 * INTERVAL '1 second')) as avg_customer_lifespan
FROM db_etl_sql_ext.customer_metrics;


INSERT INTO  sch_reporting.category_performance_analysis
--category_performance_analysis
SELECT 
    category,
    SUM(total_revenue) as category_revenue,
    SUM(total_units_sold) as category_units,
    SUM(unique_customers) as total_customers,
    AVG(avg_price) as category_avg_price,
    SUM(total_revenue)/SUM(unique_customers) as revenue_per_customer
FROM db_etl_sql_ext.product_analytics
GROUP BY category
ORDER BY category_revenue DESC;


INSERT INTO sch_reporting.top_performing_subcategories
--top_performing_subcategories
SELECT 
    category,
    subcategory,
    total_revenue,
    total_units_sold,
    ROUND((total_revenue * 100.0 / SUM(total_revenue) OVER (PARTITION BY category)), 2) as category_revenue_share
FROM db_etl_sql_ext.product_analytics
ORDER BY total_revenue DESC;


INSERT INTO  sch_reporting.customer_purchase_frequency
--customer_purchase_frequency
SELECT 
    CASE 
        WHEN total_transactions >= 10 THEN 'Frequent (10+ transactions)'
        WHEN total_transactions >= 5 THEN 'Regular (5-9 transactions)'
        ELSE 'Occasional (1-4 transactions)'
    END as frequency_segment,
    COUNT(*) as customer_count,
    AVG(total_spent) as avg_total_spent,
    AVG(avg_transaction_amount) as avg_transaction_value
FROM db_etl_sql_ext.customer_metrics
GROUP BY 
    CASE 
        WHEN total_transactions >= 10 THEN 'Frequent (10+ transactions)'
        WHEN total_transactions >= 5 THEN 'Regular (5-9 transactions)'
        ELSE 'Occasional (1-4 transactions)'
    END;