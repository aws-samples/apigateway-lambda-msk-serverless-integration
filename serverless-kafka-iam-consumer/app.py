# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
import base64
import os
from aws_lambda_powertools import Logger
from aws_lambda_powertools import Tracer
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext


# Define the TOPIC_NAME variable from environment variable or set default as "ServerlessKafkaTopic"
TOPIC_NAME = os.environ.get('TOPIC_NAME', "ServerlessKafkaTopic")

tracer = Tracer() 
logger = Logger()
metrics = Metrics()


@tracer.capture_method
def log_record(record) -> None:
        uuid = ""
        value = ""
        # The key is extracted from the event object using the partition key
        if 'key' in record:
            uuid = base64.b64decode(record["key"]).decode('utf-8')
        #The value is extracted from the event object using the partition key
        if 'value' in record:
            value = base64.b64decode(record["value"]).decode('utf-8')
        
        logger.info("Received a message from MSK with uuid: " + uuid + " and value: " + value )



# The lambda_handler is the default AWS Lambda function entry point.
@tracer.capture_lambda_handler
# ensures metrics are flushed upon request completion/failure and capturing ColdStart metric
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict, context: LambdaContext):
    # Create a partition key string by appending "-0" to the TOPIC_NAME
    str_partition_key = TOPIC_NAME + "-0"
    # Decode the value from base64 format to a string format.
    records = event["records"][str_partition_key]
    nrofrecords = 0
    for record in records:
        metrics.add_metric(name="TransferredMessages", unit=MetricUnit.Count, value=1)
        log_record(record)
        nrofrecords += 1



    metrics.flush_metrics()
    tracer.put_annotation("nrofrecords", nrofrecords)
    tracer.put_metadata("test", "test") 
 
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": str(nrofrecords) + " Records processed",
            }
        ),
    }
