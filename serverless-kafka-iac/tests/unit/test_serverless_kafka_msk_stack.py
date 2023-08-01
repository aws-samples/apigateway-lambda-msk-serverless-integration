# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Import the necessary modules
import logging as log
import aws_cdk as core
import aws_cdk.assertions as assertions
import pytest
from aws_cdk import Aspects
from aws_cdk.aws_lambda import Function
from cdk_nag import AwsSolutionsChecks
from serverless_kafka.serverless_kafka_msk_stack import ServerlessKafkaMSKStack
from serverless_kafka.serverless_kafka_vpc_stack import ServerlessKafkaVPCStack
from constructs import Construct, IConstruct
import pdb
from .test_helpers import add_resource_suppressions

# Set the logging level to INFO
log.basicConfig(level=log.INFO)

# Define a pytest fixture for creating an MSK serverless stack
@pytest.fixture(scope="session")
def serverless_kafka_msk_stack() -> ServerlessKafkaMSKStack:
    # Initialize the AWS CDK app
    app = core.App()
    
    # Create a Kafka VPC stack
    vpc_stack = ServerlessKafkaVPCStack(
        app,
        construct_id="ServerlessKafkaVPCStack",
        app_config_id="app_config",
        stack_config_id="vpc_config",
    )

    # Create an MSK serverless stack
    serverless_kafka_msk_stack = ServerlessKafkaMSKStack(
        app,
        construct_id="ServerlessKafkaMSKStack",
        app_config_id="app_config",
        stack_config_id="msk_serverless_config",
        vpcStack=vpc_stack,
    )

    # Define suppressions for managed policies
    managed_policies_supressions = [
        (
            "AwsSolutions-IAM4",
            "Custom Resource Provider for DeleteENICustomResource uses AWSLambdabasicExecution-Role by default",
        ),
        (
            "AwsSolutions-IAM5",
            "The AWS Managed AWSLambdaBasicExecutionRole has a * rule for logs:PutLogEvents, logs:CreateLogStream, logs:CreateLogGroup",
        )
    ]
    
    # Add suppressions to the MSK serverless stack
    add_resource_suppressions(serverless_kafka_msk_stack, managed_policies_supressions)   

    # Find the Bastion host child and define its suppressions
    bastion_host = serverless_kafka_msk_stack.node.find_child("ServerlessKafkaClusterBastionhost")
    bastion_host_supressions = [
        (
            "AwsSolutions-EC28", 
            "Detailed logging for Bastion host is not required for this demo"),
        (
            "AwsSolutions-EC29",
            "As this is example code as part of blogpost termination protection is not required",
        )
    ]

    # Add suppressions to the Bastion host
    add_resource_suppressions(bastion_host, bastion_host_supressions)
    
    # Add AWS Solutions Checks to the MSK serverless stack
    Aspects.of(serverless_kafka_msk_stack).add(AwsSolutionsChecks(verbose=True))
    
    # Return the MSK serverless stack
    return serverless_kafka_msk_stack

# Define a test to check if there are no errors in the MSK serverless stack
def test_serverless_kafka_msk_stack_no_errors(serverless_kafka_msk_stack):
    
    # Find errors in the MSK serverless stack and log them
    errors = assertions.Annotations.from_stack(serverless_kafka_msk_stack).find_error(
        "*", assertions.Match.string_like_regexp("AwsSolutions-.*")
    )

    log.error(errors)

    # Assert that there are no errors
    assert not errors
