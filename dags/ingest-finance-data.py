"""
### Helper DAG that generated mock data for the finance_elt DAG

This DAG runs a script located in `include/create_mock_data.py` that generates
mock data for the finance_elt DAG and loads that mock data to S3/MinIO.
"""

from airflow.decorators import dag, task
from pendulum import datetime
from airflow.providers.amazon.aws.transfers.local_to_s3 import (
    LocalFilesystemToS3Operator,
)
from airflow.providers.amazon.aws.operators.s3 import S3CreateBucketOperator
import os
from include.create_mock_data import generate_mock_data


AWS_CONN_ID = "aws_default"
DATA_BUCKET_NAME = "finance-elt-ml-data"

@dag(
    start_date=datetime(2025, 4, 14),
    schedule="@daily",
    catchup=False,
    tags=["helper"],
)
def in_finance_data():

    @task
    def generate_mock_data_task():
        generate_mock_data()

    create_bucket = S3CreateBucketOperator(
        task_id="create_bucket", aws_conn_id=AWS_CONN_ID, bucket_name=DATA_BUCKET_NAME
    )

    @task
    def get_kwargs():
        list_of_kwargs = []
        for filename in os.listdir("include/mock_data"):
            if "charge" in filename:
                kwargs_dict = {
                    "filename": f"include/mock_data/{filename}",
                    "dest_key": f"charge/{filename}",
                }
            elif "satisfaction" in filename:
                kwargs_dict = {
                    "filename": f"include/mock_data/{filename}",
                    "dest_key": f"satisfaction/{filename}",
                }
            else:
                print(
                    f"Skipping {filename} because it's not a charge or satisfaction file"
                )
                continue
            list_of_kwargs.append(kwargs_dict)

        return list_of_kwargs
    
    upload_kwargs = get_kwargs()
    generate_mock_data_task() >> upload_kwargs

    upload_mock_data = LocalFilesystemToS3Operator.partial(
        task_id="upload_mock_data",
        dest_bucket=DATA_BUCKET_NAME,
        aws_conn_id=AWS_CONN_ID,
        replace="True",
    ).expand_kwargs(upload_kwargs)

    create_bucket >> upload_mock_data

in_finance_data()