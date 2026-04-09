from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.functions import count, sum, avg, min, max, col, countDistinct
import sys

""" 
Description:
The EMR job will read data from "data-lake" layer (SILVER) which is generated in the previous step by Glue job & generate "analytics" layer (GOLD).

Step1: Read 3 Hudi tables from "data-lake" path: customers, products & transactions & generate dataframe for each
Step2: Apply transformation to calculate customer_metrics
Step3: Apply transformation to calculate product analytics
Step4: Add new column process_date & write the 2 aggregate metrics into 2 new hudi tables in "analytics" path

Input Parameters:
        a) S3 bucket name
        b) S3 output path for Hudi tables

Script usage: 

spark-submit --deploy-mode cluster 
        --jars /usr/lib/hudi/hudi-spark-bundle.jar --conf "spark.serializer=org.apache.spark.serializer.KryoSerializer" 
        --conf "spark.sql.catalog.spark_catalog=org.apache.spark.sql.hudi.catalog.HoodieCatalog" 
        --conf "spark.sql.extensions=org.apache.spark.sql.hudi.HoodieSparkSessionExtension" 
        EMR_job.py <s3_bucket_name> <s3_op_path_for_hudi_table> 

There are some hardcoded values used (like data-lake, analytics path) & you can parameterise & customise it as per your requirement.
"""

class DataLakeProcessor:
    def __init__(self):
        self.spark = SparkSession.builder \
            .appName("DataLakeProcessor") \
            .config('spark.serializer', 'org.apache.spark.serializer.KryoSerializer') \
            .config('spark.sql.hive.convertMetastoreParquet', 'false') \
            .config('hive.metastore.client.factory.class', 'com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory') \
            .enableHiveSupport() \
            .getOrCreate()
        self.bucket_name = sys.argv[1]
        self.op_folder = sys.argv[2]
    
    def read_hudi_table(self, table_name: str) -> DataFrame:
        """Read data from Hudi table"""
        return self.spark.read.format('org.apache.hudi') \
            .load(f's3://{self.bucket_name}/{self.op_folder}/data-lake/{table_name}/*')
    
    def calculate_customer_metrics(self) -> DataFrame:
        """Calculate customer purchase metrics"""
        transactions = self.read_hudi_table("transactions")
        
        return transactions.groupBy("customer_id").agg(
                count("transaction_id").alias("total_transactions"),
                sum(col("unit_price") * col("quantity")).alias("total_spent"),
                avg(col("unit_price") * col("quantity")).alias("avg_transaction_amount"),
                min("transaction_date").alias("first_purchase"),
                max("transaction_date").alias("last_purchase")
            )
    
    def create_product_analytics(self) -> DataFrame:
        """Create product analytics"""
        transactions = self.read_hudi_table("transactions")
        products = self.read_hudi_table("products")
        
        return transactions.join(products, "product_id") \
            .groupBy("category", "subcategory") \
            .agg(
                sum("quantity").alias("total_units_sold"),
                sum(col("unit_price") * col("quantity")).alias("total_revenue"),
                avg("unit_price").alias("avg_price"),
                countDistinct("customer_id").alias("unique_customers")
            )
    
    def write_analytics_to_hudi(self, df: DataFrame, table_name: str, key_fields: List[str]):
        """Write analytics results to Hudi"""
        hudi_options = {
            'hoodie.table.name': table_name,
            "hoodie.datasource.write.table.type": "COPY_ON_WRITE",
            'hoodie.datasource.write.recordkey.field': ','.join(key_fields),
            'hoodie.datasource.write.precombine.field': 'process_date',
            "hoodie.datasource.write.partitionpath.field": "process_date",
            "hoodie.parquet.compression.codec": "gzip",
            "hoodie.datasource.write.hive_style_partitioning": "true",
            'hoodie.datasource.write.operation': 'upsert',
            'hoodie.datasource.hive_sync.enable': 'true',
            'hoodie.datasource.hive_sync.database': 'db_etl_sql',
            'hoodie.datasource.hive_sync.table': table_name,
            'hoodie.datasource.hive_sync.partition_fields': 'process_date',
            "hoodie.datasource.hive_sync.partition_extractor_class": "org.apache.hudi.hive.MultiPartKeysValueExtractor",
            "hoodie.datasource.hive_sync.use_jdbc": "false",
            "hoodie.datasource.hive_sync.mode": "hms"
        }

        df.withColumn("process_date", current_date()) \
            .write.format('org.apache.hudi') \
            .options(**hudi_options) \
            .mode('append') \
            .save(f's3://{self.bucket_name}/{self.op_folder}/analytics/{table_name}')

    def run(self):
        # Calculate metrics
        customer_metrics_df = self.calculate_customer_metrics()
        product_analytics_df = self.create_product_analytics()
        
        # Write results
        self.write_analytics_to_hudi(
            customer_metrics_df,
            "customer_metrics",
            ["customer_id"]
        )
        self.write_analytics_to_hudi(
            product_analytics_df,
            "product_analytics",
            ["category", "subcategory"]
        )

if __name__ == "__main__":
    processor = DataLakeProcessor()
    processor.run()