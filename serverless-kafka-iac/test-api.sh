#!/bin/bash

# Stack Name
STACK_NAME="ServerlessKafkaProducerStack"

# Get Stack ARN
STACK_ARN=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query "Stacks[0].StackId" --output text)

# Extract the region from the Stack ARN
REGION=$(echo $STACK_ARN | cut -d':' -f4)

# Check if Resource ID and Rest ID were retrieved successfully
if [ -z "$REGION" ]; then
  echo "Failed to retrieve Region from stack ARN."
  exit 1
fi

# Get the Resource ID and Rest ID from the CloudFormation stack outputs
RESOURCE_ID=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query "Stacks[0].Outputs[?OutputKey=='ProducerAPIOutputResourceID'].OutputValue" --output text)

# Check if Resource ID and Rest ID were retrieved successfully
if [ -z "$RESOURCE_ID" ]; then
  echo "Failed to retrieve Resource ID from API Gateway endpoint"
  exit 1
fi

REST_ID=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query "Stacks[0].Outputs[?OutputKey=='ProducerAPIOutputRestID'].OutputValue" --output text)

# Check if Resource ID and Rest ID were retrieved successfully
if [ -z "$REST_ID" ]; then
  echo "Failed to retrieve Rest ID from API Gateway endpoint".
  exit 1
fi

# Path and HTTP Method (update these according to the specific endpoint you're invoking)
EP_PATH="/"
HTTP_METHOD="POST"


# Test invoke the method
OUTPUT=$(aws apigateway test-invoke-method --rest-api-id "$REST_ID" --resource-id "$RESOURCE_ID" --http-method "$HTTP_METHOD" --path-with-query-string "$ENDPOINT_PATH" --body '{"payload": "Hello World"}'  --region "$REGION" --query "body" --output text)

echo $OUTPUT
