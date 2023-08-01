# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Importing necessary modules and classes
from aws_cdk import Arn as arn
from aws_cdk import ArnFormat as af
from aws_cdk import Fn as fn
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from constructs import Node

# This function retrieves the value of the given parameter from the context of the CDK application.
# If the parameter does not exist in the context, it returns the provided default value.
def get_parameter(node: Node, parameter_name: str, default_value=None):
    return_value = node.try_get_context(parameter_name)
    if return_value:
        return return_value
    else:
        return default_value

# This function constructs the ARN for a Kafka topic given the ARN of the Kafka cluster and the topic name.
def get_topic_name(kafka_cluster_arn: str, topic_name: str):
    _arn = arn.split(kafka_cluster_arn, af.SLASH_RESOURCE_SLASH_RESOURCE_NAME)
    cluster_name = _arn.resource
    cluster_uuid = _arn.resource_name
    prefix_arn = arn.split(kafka_cluster_arn, af.COLON_RESOURCE_NAME)
    arn_with_topic = fn.join(
        delimiter="",
        list_of_values=[
            "arn",
            ":",
            prefix_arn.partition,
            ":",
            prefix_arn.service,
            ":",
            prefix_arn.region,
            ":",
            prefix_arn.account,
            ":topic/",
            cluster_name,
            "/",
            cluster_uuid,
            "/",
            topic_name,
        ],  # type: ignore
    )
    return arn_with_topic

# This function constructs the ARN for a Kafka consumer group given the ARN of the Kafka cluster and the group name.
def get_group_name(kafka_cluster_arn: str, group_name: str):
    _arn = arn.split(kafka_cluster_arn, af.SLASH_RESOURCE_SLASH_RESOURCE_NAME)
    cluster_name = _arn.resource
    cluster_uuid = _arn.resource_name
    prefix_arn = arn.split(kafka_cluster_arn, af.COLON_RESOURCE_NAME)
    arn_with_group = fn.join(
        delimiter="",
        list_of_values=[
            "arn",
            ":",
            prefix_arn.partition,
            ":",
            prefix_arn.service,
            ":",
            prefix_arn.region,
            ":",
            prefix_arn.account,
            ":group/",
            cluster_name,
            "/",
            cluster_uuid,
            "/",
            group_name,
        ],  # type: ignore
    )
    return arn_with_group

# This function adds the provided set of permissions to the IAM role of the given object. 
# The permissions should be a dictionary where keys are action names and values are lists of resources.
# If no resources are specified for an action, the function allows the action for all resources.
def add_permissions_to_role_policy(object, permissions ):
    for action, resources in permissions.items():
        if not resources:  # If resources list is empty, allow action for all resources
            resources = ["*"]
        for resource in resources:
            object.add_to_role_policy(iam.PolicyStatement(
                actions=[action],
                resources=[resource],
                effect=iam.Effect.ALLOW
            ))

# This function adds the provided set of permissions to the IAM role in the given object. 
# The permissions should be a dictionary where keys are action names and values are lists of resources.
# If no resources are specified for an action, the function allows the action for all resources.
def add_permissions_to_policy( role:iam.Role, permissions  ):
    n = 0
    for action, resources in permissions.items():
        if not resources:  # If resources list is empty, allow action for all resources
            resources = ["*"]
        for resource in resources:

            role.add_to_policy(iam.PolicyStatement(
                actions=[action],
                resources=[resource],
                effect=iam.Effect.ALLOW
            ))

def map_string_to_retention_days(retention_str: str) -> logs.RetentionDays:
    retention_days_mapping = {
        "ONE_DAY": logs.RetentionDays.ONE_DAY,
        "THREE_DAYS": logs.RetentionDays.THREE_DAYS,
        "FIVE_DAYS": logs.RetentionDays.FIVE_DAYS,
        "ONE_WEEK": logs.RetentionDays.ONE_WEEK,
        "TWO_WEEKS": logs.RetentionDays.TWO_WEEKS,
        "ONE_MONTH": logs.RetentionDays.ONE_MONTH,
        "TWO_MONTHS": logs.RetentionDays.TWO_MONTHS,
        "THREE_MONTHS": logs.RetentionDays.THREE_MONTHS,
        "FOUR_MONTHS": logs.RetentionDays.FOUR_MONTHS,
        "FIVE_MONTHS": logs.RetentionDays.FIVE_MONTHS,
        "SIX_MONTHS": logs.RetentionDays.SIX_MONTHS,
        "ONE_YEAR": logs.RetentionDays.ONE_YEAR,
        "THIRTEEN_MONTHS": logs.RetentionDays.THIRTEEN_MONTHS,
        "EIGHTEEN_MONTHS": logs.RetentionDays.EIGHTEEN_MONTHS,
        "TWO_YEARS": logs.RetentionDays.TWO_YEARS,
        "FIVE_YEARS": logs.RetentionDays.FIVE_YEARS,
        "SIX_YEARS": logs.RetentionDays.SIX_YEARS,
        "SEVEN_YEARS": logs.RetentionDays.SEVEN_YEARS,
        "EIGHT_YEARS": logs.RetentionDays.EIGHT_YEARS,
        "NINE_YEARS": logs.RetentionDays.NINE_YEARS,
        "TEN_YEARS": logs.RetentionDays.TEN_YEARS,
        "INFINITE": logs.RetentionDays.INFINITE,
    }

    return retention_days_mapping.get(retention_str.upper(), "")