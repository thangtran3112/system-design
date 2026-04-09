from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator
from airflow.providers.amazon.aws.operators.emr import EmrAddStepsOperator
from airflow.providers.amazon.aws.sensors.emr import EmrStepSensor
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.operators.dummy_operator import DummyOperator
from datetime import datetime, timedelta
"""
This is airflow DAG which will run Glue job first to read raw data file & generate 3 hudi tables  in data-lake path.
Then it will trigger EMR job which will read 3 hudi tables loaded in previous step to generate 2 hudi tables in analytics path.
Then it will call Redshift Stored Procedure to generate snapshot tables for reporting purpose.

Kindly replace the string values which are enclosed in <> before executing the job.
Moreover create a redshift connection in the Airflow as well
"""
class EtlSqlPipeline:
    def __init__(self):
        self.default_args = {
            'owner': 'etl-sql',
            'depends_on_past': False,
            'start_date': datetime(2025, 1, 1),
            'retries': 1,
            'retry_delay': timedelta(minutes=5)
        }
        self.RS_CONN_ID = '<enter Redshift connection name>'
        self.EMR_cluster_id = '<enter EMR Cluster ID>'

        
        self.dag = DAG(
            dag_id='etl_sql_demo_pipeline',
            default_args=self.default_args,
            schedule_interval=None,
            description="Demo etl-sql pipeline that runs Glue, EMR & Redshift loads",
            catchup=False,
            tags=["etl-sql","demo"],
        )
        
        self.create_tasks()
    
    def create_tasks(self):
        # Start
        start_pipeline = DummyOperator(task_id="LetsGo")

        # Glue ETL Job
        Step1_GlueJob = GlueJobOperator(
            task_id='Step1_GlueJob',
            job_name='<enter glue job name>',
            script_args={
                "--bucket_name": "<enter s3 bucket name>",
                "--ip_path": "<enter input raw data files path>",
                "--op_path": "<enter output hudi table path>",
            },
            dag=self.dag
        )
        
        # EMR Analytics Job
        emr_steps = [{
            'Name': 'Generate_Gold_Layer',
            'ActionOnFailure': 'CONTINUE',
            'HadoopJarStep': {
                'Jar': 'command-runner.jar',
                'Args': [
                    "spark-submit",
                    "--deploy-mode", "cluster", 
                    "--jars", "/usr/lib/hudi/hudi-spark-bundle.jar",
                    "--conf", "spark.serializer=org.apache.spark.serializer.KryoSerializer",
                    "--conf", "spark.sql.catalog.spark_catalog=org.apache.spark.sql.hudi.catalog.HoodieCatalog" ,
                    "--conf", "spark.sql.extensions=org.apache.spark.sql.hudi.HoodieSparkSessionExtension" ,
                    "<enter S3 bucket path for EMR job>",
                    "<enter output S3 bucket name>",
                    "<enter output hudi table S3 path>"
                ]
            }
        }]
        
        Step2_EmrStart = EmrAddStepsOperator(
            task_id='Step2_EmrStart',
            job_flow_id=self.EMR_cluster_id,
            steps=emr_steps,
            dag=self.dag
        )
        
        Step3_EmrWatcher = EmrStepSensor(
            task_id='Step3_EmrWatcher',
            job_flow_id=self.EMR_cluster_id,
            step_id='{{ task_instance.xcom_pull("Step2_EmrStart", key="return_value")[0] }}',
            dag=self.dag
        )
        
        # Redshift Load Tasks
        Step4_RedshiftSpst = PostgresOperator(
            task_id='Step4_RedshiftSpst',
            sql='call sch_reporting.load_snapshot_data()',
            postgres_conn_id=self.RS_CONN_ID,
            dag=self.dag
        )
        
        #End
        end_pipeline = DummyOperator(task_id="YouWon")
        
        # Set dependencies
        start_pipeline >> Step1_GlueJob >> Step2_EmrStart >> Step3_EmrWatcher >> Step4_RedshiftSpst >> end_pipeline

# Create pipeline
pipeline = EtlSqlPipeline()
dag = pipeline.dag