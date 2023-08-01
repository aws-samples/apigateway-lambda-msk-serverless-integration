# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Import the required modules
import logging as log

from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from constructs import Construct

# Import the constructs that are used to build up this stack
from serverless_kafka.bastion_construct import BastionHost
from serverless_kafka.msk_serverless_construct import MSKServerlessCluster
from serverless_kafka.delete_enis_construct import DeleteENIsConstruct

# Initialize logging
log.basicConfig(level=log.INFO)

# ServerlessKafkaMSKStack is a construct that sets up a stack including a MSK serverless cluster,
# a bastion host, and a construct to handle deletion of ENIs
class ServerlessKafkaMSKStack(Stack):
    def __init__(
        self, scope: Construct,
        construct_id: str, 
        app_config_id: str, 
        stack_config_id: str, 
        vpcStack, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get the configuration for the stack from the context
        app_config = self.node.try_get_context(app_config_id) or {}
        msk_serverless_config = self.node.try_get_context(stack_config_id) or {}

        # Setting up a tag for the stack
        self.tags.set_tag("app", app_config.get('application_tag', "ServerlessKafka"))
        # Setting up a tag for the stack
        self.tags.set_tag("stack", msk_serverless_config.get("stack_tag", "ServerlessKafkaMSKStack"))

        # Get the Cluster name from the stack config
        cluster_name = msk_serverless_config.get("cluster_name", "ServerlessKafkaCluster")

        # Get the Cluster ID from the stack config
        cluster_id = msk_serverless_config.get("cluster_id", "ServerlessKafkaCluster")

        # Get the Cluster ID from the stack config
        security_group_id = msk_serverless_config.get("security_group_id", "ClusterSecGroup")
        
        # Get the Kafka VPC from the passed vpcStack
        self.kafka_vpc = vpcStack.get_kafka_vpc

        # Create a MSK serverless cluster
        msk = MSKServerlessCluster(self, "msk", kafka_vpc=self.kafka_vpc, cluster_id=cluster_id, cluster_name=cluster_name, security_group_id=security_group_id)

        # Get the ARN and the security group of the MSK cluster
        self.msk_arn = msk.kafka_cluster.attr_arn
        self.kafka_security_group = msk.get_kafka_security_group
        if msk_serverless_config.get("enable_bastion_host", "yes") == "yes":
            # Create a bastion host for accessing the Kafka cluster
            bastion_host = BastionHost(
                self,
                construct_id=cluster_id + "Bastionhost",
                region=self.region,
                kafka_vpc=self.kafka_vpc,
                msk_cluster_arn=self.msk_arn,
                cluster_id=cluster_id,
                kafka_cluster_security_group=self.kafka_security_group,
                instance_type=msk_serverless_config.get("bastion_host_instance_type", ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE2, ec2.InstanceSize.MICRO).to_string())
            )

        # Create a construct to handle deletion of ENIs created by the Consumer lambda function
        # This is necessary to prevent issues with stack deletion.
        if msk_serverless_config.get("enable_eni_delete", "yes") == "yes":
          delete_enis_construct = DeleteENIsConstruct(self, "DeleteENIsLambda", security_group_id)


    # Getter methods to get the ARN of the MSK cluster, the Kafka VPC, the bootstrap server of Kafka, and the Kafka security group.
    @property
    def get_msk_arn(self) -> str:
        return str(self.msk_arn)

    @property
    def get_kafka_vpc(self) -> ec2.IVpc:
        return self.kafka_vpc

    @property
    def get_kafka_bootstrap_server(self) -> str:
        return str(self.kafka_boostrap_server)

    @property
    def get_kafka_security_group(self) -> ec2.ISecurityGroup:
        return self.kafka_security_group
