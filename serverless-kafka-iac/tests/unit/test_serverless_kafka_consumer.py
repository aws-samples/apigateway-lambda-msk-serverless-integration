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
from serverless_kafka.serverless_kafka_consumer_stack import ServerlessKafkaConsumerStack
from serverless_kafka.serverless_kafka_vpc_stack import ServerlessKafkaVPCStack

# Import resource suppressions from test_helpers
from .test_helpers import add_resource_suppressions

# Set logging to display info level logs
log.basicConfig(level=log.INFO)

@pytest.fixture(scope="session")
def demo_stack() -> ServerlessKafkaConsumerStack:
    # Create an AWS CDK core application
    app = core.App()

    # Instantiate the ServerlessKafkaVPCStack
    vpc_stack = ServerlessKafkaVPCStack(
        app,
        construct_id="ServerlessKafkaVPCStack",
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

    # Instantiate the ServerlessKafkaConsumerStack
    kafka_consumer = ServerlessKafkaConsumerStack (
        app,
        construct_id="ServerlessKafkaConsumerStack",
        app_config_id="app_config",
        stack_config_id="serverless_kafka_consumer_config",
        kafka_vpc=serverless_kafka_msk_stack.kafka_vpc,
        kafka_security_group=serverless_kafka_msk_stack.kafka_security_group,
        msk_arn=serverless_kafka_msk_stack.msk_arn
    )


    consumer_function_role = kafka_consumer.node.find_child("ConsumerLambdaRole")
    consumer_function_role_supressions = [
        
        (
            "AwsSolutions-IAM4",
            "MSK Lambda Event Integration uses AWSLambdaMSKExecutionRole per default",
        ),

        (
            "AwsSolutions-IAM5",
            "Some * rules for logs:PutLogEvents, logs:CreateLogStream, logs:CreateLogGroup needed. Limited everything to the best known practices",
        )
    ]

    add_resource_suppressions(consumer_function_role, consumer_function_role_supressions)

    # Find child "ServerlessKafkaConsumer" and define and add resource suppressions
    consumer_function_policy = kafka_consumer.node.find_child("ConsumerLambdaPolicy")
    consumer_function_policy_supressions = [
        
        (
            "AwsSolutions-IAM5",
            "Some * rules for logs:PutLogEvents, logs:CreateLogStream, logs:CreateLogGroup needed. Limited everything to the best known practices",
        )
    ]

    add_resource_suppressions(consumer_function_policy, consumer_function_policy_supressions)

    log_retention_role = kafka_consumer.node.find_child("ConsumerLambdaLogRetentionRole")
    log_retention_role_supressions = [
        
        (
            "AwsSolutions-IAM5",
            "Some * rules for logs:PutLogEvents, logs:CreateLogStream, logs:CreateLogGroup needed. Limited everything to the best known practices",
        )
    ]
    add_resource_suppressions(log_retention_role, log_retention_role_supressions)

    # Find child "ServerlessKafkaConsumer" and define and add resource suppressions
    consumer_function = kafka_consumer.node.find_child("ConsumerLambda")
    consumer_function_supressions = [
        (
            "AwsSolutions-L1",
            "We are using the Runtime Java 11 the code was tested and build with",
        )
    ]
    add_resource_suppressions(consumer_function, consumer_function_supressions)

    # Add Aspects to kafka_consumer with AwsSolutionsChecks
    Aspects.of(kafka_consumer).add(AwsSolutionsChecks(verbose=True))

    # Return the kafka_consumer
    return kafka_consumer

# Test for any error in the serverless consumer stack
def test_serverless_consumer_stack_errors(demo_stack):
    # Find any error related to AwsSolutions-* and log them
    error = assertions.Annotations.from_stack(demo_stack).find_error(
        "*", assertions.Match.string_like_regexp("AwsSolutions-.*")
    )
    log.error(error)

    # Assert that there is no error
    assert not error
