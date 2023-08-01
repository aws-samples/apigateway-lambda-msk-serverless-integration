# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Import necessary libraries
import logging as log
import aws_cdk as core
import aws_cdk.assertions as assertions
import pytest
from aws_cdk import Aspects
from aws_cdk.aws_lambda import Function
from cdk_nag import AwsSolutionsChecks
from constructs import Construct, IConstruct

# Import necessary components from serverless_kafka
from serverless_kafka.serverless_kafka_msk_stack import ServerlessKafkaMSKStack
from serverless_kafka.serverless_kafka_handler_stack import ServerlessKafkaHandlerStack
from serverless_kafka.serverless_kafka_vpc_stack import ServerlessKafkaVPCStack

# Import resource suppressions from test_helpers
from .test_helpers import add_resource_suppressions

# Set logging to display info level logs
log.basicConfig(level=log.INFO)

# ServerlessKafkahandlerStack architecture with components like Kafkahandler LambdaFunction, API Gateway, 
# AWS CustomResource to read the Bootstrap URL of the MSK cluster, lambda for changing log retention period, 
# lambda function to read the bootstrap url.
@pytest.fixture(scope="session")
def demo_stack() -> ServerlessKafkaHandlerStack:
    # Create an AWS CDK core application
    app = core.App()

    # Instantiate the KafkaVPCStack
    vpc_stack = ServerlessKafkaVPCStack(
        app,
        construct_id="ServerlessServerlessKafkaVPCStack",
        app_config_id="app_config",
        stack_config_id="vpc_config",
    )

    # Instantiate the ServerlessKafkaMSKStack
    serverless_kafka_msk_stack = ServerlessKafkaMSKStack(
        app,
        construct_id="ServerlessKafkaMSKStack",
        app_config_id="app_config",
        stack_config_id="msk_serverless_config",
        vpcStack=vpc_stack,
    )

    # Instantiate the ServerlessKafkaHandlerStack
    kafka_handler = ServerlessKafkaHandlerStack(
        app,
        construct_id="ServerlessKafkaHandlerStack",
        app_config_id="app_config",
        stack_config_id="serverless_kafka_handler_config",
        kafka_vpc=serverless_kafka_msk_stack.kafka_vpc,
        kafka_security_group=serverless_kafka_msk_stack.kafka_security_group,
        msk_arn=serverless_kafka_msk_stack.msk_arn
    )


    # Find child "ServerlessKafkaConsumer" and define and add resource suppressions
    custom_resource_provider_role = kafka_handler.node.find_child("HandlerLambdaCustomResourceProvider")
    custom_resource_provider_role_supressions = [
         (
            "AwsSolutions-IAM4",
            "Custom Resource provider uses AWSLambdaBasicExecutionRole per default",
        ),       
        (
            "AwsSolutions-IAM5",
            "Some * rules for logs:PutLogEvents, logs:CreateLogStream, logs:CreateLogGroup needed. Limited everything to the best known practices",
        )
    ]

    add_resource_suppressions(custom_resource_provider_role, custom_resource_provider_role_supressions)

    consumer_handler_role = kafka_handler.node.find_child("HandlerLambdaRole")
    consumer_handler_role_supressions = [
        
        (
            "AwsSolutions-IAM5",
            "Some * rules for logs:PutLogEvents, logs:CreateLogStream, logs:CreateLogGroup needed. Limited everything to the best known practices",
        )
    ]
    add_resource_suppressions(consumer_handler_role, consumer_handler_role_supressions)



    consumer_handler_policy = kafka_handler.node.find_child("HandlerLambdaPolicy")
    consumer_handler_policy_supressions = [
        
        (
            "AwsSolutions-IAM5",
            "Some * rules for logs:PutLogEvents, logs:CreateLogStream, logs:CreateLogGroup needed. Limited everything to the best known practices",
        )
    ]
    add_resource_suppressions(consumer_handler_policy, consumer_handler_policy_supressions)


    log_retention_role = kafka_handler.node.find_child("HandlerLambdaLogRetentionRole")
    log_retention_role_supressions = [
        
        (
            "AwsSolutions-IAM5",
            "Some * rules for logs:PutLogEvents, logs:CreateLogStream, logs:CreateLogGroup needed. Limited everything to the best known practices",
        )
    ]
    add_resource_suppressions(log_retention_role, log_retention_role_supressions)

    # Add Aspects to kafka_handler with AwsSolutionsChecks
    Aspects.of(kafka_handler).add(AwsSolutionsChecks(verbose=True))

    # Return the kafka_handler
    return kafka_handler

# Test for any error in the serverless handler stack
def test_serverless_handler_stack_errors(demo_stack):
    # Find any error related to AwsSolutions-* and log them
    error = assertions.Annotations.from_stack(demo_stack).find_error(
        "*", assertions.Match.string_like_regexp("AwsSolutions-.*")
    )
    log.error(error)

    # Assert that there is no error
    assert not error
