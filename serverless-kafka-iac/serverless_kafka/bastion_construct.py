# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Importing necessary modules and classes
import logging as log

from aws_cdk import CfnOutput
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from constructs import Construct

from .helpers import get_group_name, get_topic_name

# Setting up logging with level INFO
log.basicConfig(level=log.INFO)

# Defining a custom Construct for creating a Bastion Host
class BastionHost(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        kafka_vpc: ec2.IVpc,
        msk_cluster_arn: str,
        cluster_id: str,
        region: str,
        kafka_cluster_security_group: ec2.ISecurityGroup,
        instance_type: str,
    ) -> None:
        super().__init__(scope, construct_id)

        vpc = kafka_vpc

        kafka_bastion_host_security_group = self.init_kafka_bastion_host_security_group(
            vpc=vpc, cluster_id=cluster_id
        )

        bastion_host = self.init_bastion_host(
            vpc=vpc,
            kafka_cluster_arn=msk_cluster_arn,
            region=region,
            cluster_id=cluster_id,
            kafka_bastion_host_security_group=kafka_bastion_host_security_group,
            kafka_cluster_security_group=kafka_cluster_security_group,
            instance_type=instance_type,
        )

    def init_bastion_host(
        self,
        vpc: ec2.IVpc,
        kafka_cluster_arn: str,
        cluster_id: str,
        kafka_bastion_host_security_group: ec2.ISecurityGroup,
        kafka_cluster_security_group: ec2.ISecurityGroup,
        region: str,
        instance_type: str,
    ):
        # Create an EC2 instance for the bastion host
        kafka_bastion_host_instance = ec2.Instance(
            self,
            cluster_id + "BastionHostInstance",
            vpc=vpc,
            instance_type=ec2.InstanceType(instance_type),
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_group=kafka_bastion_host_security_group,
            machine_image=ec2.MachineImage.latest_amazon_linux2(),
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda",
                    volume=ec2.BlockDeviceVolume.ebs(8, encrypted=True)
                )
            ]
        )

        # Create a CloudFormation output to export the bastion host instance ID
        output = CfnOutput(
            self,
            "bastionoutput",
            value=kafka_bastion_host_instance.instance_id,
            description="Bastion host EC2 Instance ID",
            export_name=cluster_id+ "BastionHostEc2ID",
        )

        # Configure the user data for the bastion host instance
        kafka_bastion_host_instance.add_user_data(
            "yum update -y",
            "yum install -y java-11-amazon-corretto-headless",  # install a trusted JRE
            "cd /home/ec2-user/",
            "wget https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip",  # upgrade to AWS CLI v2 to get bootstrap information
            "wget https://github.com/aws/aws-msk-iam-auth/releases/download/v1.1.3/aws-msk-iam-auth-1.1.3-all.jar",  # download the IAM authenticator
            "wget https://archive.apache.org/dist/kafka/2.6.3/kafka_2.13-2.6.3.tgz",  # download the Kafka client
            "unzip awscli-exe-linux-x86_64.zip",
            "tar -xvf kafka_2.13-2.6.3.tgz",
            "./aws/install",
            "PATH=/usr/local/bin:$PATH",
            "source ~/.bash_profile",
            f'echo "TLS=$(aws kafka describe-cluster --cluster-arn {kafka_cluster_arn} --query "ClusterInfo.ZookeeperConnectString" --region {region})" >> /etc/environment',
            f'echo "ZK=$(aws kafka get-bootstrap-brokers --cluster-arn {kafka_cluster_arn} --query "BootstrapBrokerStringSaslIam" --region {region})" >> /etc/environment',
            'echo "CLASSPATH=/home/ec2-user/aws-msk-iam-auth-1.1.3-all.jar" >> /etc/environment',
            "cd kafka_2.13-2.6.3/bin/",
            'echo "security.protocol=SASL_SSL" >> client.properties',
            'echo "sasl.mechanism=AWS_MSK_IAM" >> client.properties'
        )

        # Define IAM policy statements for accessing Kafka
        access_kafka_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "kafka:ListClusters",
                "kafka:GetBootstrapBrokers",
                "kafka:DescribeCluster",
                "kafka-cluster:Connect",
                "kafka-cluster:AlterCluster",
            ],
            resources=[kafka_cluster_arn],
        )

        admin_kafka_topics = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "kafka-cluster:WriteData",
                "kafka-cluster:ReadData",
                "kafka-cluster:*Topic*",
            ],
            resources=[
                get_topic_name(
                    kafka_cluster_arn=kafka_cluster_arn, topic_name="*"
                )
            ],
        )

        access_to_user_groups = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["kafka-cluster:AlterGroup", "kafka-cluster:DescribeGroup"],
            resources=[
                get_group_name(kafka_cluster_arn=kafka_cluster_arn, group_name="*")
            ],
        )

        # Add the required managed policies and IAM policy statements to the bastion host instance
        kafka_bastion_host_instance.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")
        )
        kafka_bastion_host_instance.add_to_role_policy(access_kafka_policy)
        kafka_bastion_host_instance.add_to_role_policy(admin_kafka_topics)
        kafka_bastion_host_instance.add_to_role_policy(access_to_user_groups)

        # Allow the bastion host to access the Kafka cluster
        self.allow_bastion_host_to_access_kafka(
            kafka_cluster_security_group, kafka_bastion_host_security_group
        )
        return kafka_bastion_host_instance

    # Initialize the security group for the Kafka bastion host
    def init_kafka_bastion_host_security_group(self, vpc: ec2.IVpc, cluster_id:str):
        kafka_bastion_host_sg = ec2.SecurityGroup(
            self,
            cluster_id + "BastionHostSecurityGroup",
            vpc=vpc,
            description="kafka bastion host security group"
        )
        return kafka_bastion_host_sg

    # Allow traffic from bastion host to Kafka
    def allow_bastion_host_to_access_kafka(
        self, kafka_sg: ec2.ISecurityGroup, bastion_host_sg: ec2.ISecurityGroup
    ):
        kafka_sg.connections.allow_from(other=bastion_host_sg.connections, port_range=ec2.Port.tcp(9098))  
        return None
