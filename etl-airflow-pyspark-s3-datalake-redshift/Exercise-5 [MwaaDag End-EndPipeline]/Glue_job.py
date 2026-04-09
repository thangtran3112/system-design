'''
Description: 
Step1: The Glue job will read 3 input data files & create a dataframe for each file- 
		customers
    	products
    	transactions
Step2: Basic string transformations are applied & new load_date column is added
Step3: Write the dataframe into a Hudi table & register in Glue Catalog

This process is equivalent to reading data from input(bronze) layer 
& generate data-lake (silver) data layer

Parameters used in the Glue Job:
--conf spark.serializer=org.apache.spark.serializer.KryoSerializer 
--conf spark.sql.hive.convertMetastoreParquet=false
--datalake-formats hudi
--bucket_name <enter_your_bucket_name>
--ip_path <enter_input_raw_files_path>
--op_path <enter_output_silver_files_path>

Some hardcoded values are used in the code like databasename, tablename.
Feel free to change it as per your requirement.

'''

import sys
from pyspark.sql.functions import *
from pyspark.sql.functions import current_date
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from awsglue.transforms import *
from pyspark.context import SparkContext

class ETLSQL:
    def __init__(self):
        params = ["bucket_name","ip_path","op_path"]
        args = getResolvedOptions(sys.argv, params)
        
        self.context = GlueContext(SparkContext.getOrCreate())
        self.spark = self.context.spark_session
        self.job = Job(self.context)
        self.bucket_name = args["bucket_name"]
        self.ip_path = args["ip_path"]
        self.op_path = args["op_path"]
    
    def read_raw_data(self, path: str, format: str = "csv") -> DataFrame:
        """Read raw data from S3"""
        return self.spark.read.format(format) \
            .option("header", "true") \
            .option("inferSchema", "true") \
            .load(path)
    
    def process_customers(self, df: DataFrame) -> DataFrame:
        """Process customer data"""
        return df.withColumn("email", lower(col("email"))) \
            .withColumn("country", upper(col("country"))) \
            .withColumn("load_date", current_date())
    
    def process_products(self, df: DataFrame) -> DataFrame:
        """Process product data"""
        return df.withColumn("category", initcap(col("category"))) \
            .withColumn("subcategory", initcap(col("subcategory"))) \
            .withColumn("load_date", current_date())
    
    def process_transactions(self, df: DataFrame) -> DataFrame:
        """Process transactions data"""
        return df.withColumn("load_date", current_date())
    
    def write_to_hudi(self, df: DataFrame, table_name: str, key_field: str):
        """Write DataFrame to Hudi table"""
        hudi_options = {
            'hoodie.table.name': table_name,
            "hoodie.datasource.write.table.type": "COPY_ON_WRITE",
            'hoodie.datasource.write.recordkey.field': key_field,
            'hoodie.datasource.write.precombine.field': 'load_date',
            'hoodie.datasource.write.operation': 'upsert',
            "hoodie.datasource.write.partitionpath.field": "load_date",
            "hoodie.parquet.compression.codec": "gzip",
            "hoodie.datasource.write.hive_style_partitioning": "true",
            'hoodie.datasource.hive_sync.enable': 'true',
            'hoodie.datasource.hive_sync.database': 'db_etl_sql',
            'hoodie.datasource.hive_sync.table': table_name,
            'hoodie.datasource.hive_sync.partition_fields': 'load_date',
            "hoodie.datasource.hive_sync.partition_extractor_class": "org.apache.hudi.hive.MultiPartKeysValueExtractor",
            "hoodie.datasource.hive_sync.use_jdbc": "false",
            "hoodie.datasource.hive_sync.mode": "hms"
        }
        
        df.write.format('hudi') \
            .options(**hudi_options) \
            .mode('append') \
            .save( f's3://{self.bucket_name}/{self.op_path}/data-lake/{table_name}')

    def run(self):
        # Read raw data
        customers_df = self.read_raw_data(f"s3://{self.bucket_name}/{self.ip_path}/customers/")
        products_df = self.read_raw_data(f"s3://{self.bucket_name}/{self.ip_path}/products/")
        transactions_df = self.read_raw_data(f"s3://{self.bucket_name}/{self.ip_path}/transactions/")

        # Process data
        processed_customers = self.process_customers(customers_df)
        processed_products = self.process_products(products_df)
        processed_transactions = self.process_transactions(transactions_df)
        
        # Write to Hudi tables
        self.write_to_hudi(processed_customers, "customers", "customer_id")
        self.write_to_hudi(processed_products, "products", "product_id")
        self.write_to_hudi(processed_transactions, "transactions", "transaction_id")

        self.job.commit()

if __name__ == "__main__":
    etl = ETLSQL()
    etl.run()