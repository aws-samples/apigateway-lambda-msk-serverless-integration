# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Import the necessary modules
import logging as log
import aws_cdk as core
import aws_cdk.assertions as assertions
import pytest
from aws_cdk import Aspects
from cdk_nag import AwsSolutionsChecks
from serverless_kafka.serverless_kafka_vpc_stack import ServerlessKafkaVPCStack
from .test_helpers import add_resource_suppressions

# Set the logging level to INFO
log.basicConfig(level=log.INFO)

# Define a pytest fixture for creating a Kafka VPC stack
@pytest.fixture(scope="session")
def demo_stack() -> ServerlessKafkaVPCStack:
    # Initialize the AWS CDK app
    app = core.App()
    
    # Create a Kafka VPC stack
    vpc_stack = ServerlessKafkaVPCStack(
        app,
        construct_id="ServerlessKafkaVPCStack",
        app_config_id="app_config",
        stack_config_id="vpc_config",
    )
  
    # Add AWS Solutions Checks to the Kafka VPC stack
    Aspects.of(vpc_stack).add(AwsSolutionsChecks(verbose=True))
    
    # Return the Kafka VPC stack
    return vpc_stack



# Define a test to check if there are no errors in the Kafka VPC stack
def test_serverless_kafka_vpc_stack_no_errors(demo_stack):
    # Find errors in the Kafka VPC stack and log them
    errors = assertions.Annotations.from_stack(demo_stack).find_error(
        "*", assertions.Match.string_like_regexp("AwsSolutions-.*")
    )

    log.error(errors)

    # Assert that there are no errors
    assert not errors
