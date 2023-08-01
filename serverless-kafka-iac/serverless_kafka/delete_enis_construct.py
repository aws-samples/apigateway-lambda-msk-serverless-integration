"""
This script is part of a CDK application and it defines a construct for AWS CDK which creates a Lambda function 
for deleting Elastic Network Interfaces (ENIs) associated with a given security group. 
It also sets up the necessary IAM role with appropriate permissions for this Lambda function to operate. 
The Lambda function is triggered when the CDK stack is destroyed, effectively cleaning up resources that would 
otherwise linger after stack deletion. The implementation of the Lambda function itself is in a 
separate file called delete_enis_lambda.py in the path 'serverless_kafka/delete_enis_lambda/'.
For more informaation on the general requirement that makes this necessary read:
https://stackoverflow.com/questions/41299662/aws-lambda-created-eni-not-deleting-while-deletion-of-stack
"""

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from aws_cdk import (
    Duration, CustomResource,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_cloudformation as cfn,
    custom_resources as cr,
    aws_logs as logs,
)
from constructs import Construct
class DeleteENIsConstruct(Construct):

    def __init__(self, scope: Construct, id: str, security_group_id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        # Create the IAM role for Lambda function


        delete_enis_role = iam.Role(scope=self, 
                                      id=security_group_id + "ENICleanUpRole",
                                      assumed_by =iam.ServicePrincipal('lambda.amazonaws.com'),
                                      role_name=security_group_id + "ENICleanupFunctionRole",
                                    )
        
        delete_enis_role.add_to_policy(iam.PolicyStatement(
            actions=[
                'logs:CreateLogGroup',
                'logs:CreateLogStream',
                'logs:PutLogEvents',
            ],
            resources=['arn:aws:logs:*:*:*']
        ))


        delete_enis_role.add_to_policy(iam.PolicyStatement(
            actions=[
                'ec2:DescribeNetworkInterfaces',
                'ec2:DeleteNetworkInterface',
            ],
            resources=['*']
        ))

        # Create the Lambda function
        delete_enis_lambda = _lambda.SingletonFunction(self, security_group_id + 'DeleteENIsLambda',
            uuid=security_group_id + "ENICleanUp",
            function_name=security_group_id + "ENICleanupFunction",
            code=_lambda.AssetCode('serverless_kafka/delete_enis_lambda/'), 
            handler="delete_enis_lambda.handler",
            description="This Lambda function will delete all ENIs associated with the security group provided, when the stack is destroyed.",
            timeout=Duration.seconds(300),
            runtime=_lambda.Runtime.PYTHON_3_11,
            role=delete_enis_role,
            environment={
                'SECURITY_GROUP_ID': security_group_id,
            }
        )
        
        my_provider = cr.Provider(self, security_group_id + "ENICleanupCustomResourceProvider",
            on_event_handler=delete_enis_lambda,
            provider_function_name=security_group_id + "ENICleanupCustomResourceProvider",
            )
        
        CustomResource(self, "KafkaENICleanupFunctionCustomResource", service_token=my_provider.service_token)