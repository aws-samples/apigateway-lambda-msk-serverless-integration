# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
import base64
import os

# Define the TOPIC_NAME variable from environment variable or set default as "ServerlessKafkaTopic"
TOPIC_NAME = os.environ.get('TOPIC_NAME', "ServerlessKafkaTopic")

# The lambda_handler is the default AWS Lambda function entry point.
def lambda_handler(event, context):
    # Create a partition key string by appending "-0" to the TOPIC_NAME
    str_partition_key = TOPIC_NAME + "-0"
    # Decode the value from base64 format to a string format.
    records = event["records"][str_partition_key]
    nrofrecords = 0
    for record in records:
        
        uuid = ""
        value = ""
        # The key is extracted from the event object using the partition key
        if 'key' in record:
            uuid = base64.b64decode(record["key"]).decode('utf-8')
        #The value is extracted from the event object using the partition key
        if 'value' in record:
            value = base64.b64decode(record["value"]).decode('utf-8')
            nrofrecords += 1

        print("Received a message from MSK with uuid: " + uuid + " and value: " + value )

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": str(nrofrecords) + " Records processed",
            }
        ),
    }
