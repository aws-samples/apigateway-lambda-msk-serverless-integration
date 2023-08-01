# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from cdk_nag import NagPackSuppression, NagSuppressions
from aws_cdk.aws_lambda import Function
from constructs import IConstruct


def add_resource_suppressions(cdk_node:IConstruct, list_of_supression_tuples):
    NagSuppressions.add_resource_suppressions(
        cdk_node,
        [NagPackSuppression(id=e[0], reason=e[1]) for e in list_of_supression_tuples],
        apply_to_children=True,
    )


def add_resource_suppressions_to_function(cdk_node:Function, list_of_supression_tuples):
    NagSuppressions.add_resource_suppressions(
        cdk_node,
        [NagPackSuppression(id=e[0], reason=e[1]) for e in list_of_supression_tuples],
        apply_to_children=True,
    )