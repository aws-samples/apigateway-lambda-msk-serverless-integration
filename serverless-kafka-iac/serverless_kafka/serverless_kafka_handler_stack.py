# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Import necessary modules
import logging as log
import os
from pathlib import Path

from aws_cdk import (BundlingOptions, BundlingOutput, DockerVolume, Duration,
                     Stack, CustomResource, CfnOutput)
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_lambda as _lambda
from aws_cdk import custom_resources as cr
from constructs import Construct

from .helpers import get_topic_name, add_permissions_to_policy, map_string_to_retention_days

# Set up logging
log.basicConfig(level=log.INFO)

# Define the ServerlessKafkaHandlerStack class, inherited from the Stack class
class ServerlessKafkaHandlerStack(Stack):
    # Initialize the instance of the class
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
    ) -> None:
        # Call the constructor of the base class
        super().__init__(scope, construct_id, **kwargs)

        # Get the configuration for the stack from the context
        app_config = self.node.try_get_context(app_config_id) or {}
        serverless_kafka_handler_config = self.node.try_get_context(stack_config_id) or {}
        # Setting up a tag for the app
        self.tags.set_tag("app", app_config.get('application_tag', "ServerlessKafka"))
        # Setting up a tag for the stack
        self.tags.set_tag("stack", serverless_kafka_handler_config.get("stack_tag", "ServerlessKafkaHandlerStack"))

        # Get the topic name from the application config
        topic_name =  serverless_kafka_handler_config.get("topic_name", "ServerlessKafkaTopic")

        # Initialize the Kafka topic and retrieve the bootstrap server
        self.kafka_bootstrap_server = self.init_topic_and_retrieve_bootstrap_server(msk_arn=msk_arn, 
                                                                                    kafka_vpc=kafka_vpc, 
                                                                                    kafka_security_group=kafka_security_group, 
                                                                                    topic_name=topic_name,
                                                                                    serverless_kafka_handler_config=serverless_kafka_handler_config)

        # Create an output for the CloudFormation stack
        output = CfnOutput(
            self,
            "BootStrapServer",
            value=str(self.kafka_bootstrap_server),
            description="MSK Serverless Bootstrap Server",
            export_name="MSKServerlessBootstrapServer",
        )

    # Define a method to initialize the Kafka topic and retrieve the bootstrap server
    def init_topic_and_retrieve_bootstrap_server(self, msk_arn: str, kafka_vpc: ec2.IVpc, kafka_security_group: ec2.ISecurityGroup, topic_name:str, serverless_kafka_handler_config):

        # Define your base policy
        kafka_handler_policy = iam.ManagedPolicy(self, 
                                                id=serverless_kafka_handler_config.get("function_id", "HandlerLambda") + "Policy",
                                                managed_policy_name=serverless_kafka_handler_config.get("function_name", "ServerlessKafkaHandler") + "Policy",
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
                                                            "ec2:DeleteNetworkInterface"
                                                        ],
                                                        resources=["*"]
                                                    )
                                                ]
                                                )

        # Define the role for the Lambda Function
        kafka_handler_role = iam.Role(scope=self, 
                                    id=serverless_kafka_handler_config.get("function_id", "HandlerLambda") + "Role",
                                    assumed_by =iam.ServicePrincipal('lambda.amazonaws.com'),
                                    role_name=serverless_kafka_handler_config.get("function_name", "ServerlessKafkaHandler") + "Role",
                                    managed_policies=[kafka_handler_policy])
        

        # Add permissions to the role
        add_permissions_to_policy(role=kafka_handler_role, permissions= {
            "kafka-cluster:Connect": [msk_arn],
            "kafka-cluster:DescribeCluster": [msk_arn],
            "kafka-cluster:DescribeClusterDynamicConfiguration": [msk_arn],
            "kafka-cluster:AlterTopic": [get_topic_name(msk_arn, topic_name)],
            "kafka-cluster:AlterTopicDynamicConfiguration": [get_topic_name(msk_arn, topic_name)],
            "kafka-cluster:CreateTopic": [get_topic_name(msk_arn, topic_name)],
            "kafka-cluster:DeleteTopic": [get_topic_name(msk_arn, topic_name)],
            "kafka-cluster:DescribeTopic": [get_topic_name(msk_arn, topic_name)],
            "kafka-cluster:DescribeTopicDynamicConfiguration": [get_topic_name(msk_arn, topic_name)],
            "kafka:GetBootstrapBrokers": [msk_arn],
        })

        # Define the log retention role for the lambda function
        kafka_handler_log_retention_role = iam.Role(scope=self, 
                                      id=serverless_kafka_handler_config.get("function_id", "HandlerLambda") + "LogRetentionRole",
                                      assumed_by =iam.ServicePrincipal('lambda.amazonaws.com'),
                                      role_name=serverless_kafka_handler_config.get("function_name", "ServerlessKafkaHandler") + "LogRetentionRole",
                                      managed_policies=[kafka_handler_policy]
                                    )

        # Add permissions to the log retention role
        add_permissions_to_policy(role=kafka_handler_log_retention_role, permissions= {
                "logs:PutRetentionPolicy": ["arn:aws:logs:*:*:*"] ,
                "logs:DeleteRetentionPolicy": ["arn:aws:logs:*:*:*"]
        })


        # Define the AWS Lambda function and settings
        kafka_handler_lambda = _lambda.Function(
            self,
            id=serverless_kafka_handler_config.get("function_id", "HandlerLambda"),
            function_name=serverless_kafka_handler_config.get("function_name", "ServerlessKafkaHandler"),
            runtime=_lambda.Runtime.JAVA_17,
            handler="software.amazon.samples.kafka.lambda.KafkaHandler::handleRequest",
            timeout=Duration.seconds(serverless_kafka_handler_config.get("function_timeout_seconds", 150)),
            log_retention=map_string_to_retention_days(serverless_kafka_handler_config.get("function_log_retention_enum", "ONE_DAY")),
            code=self.build_mvn_package(),
            tracing=_lambda.Tracing.ACTIVE if serverless_kafka_handler_config.get("function_tracing_enabled", "yes") == "yes" else _lambda.Tracing.DISABLED,
            vpc=kafka_vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[kafka_security_group],
            reserved_concurrent_executions=serverless_kafka_handler_config.get("function_max_concurrency", 60),
            role=kafka_handler_role,            
            log_retention_role=kafka_handler_log_retention_role,
            environment={
                "MSK_CLUSTER_ARN": msk_arn,
                "JAVA_TOOL_OPTIONS": serverless_kafka_handler_config.get("function_java_tool_options", "-XX:+TieredCompilation -XX:TieredStopAtLevel=1 -DLOG_LEVEL=INFO")
            },
            memory_size=serverless_kafka_handler_config.get("function_memory_size", 256)
        )

        # Create the Custom Resource Provider that is triggered during stack create, update and destroy
        kafka_handler_custom_resourceprovider = cr.Provider(self, 
                                                            serverless_kafka_handler_config.get("function_id", "HandlerLambda") + "CustomResourceProvider",
                                                            on_event_handler=kafka_handler_lambda,
                                                            log_retention=logs.RetentionDays.ONE_DAY,
                                                            provider_function_name=serverless_kafka_handler_config.get("function_id", "HandlerLambda"),
                                                            )

        # Create the Custom Resource
        kafka_handler_custom_resource = CustomResource( self, 
                                                        serverless_kafka_handler_config.get("function_id", "HandlerLambda") + "CustomResource", 
                                                        service_token=kafka_handler_custom_resourceprovider.service_token,
                                                        properties={
                                                        'topicConfig': {
                                                            'topicName': topic_name,
                                                            'numPartitions': 1,
                                                            'replicationFactor': 2
                                                        }
                                                        })

        # Add the dependency on the Lambda function                                          
        kafka_handler_custom_resource.node.add_dependency(kafka_handler_lambda)

        # Retrieve the bootstrap servers from the response
        bootstrap_servers = kafka_handler_custom_resource.get_att('BootstrapServers').to_string()

        return bootstrap_servers

    # Define a method to build the Maven package
    def build_mvn_package(self):

        # Determine the home directory
        home = str(Path.home())

        # Specify the Maven home directory
        m2_home = os.path.join(home, ".m2/")
        log.info(f"Building Java Project ServerlessKafkaHandler using M2 home from directory: {m2_home}")

        # Define the Lambda function code
        code = _lambda.Code.from_asset(
            path=os.path.join("..", "kafka-handler"),
            bundling=BundlingOptions(
                image=_lambda.Runtime.JAVA_17.bundling_image,
                command=[
                    "/bin/sh",
                    "-c",
                    "mvn clean install -q -Dmaven.test.skip=true && cp /asset-input/target/KafkaHandler.zip /asset-output/",
                ],
                user="root",
                output_type=BundlingOutput.ARCHIVED,
                volumes=[DockerVolume(host_path=m2_home, container_path="/root/.m2/")],
            ),
        )
        return code

    # Getter method for the Kafka bootstrap server
    @property
    def get_kafka_bootstrap_server(self) -> ec2.ISecurityGroup:
        return self.kafka_bootstrap_server
