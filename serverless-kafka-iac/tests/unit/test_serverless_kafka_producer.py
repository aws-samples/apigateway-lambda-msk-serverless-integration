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
from serverless_kafka.serverless_kafka_producer_stack import ServerlessKafkaProducerStack
from serverless_kafka.serverless_kafka_vpc_stack import ServerlessKafkaVPCStack

# Import resource suppressions from test_helpers
from .test_helpers import add_resource_suppressions

# Set logging to display info level logs
log.basicConfig(level=log.INFO)

# Define a pytest fixture for the demo_stack 
# The scope is set to "session" which means this fixture will be created once per test session
@pytest.fixture(scope="session")
def demo_stack() -> ServerlessKafkaProducerStack:
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

    # Instantiate the ServerlessKafkaProducerStack
    kafka_producer = ServerlessKafkaProducerStack(
        app,
        construct_id="ServerlessKafkaProducerStack",
        app_config_id="app_config",
        stack_config_id="serverless_kafka_producer_config",
        kafka_vpc=serverless_kafka_msk_stack.kafka_vpc,
        kafka_security_group=serverless_kafka_msk_stack.kafka_security_group,
        msk_arn=serverless_kafka_msk_stack.msk_arn,
        kafka_bootstrap_server=kafka_handler.get_kafka_bootstrap_server,
    )


    consumer_producer_role = kafka_producer.node.find_child("ProducerLambdaRole")
    consumer_producer_role_supressions = [
        
        (
            "AwsSolutions-IAM5",
            "Some * rules for logs:PutLogEvents, logs:CreateLogStream, logs:CreateLogGroup needed. Limited everything to the best known practices",
        )
    ]
    add_resource_suppressions(consumer_producer_role, consumer_producer_role_supressions)



    kafka_producer_policy = kafka_producer.node.find_child("ProducerLambdaPolicy")
    kafka_producer_policy_supressions = [
        
        (
            "AwsSolutions-IAM5",
            "Some * rules for logs:PutLogEvents, logs:CreateLogStream, logs:CreateLogGroup needed. Limited everything to the best known practices",
        )
    ]
    add_resource_suppressions(kafka_producer_policy, kafka_producer_policy_supressions)


    log_retention_role = kafka_producer.node.find_child("ProducerLambdaLogRetentionRole")
    log_retention_role_supressions = [
        
        (
            "AwsSolutions-IAM5",
            "Some * rules for logs:PutLogEvents, logs:CreateLogStream, logs:CreateLogGroup needed. Limited everything to the best known practices",
        )
    ]
    add_resource_suppressions(log_retention_role, log_retention_role_supressions)

    # Find the API gateway and add its suppressions
    api_gw = kafka_producer.node.find_child("ProducerAPI")
    api_gw_supressions = [
        (
            "AwsSolutions-COG4",
            "We are using IAM-authentication. Therefore no Cognito User Pools are needed",
        ),
    ]
    add_resource_suppressions(api_gw, api_gw_supressions)

    # Add Aspects to kafka_producer with AwsSolutionsChecks
    Aspects.of(kafka_producer).add(AwsSolutionsChecks(verbose=True))

    # Return the kafka_producer
    return kafka_producer

# Test for any error in the serverless producer stack
def test_serverless_producer_stack_errors(demo_stack):
    # Find any error related to AwsSolutions-* and log them
    error = assertions.Annotations.from_stack(demo_stack).find_error(
        "*", assertions.Match.string_like_regexp("AwsSolutions-.*")
    )
    log.error(error)

    # Assert that there is no error
    assert not error
