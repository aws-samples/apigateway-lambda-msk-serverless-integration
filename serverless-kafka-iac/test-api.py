import boto3
import botocore
import requests
import sys
import json

# Stack Name
STACK_NAME = "ServerlessKafkaProducerStack"

# Create a CloudFormation client
cloudformation = boto3.client('cloudformation')

# Get Stack ARN
response = cloudformation.describe_stacks(StackName=STACK_NAME)
STACK_ARN = response['Stacks'][0]['StackId']

# Extract the region from the Stack ARN
REGION = STACK_ARN.split(':')[3]

# Check if the region was retrieved successfully
if not REGION:
    print("Failed to retrieve Region from stack ARN.")
    sys.exit(1)

# Get the Resource ID and Rest ID from the CloudFormation stack outputs
outputs = response['Stacks'][0]['Outputs']

ENDPOINT_URL = None
RESOURCE_PATH = None
HTTP_METHOD = None

for output in outputs:
    if "ProducerAPIEndpoint" in output['OutputKey']:
        ENDPOINT_URL = output['OutputValue']
    elif output['OutputKey'] == 'ProducerAPIOutputResourcePath':
        RESOURCE_PATH = output['OutputValue'].replace("/","")
    elif output['OutputKey'] == 'ProducerAPIOutputAPIMethod':
        HTTP_METHOD = output['OutputValue']


if not RESOURCE_PATH:
    print("Failed to retrieve Resource path from API Gateway endpoint CDK Stack output")
    sys.exit(1)

if not ENDPOINT_URL:
    print("Failed to retrieve Endpoint url from API Gateway endpoint CDK Stack output")
    sys.exit(1)

if not HTTP_METHOD:
    print("Failed to retrieve HTTP Method from API Gateway endpoint CDK Stack output")
    sys.exit(1)


# Build the endpoint URL
FINAL_ENDPOINT_URL = f"{ENDPOINT_URL}{RESOURCE_PATH}"

# Prepare the request he#aders and payload
headers = {
    'Content-Type': 'application/json'
}

payload = json.dumps({"payload": "Hello World"})

# Create a session using Botocore
session = botocore.session.get_session()
credentials = session.get_credentials().get_frozen_credentials()

# Sign the request using Signature Version 4
awsauth = botocore.auth.SigV4Auth(
    credentials, 'execute-api', REGION
)

# Sign the request
request = botocore.awsrequest.AWSRequest(
    method=HTTP_METHOD, url=FINAL_ENDPOINT_URL, data=payload, headers=headers
)

awsauth.add_auth(request)

# Perform the request using the signed headers
response = requests.request(
    method=HTTP_METHOD, url=FINAL_ENDPOINT_URL, data=payload, headers=dict(request.headers)
)

# Output the response
print(response.text)





# import boto3
# import botocore.auth
# import botocore.awsrequest
# import requests
# import json

# def invoke_api(api_url, region_name, payload):
#     # Create a boto3 session
#     session = boto3.Session()

#     # Get the credentials
#     credentials = session.get_credentials().get_frozen_credentials()

#     # Prepare the request
#     request = botocore.awsrequest.AWSRequest(method='POST', url=api_url, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
#     signer = botocore.auth.SigV4Auth(credentials, 'execute-api', region_name)

#     # Sign the request
#     signer.add_auth(request)

#     # Send the request
#     response = requests.post(api_url, headers=dict(request.headers), data=json.dumps(payload))

#     # Return the response
#     return response.text

# # Example usage
# api_url = "https://3bmzbor1mi.execute-api.eu-central-1.amazonaws.com/prod/ProducerAPIResource"
# region_name = 'eu-central-1'
# payload = {"payload": "Hello World"}
# response = invoke_api(api_url, region_name, payload)
# print(response)
