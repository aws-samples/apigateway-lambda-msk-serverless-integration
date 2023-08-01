# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os

import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2

from serverless_kafka.serverless_kafka_vpc_stack import ServerlessKafkaVPCStack

from serverless_kafka.helpers import get_parameter

from serverless_kafka.serverless_kafka_consumer_stack import ServerlessKafkaConsumerStack
from serverless_kafka.serverless_kafka_producer_stack import ServerlessKafkaProducerStack
from serverless_kafka.serverless_kafka_handler_stack import ServerlessKafkaHandlerStack
from serverless_kafka.serverless_kafka_vpc_stack import ServerlessKafkaVPCStack
from serverless_kafka.serverless_kafka_msk_stack import ServerlessKafkaMSKStack

#######################################################################################################################
########################################################################################################################
# The solution ist configured to use the cdk.context.json file to define the context.
# Alternatively you can define the context here (see example below) or overwrite the stack-context using -c parameter
# eg. cdk deploy --c vpc_config={ "stack_tag": "ServerlessKafkaVPCStack", "vpc_name": "ServerlessKafkaVPC", 
# "vpc_cidr_range": "10.0.0.0/16", "enable_flow_logs": "yes" }
#
#
# context = {  
#     "app_config": {
#         "application_tag": "ServerlessKafka"
#     },  
#     "vpc_config": {
#         "stack_tag": "ServerlessKafkaVPCStack",
# ...
#         "topic_name": "ServerlessKafkaTopic"
#     },
#     "serverless_kafka_consumer_config": {
#         "stack_tag": "ServerlessKafkaConsumerStack",
#         "function_id": "ServerlessKafkaConsumerLambda",
#         "function_name": "ServerlessKafkaConsumerLambda",
#         "function_timeout_seconds": 150,
#         "function_log_retention_enum": "ONE_DAY", 
#         "function_max_concurrency": 60,
#         "function_memory_size": 256,
#         "function_tracing_enabled": "yes",
#         "function_event_source_consumer_group_id": "KafkaServerlessConsumerGroup",
#         "function_event_source_batch_size": 100,
#         "topic_name": "ServerlessKafkaTopic"
#     }
# }
#
# app = cdk.App(context=context)
#######################################################################################################################
#######################################################################################################################

app = cdk.App()


vpcStack = ServerlessKafkaVPCStack(
    app,
    construct_id="ServerlessKafkaVPCStack",
    app_config_id="app_config",
    stack_config_id="vpc_config",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
    )
)

serverless_kafka_msk_stack = ServerlessKafkaMSKStack(
    app,
    construct_id="ServerlessKafkaMSKStack",
    app_config_id="app_config",
    stack_config_id="msk_serverless_config",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
    ),
    vpcStack=vpcStack,
)

serverless_handler = ServerlessKafkaHandlerStack(
    app,
    construct_id="ServerlessKafkaHandlerStack",
    app_config_id="app_config",
    stack_config_id="serverless_kafka_handler_config",
    kafka_vpc=serverless_kafka_msk_stack.kafka_vpc,
    kafka_security_group=serverless_kafka_msk_stack.kafka_security_group,
    msk_arn=serverless_kafka_msk_stack.msk_arn,
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
    )
)

serverless_producer = ServerlessKafkaProducerStack(
    app,
    construct_id="ServerlessKafkaProducerStack",
    app_config_id="app_config",
    stack_config_id="serverless_kafka_producer_config",
    kafka_vpc=serverless_kafka_msk_stack.kafka_vpc,
    kafka_security_group=serverless_kafka_msk_stack.kafka_security_group,
    msk_arn=serverless_kafka_msk_stack.msk_arn,
    kafka_bootstrap_server=serverless_handler.get_kafka_bootstrap_server,
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
    )
)

serverless_consumer = ServerlessKafkaConsumerStack(
     app,
    construct_id="ServerlessKafkaConsumerStack",
    app_config_id="app_config",
    stack_config_id="serverless_kafka_consumer_config",
    kafka_vpc=serverless_kafka_msk_stack.kafka_vpc,
    kafka_security_group=serverless_kafka_msk_stack.kafka_security_group,
    msk_arn=serverless_kafka_msk_stack.msk_arn,
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
    )
)
serverless_consumer.add_dependency(serverless_handler)

app.synth()
