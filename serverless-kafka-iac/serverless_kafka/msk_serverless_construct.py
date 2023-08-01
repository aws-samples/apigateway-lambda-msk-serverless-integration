# Importing necessary libraries and modules
import logging as log
from typing import List, Tuple
from aws_cdk import Duration, CustomResource
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_logs as logs
from aws_cdk import aws_msk as msk
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_iam as iam
from aws_cdk import custom_resources as cr
from constructs import Construct


log.basicConfig(level=log.INFO)  # setting basic log configuration

# Defining class for MSK serverless cluster
class MSKServerlessCluster(Construct):
    # Initializer
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        kafka_vpc: ec2.IVpc,
        cluster_id: str,
        cluster_name: str,
        security_group_id: str,
    ) -> None:
        super().__init__(scope, construct_id)  # calling parent initializer

        self.kafka_security_group = self.init_kafka_security_group(vpc=kafka_vpc, 
                                                                   security_group_id=security_group_id)  # initializing security group

        # initializing kafka cluster and setting security group
        self.kafka_cluster = self.init_kafka_cluster(vpc_stack=kafka_vpc, 
                                                     security_group=self.kafka_security_group, 
                                                     cluster_id=cluster_id, 
                                                     cluster_name=cluster_name)
        


    # Function to initialize kafka security group
    def init_kafka_security_group(self, vpc: ec2.IVpc, security_group_id:str):
        # defining security group
        kafka_security_group = ec2.SecurityGroup(
            self,
            security_group_id,
            vpc=vpc,
            description="MSK serverless demo kafka client security group"
        )

        # define list of ports that should communicate internally
        ports_list = [(2181, "Default Zookeeper"), (2182, "TLS Zookeeper"), (9098, "IAM Access")]

        # allowing tcp ports to connect internally        
        for port in ports_list:
            kafka_security_group.connections.allow_internally(ec2.Port.tcp(port=port[0]), description=port[1])

        return kafka_security_group  # returning the security group


    # Function to initialize kafka cluster
    def init_kafka_cluster(
        self, 
        vpc_stack: ec2.IVpc, 
        security_group: ec2.ISecurityGroup, 
        cluster_id: str,
        cluster_name: str,
    ) -> msk.CfnServerlessCluster:

        # setting up log group with a retention of one day
        logs.LogGroup(self, cluster_id + "BrokerLogs", retention=logs.RetentionDays.ONE_DAY)

        # defining logging info property
        logging_info_property = msk.CfnCluster.LoggingInfoProperty(
            broker_logs=msk.CfnCluster.BrokerLogsProperty(
                cloud_watch_logs=msk.CfnCluster.CloudWatchLogsProperty(
                    enabled=True,
                    log_group=cluster_id + "BrokerLogs"
                )
            )
        )

        # defining kafka cluster with various properties and configurations
        kafka_cluster = msk.CfnServerlessCluster(
            self,
            id=cluster_id,
            cluster_name=cluster_name,
            vpc_configs=[msk.CfnServerlessCluster.VpcConfigProperty(
                subnet_ids=vpc_stack.select_subnets(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                ).subnet_ids,
                security_groups=[security_group.security_group_id]  
            )],
            client_authentication=msk.CfnServerlessCluster.ClientAuthenticationProperty(
                sasl=msk.CfnServerlessCluster.SaslProperty(
                    iam=msk.CfnServerlessCluster.IamProperty(enabled=True),
                )
            ),
        )

        return kafka_cluster  # returning the kafka cluster

    # Property to get kafka cluster
    @property
    def get_kafka_cluster(self) -> msk.CfnServerlessCluster:
        return self.kafka_cluster

    # Property to get kafka security group
    @property
    def get_kafka_security_group(self) -> ec2.ISecurityGroup:
        return self.kafka_security_group
    
