"""
This Lambda function handler is used to manage network interfaces associated with a specific security group within the AWS EC2 service. 
Upon receiving a 'Delete' event from CloudFormation, the function attempts to delete all available network interfaces tied to the security group. 
The function makes multiple attempts if necessary and communicates the success or failure of the operation back to CloudFormation.
It is intended to be used as CloudFormation Custom Resource to delete ENIs left out on destruction of stack resources.
For more informaation on the general problem that makes this necessary read:
https://stackoverflow.com/questions/41299662/aws-lambda-created-eni-not-deleting-while-deletion-of-stack
"""

import boto3
import os
import time
import random
import json
import http.client
from urllib.parse import urlparse

MAX_ATTEMPTS = 10  # Maximum number of delete attempts for network interfaces
response_body = ""

# Function to send a response to the CloudFormation service with a status and a message.
# This function constructs an HTTPS request and sends it to a pre-defined response URL.
def send_cfn_response(event, context, response_status, response_data):
    global response_body
    response_body = json.dumps({
        "Status": response_status,
        "Reason": "See the details in CloudWatch Log Stream: " + context.log_stream_name,
        "PhysicalResourceId": context.log_stream_name,
        "StackId": event['StackId'],
        "RequestId": event['RequestId'],
        "LogicalResourceId": event['LogicalResourceId'],
        "Data": response_data
    })

    headers = {
        'content-type': '',
        'content-length': str(len(response_body))
    }

    # Parse the response URL and send a HTTPS request to it
    try:
        parsed_url = urlparse(event['ResponseURL'])
        conn = http.client.HTTPSConnection(parsed_url.hostname)
        conn.request('PUT', parsed_url.path+'?'+parsed_url.query, response_body, headers)
        response = conn.getresponse()
        print("CloudFormation response status code:", response.status)
    except Exception as e:
        print("Failed to send CloudFormation response: ", str(e))

# The main handler function for the Lambda function.
# This function is triggered by CloudFormation events, specifically looking for 'Delete' events.
def handler(event, context):
    global response_body
    responseData = {}
    try:
        if event['RequestType'] == 'Delete':
            ec2 = boto3.client('ec2')  # AWS EC2 client to interact with the EC2 service
            security_group_id = os.environ['SECURITY_GROUP_ID']

            for attempt in range(MAX_ATTEMPTS):
                # Describe network interfaces with the specified security group ID and status
                enis = ec2.describe_network_interfaces(
                    Filters=[
                        {'Name': 'group-id', 'Values': [security_group_id]},
                        {'Name': 'status', 'Values': ['available']}
                    ]
                )['NetworkInterfaces']

                if not enis:  # No more network interfaces, break the loop
                    break

                # Attempt to delete each network interface
                for eni in enis:
                    try:
                        ec2.delete_network_interface(NetworkInterfaceId=eni['NetworkInterfaceId'])
                    except Exception as e:
                        print("Failed to delete " + eni['NetworkInterfaceId'] + ": " + str(e))

                # Sleep before retrying to give the system some time to process
                if attempt < MAX_ATTEMPTS - 1:  # Do not sleep after the last attempt
                    sleep_time = (2 ** attempt) + random.random()
                    print(f"Sleeping for {sleep_time} seconds before retrying.")
                    time.sleep(sleep_time)

            responseData['Message'] = "Successfully deleted network interfaces."
            print(responseData['Message'] + " Response to CloudFormation: " + json.dumps(responseData))
            send_cfn_response(event, context, 'SUCCESS', responseData)
    except Exception as e:
        print(str(e))
        responseData['Error'] = str(e)
        send_cfn_response(event, context, 'FAILED', responseData)

    return response_body
