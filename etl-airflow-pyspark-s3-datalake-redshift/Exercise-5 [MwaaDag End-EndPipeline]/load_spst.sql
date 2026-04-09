/* 
Stored Procedure created that encapsulates the DML statements for 5 snapshot tables.
The SP will be called in MWAA Dag directly.
*/

CREATE OR REPLACE PROCEDURE sch_reporting.load_snapshot_data()
LANGUAGE plpgsql
AS $$
BEGIN

DELETE from sch_reporting.customer_segment_value where spst_date=current_date;
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




DELETE from sch_reporting.customer_activity_analysis where spst_date=current_date;
INSERT INTO sch_reporting.customer_activity_analysis
--customer_activity_analysis
SELECT 
    COUNT(*) as total_customers,
    COUNT(CASE WHEN DATEDIFF('day',TIMESTAMP 'epoch' + last_purchase / 1000000 * INTERVAL '1 second' , CURRENT_DATE) <= 90 THEN 1 END) as active_90_days,
    COUNT(CASE WHEN DATEDIFF('day', TIMESTAMP 'epoch' + last_purchase / 1000000 * INTERVAL '1 second', CURRENT_DATE) > 90 THEN 1 END) as inactive_90_days,
    AVG(DATEDIFF('day', TIMESTAMP 'epoch' + first_purchase / 1000000 * INTERVAL '1 second', TIMESTAMP 'epoch' + last_purchase / 1000000 * INTERVAL '1 second')) as avg_customer_lifespan
FROM db_etl_sql_ext.customer_metrics;



DELETE from sch_reporting.category_performance_analysis where spst_date=current_date;
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



DELETE from sch_reporting.top_performing_subcategories where spst_date=current_date;
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



DELETE from sch_reporting.customer_purchase_frequency where spst_date=current_date;
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

END;
$$;