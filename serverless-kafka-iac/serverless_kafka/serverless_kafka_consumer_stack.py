# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import logging as log
from pathlib import Path
import subprocess, shutil, os

from aws_cdk import (Duration, Stack)
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk.aws_lambda_event_sources import ManagedKafkaEventSource
from constructs import Construct

from .helpers import get_group_name,  get_topic_name, add_permissions_to_policy, map_string_to_retention_days


log.basicConfig(level=log.INFO)

# Stack for a Kafka consumer Lambda function.
class ServerlessKafkaConsumerStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        app_config_id:str , 
        stack_config_id: str, 
        kafka_vpc: ec2.IVpc,
        kafka_security_group: ec2.ISecurityGroup,
        msk_arn: str,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        # Get the configuration for the stack from the context
        app_config = self.node.try_get_context(app_config_id) or {}
        serverless_kafka_consumer_config = self.node.try_get_context(stack_config_id) or {}

        # Setting up a tag for the stack
        self.tags.set_tag("app", app_config.get('application_tag', "ServerlessKafka"))
        # Setting up a tag for the stack
        self.tags.set_tag("stack", serverless_kafka_consumer_config.get("stack_tag", "ServerlessKafkaConsumerStack"))

        # Get the topic name from the stack config
        topic_name = serverless_kafka_consumer_config.get("topic_name", "ServerlessKafkaTopic")

        # Initialize the Kafka consumer Lambda function
        self.init_kafka_consumer_lambda(
            vpc=kafka_vpc,
            kafka_security_group=kafka_security_group,
            msk_arn=msk_arn,
            topic_name=topic_name,
            app_config=app_config,
            serverless_kafka_consumer_config=serverless_kafka_consumer_config

        )

    # Create the Kafka consumer Lambda function
    def init_kafka_consumer_lambda(
        self,
        vpc: ec2.IVpc,
        kafka_security_group: ec2.ISecurityGroup,
        msk_arn: str,
        topic_name: str,
        app_config,
        serverless_kafka_consumer_config

    ):

        # Define consumer group ID
        consumer_group_id = serverless_kafka_consumer_config.get("function_event_source_consumer_group_id", "ServerlessKafkaConsumerGroup",)


        # Create base policy to use for the Lambda function
        kafka_consumer_policy = iam.ManagedPolicy(self, 
                                                serverless_kafka_consumer_config.get("function_id", "ConsumerLambda") + "Policy",
                                                managed_policy_name=serverless_kafka_consumer_config.get("function_name", "ServerlessKafkaConsumer") + "Policy",
                                                statements=[
                                                    iam.PolicyStatement(
                                                        actions=[
                                                            "logs:CreateLogGroup",
                                                            "logs:CreateLogStream",
                                                            "logs:PutLogEvents"
                                                        ],
                                                        resources=["arn:aws:logs:*:*:*"]
                                                    ),
                                                    iam.PolicyStatement(
                                                        actions=[
                                                            "ec2:CreateNetworkInterface",
                                                            "ec2:DescribeNetworkInterfaces",
                                                            "ec2:DeleteNetworkInterface",
                                                            "kafka:DescribeCluster",
                                                            "kafka:DescribeClusterV2",
                                                            "kafka:GetBootstrapBrokers",
                                                            "ec2:DescribeVpcs",
                                                            "ec2:DeleteNetworkInterface",
                                                            "ec2:DescribeSubnets",
                                                            "ec2:DescribeSecurityGroups",
                                                            "logs:CreateLogGroup",
                                                            "logs:CreateLogStream",
                                                            "logs:PutLogEvents",
                                                            "xray:PutTraceSegments",
                                                            "xray:PutTelemetryRecords"

                                                        ],
                                                        resources=["*"]
                                                    )
                                                ]
                                                )


        # Create base role to use for the Lambda function
        kafka_consumer_role = iam.Role(scope=self, 
                                      id=serverless_kafka_consumer_config.get("function_id", "ConsumerLambda") + "Role",
                                      assumed_by =iam.ServicePrincipal('lambda.amazonaws.com'),
                                      role_name=serverless_kafka_consumer_config.get("function_name", "ServerlessKafkaConsumer") + "Role",
                                      managed_policies=[kafka_consumer_policy])

        
        # Add policies to base role to allow access to the MSK cluster
        add_permissions_to_policy(role=kafka_consumer_role, permissions= {
            "kafka-cluster:Connect": [msk_arn],
            "kafka-cluster:DescribeGroup": [get_group_name(msk_arn, consumer_group_id)],
            "kafka-cluster:AlterGroup": [get_group_name(msk_arn, consumer_group_id)],
            "kafka-cluster:DescribeTopic": [get_topic_name(msk_arn, topic_name)],
            "kafka-cluster:ReadData": [get_topic_name(msk_arn, topic_name)],
            "kafka-cluster:ReadGroup": [get_group_name(msk_arn, consumer_group_id)],
            "kafka-cluster:DescribeClusterDynamicConfiguration": [msk_arn]
        })

        # Create base role to use for the Lambda function that performs log retention
        kafka_consumer_log_retention_role = iam.Role(scope=self, 
                                      id=serverless_kafka_consumer_config.get("function_id", "ConsumerLambda") + "LogRetentionRole",
                                      assumed_by =iam.ServicePrincipal('lambda.amazonaws.com'),
                                      role_name=serverless_kafka_consumer_config.get("function_name", "ServerlessKafkaConsumer") + "LogRetentionRole",
                                      managed_policies=[kafka_consumer_policy]
                                    )

        # Add policies to log retention role 
        add_permissions_to_policy(role=kafka_consumer_log_retention_role, permissions= {
                "logs:PutRetentionPolicy": ["arn:aws:logs:*:*:*"] ,
                "logs:DeleteRetentionPolicy": ["arn:aws:logs:*:*:*"]
        })
        
        consumer_function_lambda_Layer= _lambda.LayerVersion.from_layer_version_arn(self, 
                                                                                    serverless_kafka_consumer_config.get("function_id", "ConsumerLambda") + "Layer", 
                                                                                     layer_version_arn=f"arn:aws:lambda:{self.region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:40")

        # Create Lambda function and settings
        consumer_function = _lambda.Function(
            self,
            id=serverless_kafka_consumer_config.get("function_id", "ConsumerLambda"),
            function_name=serverless_kafka_consumer_config.get("function_name", "ServerlessKafkaConsumer"),
            runtime=_lambda.Runtime.PYTHON_3_11,  # type: ignore
            handler="app.lambda_handler",
            timeout=Duration.seconds(serverless_kafka_consumer_config.get("function_timeout_seconds", 150)),
            log_retention=map_string_to_retention_days(serverless_kafka_consumer_config.get("function_log_retention_enum", "ONE_DAY")),
            code=_lambda.Code.from_asset(path= '../serverless-kafka-iam-consumer'),
            tracing=_lambda.Tracing.ACTIVE if serverless_kafka_consumer_config.get("function_tracing_enabled", "yes") else _lambda.Tracing.DISABLED,
            vpc=vpc,
            layers=[consumer_function_lambda_Layer],
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            environment={
                "TOPIC_NAME": topic_name,
                "POWERTOOLS_SERVICE_NAME": serverless_kafka_consumer_config.get("function_name", "ServerlessKafkaConsumer"),
                "POWERTOOLS_METRICS_NAMESPACE": app_config.get('application_tag', "ServerlessKafka"),
                "LOG_LEVEL": "INFO"
            },
            role=kafka_consumer_role,
            log_retention_role=kafka_consumer_log_retention_role
            ,
            security_groups=[kafka_security_group],
            reserved_concurrent_executions=serverless_kafka_consumer_config.get("function_max_concurrency", 60),
            memory_size=serverless_kafka_consumer_config.get("function_memory_size", 256)
        )

        # Attach Kafka event source
        consumer_function.add_event_source(
            ManagedKafkaEventSource(
                cluster_arn=msk_arn,
                topic=topic_name,

                batch_size=serverless_kafka_consumer_config.get("function_event_source_batch_size", 100),
                consumer_group_id=consumer_group_id,
                starting_position=_lambda.StartingPosition.TRIM_HORIZON,
            )
        )

