# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import logging as log

from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_logs as logs
from aws_cdk import aws_iam as iam
from constructs import Construct

log.basicConfig(level=log.INFO)


# ServerlessKafkaVPCStack class to define the VPC configuration and subnets for a Serverless Kafka application.
# This class includes the setup for private and public subnets, VPC flow logs, and necessary tagging.
class ServerlessKafkaVPCStack(Stack):

    #Initialize the ServerlessKafkaVPCStack.
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str, 
        app_config_id:str, 
        stack_config_id: str, 
        **kwargs
    ) -> None:

        super().__init__(scope, construct_id, **kwargs)
        
        # Get the application and stack configurations
        app_config = self.node.try_get_context(app_config_id) or {}
        vpc_config = self.node.try_get_context(stack_config_id) or {}

        vpc_name = vpc_config.get("vpc_name", "ServerlessKafkaVPC")

        # Tag the stack with the application and stack information
        self.tags.set_tag("app", app_config.get('application_tag', "ServerlessKafka"))
        self.tags.set_tag("stack", vpc_config.get("stack_tag", "ServerlessKafkaVPCStack"))

        # Define the subnets for the VPC
        self.subnets = [
            ec2.SubnetConfiguration(
                name=vpc_name+"Private",
                cidr_mask=24,
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
            ),
            ec2.SubnetConfiguration(
                name=vpc_name+"Public",
                cidr_mask=24,
                subnet_type=ec2.SubnetType.PUBLIC,
            ),
        ]

        # Create the VPC with the specified configuration
        self.vpc = ec2.Vpc(
            self,
            vpc_name,
            nat_gateways=1,
            max_azs=3,
            ip_addresses=ec2.IpAddresses.cidr(vpc_config.get("vpc_cidr_range","10.0.0.0/16")),
            subnet_configuration=self.subnets
        )

        # Enable VPC flow logs if specified in the configuration
        if vpc_config.get("enable_flow_logs","yes")=="yes":  
            log_group = logs.LogGroup(self, vpc_name+"FlowLogs", retention=logs.RetentionDays.ONE_DAY)
            role = iam.Role(self, vpc_name+"FlowLogsRole", assumed_by=iam.ServicePrincipal("vpc-flow-logs.amazonaws.com"))  # type: ignore
            self.vpc.add_flow_log(vpc_name+"FlowLog", destination=ec2.FlowLogDestination.to_cloud_watch_logs(log_group=log_group, iam_role=role))

    @property
    def get_kafka_vpc(self) -> ec2.IVpc:
        return self.vpc