# Importing required libraries and modules
import logging as log
import os
from pathlib import Path

from aws_cdk import (BundlingOptions, BundlingOutput, DockerVolume, Duration,
                     Stack, CfnOutput)
from aws_cdk import aws_apigateway as apig
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_xray as xray
from constructs import Construct

from .helpers import get_group_name, get_topic_name, add_permissions_to_role_policy, map_string_to_retention_days, add_permissions_to_policy

# Setting the basic configuration for logging
log.basicConfig(level=log.INFO)


class ServerlessKafkaProducerStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        app_config_id:str , 
        stack_config_id: str, 
        kafka_vpc: ec2.IVpc,
        kafka_security_group: ec2.ISecurityGroup,
        kafka_bootstrap_server: str,
        msk_arn: str,
        **kwargs,
    ) -> None:
        # Initializing the parent class
        super().__init__(scope, construct_id, **kwargs)

        # Get the configuration for the stack from the context
        app_config = self.node.try_get_context(app_config_id) or {}
        serverless_kafka_producer_config = self.node.try_get_context(stack_config_id) or {}
        

        # Setting up a tag for the stack
        self.tags.set_tag("app", app_config.get('application_tag', "ServerlessKafka"))
        # Setting up a tag for the stack
        self.tags.set_tag("stack", serverless_kafka_producer_config.get("stack_tag", "ServerlessKafkaProducerStack"))

        # Get the topic name from the stack config
        topic_name = serverless_kafka_producer_config.get("topic_name", "ServerlessKafkaTopic")

        # Initializing proxy lambda function
        function = self.init_proxy_lambda(
            vpc=kafka_vpc,
            kafka_security_group=kafka_security_group,
            bootstrap_broker=kafka_bootstrap_server,
            msk_arn=msk_arn,
            topic_name=topic_name,
            app_config=app_config,
            serverless_kafka_producer_config=serverless_kafka_producer_config
        )

        # Initializing the API Gateway
        self.init_api_gateway(function, kafka_vpc, kafka_security_group, serverless_kafka_producer_config )  # type: ignore



    # Function to create API Gateway endpoint
    def init_api_gateway(
        self,
        _function: _lambda.IFunction,
        vpc: ec2.IVpc,
        kafka_security_group: ec2.ISecurityGroup,
        serverless_kafka_producer_config
    ):

        # Creating the REST API
        rest_api = apig.RestApi(
            self,
            serverless_kafka_producer_config.get("apigateway_api_id", "ProducerAPI"),
            rest_api_name=serverless_kafka_producer_config.get("apigateway_rest_api_name", "ServerlessKafkaProducerAPI"),
            cloud_watch_role=False,
            deploy_options=apig.StageOptions(
                logging_level=apig.MethodLoggingLevel.INFO if serverless_kafka_producer_config.get("apigateway_method_log_level", 'INFO') == "INFO" else apig.MethodLoggingLevel.ERROR if serverless_kafka_producer_config.get("apigateway_rest_api_name", 'INFO') == "ERROR" else apig.MethodLoggingLevel.OFF,
                data_trace_enabled=True if serverless_kafka_producer_config.get("apigateway_data_trace_enabled", "yes") == "yes" else False,
                tracing_enabled=True if serverless_kafka_producer_config.get("apigateway_tracing_enabled", "yes") == "yes" else False,
                cache_data_encrypted=True if serverless_kafka_producer_config.get("apigateway_cache_data_encrypted", "yes") == "yes" else False,
                metrics_enabled=True if serverless_kafka_producer_config.get("apigateway_metrics_enabled", "yes") == "yes" else False,
                access_log_destination=apig.LogGroupLogDestination(
                        logs.LogGroup(self, "AccessLogs", retention=logs.RetentionDays.ONE_WEEK)
                    ),
                access_log_format=apig.AccessLogFormat.clf(),
                
            ),
            default_method_options=apig.MethodOptions(
                authorization_type=apig.AuthorizationType.IAM 
            ),
        )
        # Define a resource
        resource = rest_api.root.add_resource(serverless_kafka_producer_config.get("apigateway_api_id", "ProducerAPI") + "Resource")

        # Define request model for validation
        request_model = apig.Model(self, serverless_kafka_producer_config.get("apigateway_api_id", "ProducerAPI") + "RequestModel",
                                         rest_api=rest_api,
                                         content_type="application/json",
                                         schema=apig.JsonSchema(
                                             type=apig.JsonSchemaType.OBJECT,
                                             properties={
                                                 "payload": apig.JsonSchema(
                                                     type=apig.JsonSchemaType.STRING
                                                 )
                                             },
                                             required=["payload"]
                                        
                                         ))

        # Define request parameters validation
        request_validator = apig.RequestValidator(self, serverless_kafka_producer_config.get("apigateway_api_id", "ProducerAPI") + "RequestValidator",
                                                        rest_api=rest_api,
                                                        validate_request_parameters=True,
                                                        validate_request_body=True,)


        # Define a method on the resource with request validation
        method = resource.add_method(serverless_kafka_producer_config.get("apigateway_api_method","POST"), 
                            apig.LambdaIntegration(_function, request_templates={"application/json": '{"statusCode": 200}'}),
                            request_validator=request_validator,
                            request_models={"application/json": request_model})
        


        rest_full_path_output = CfnOutput(scope=self, id="ProducerAPIOutputResourcePath", value=resource.path )
        rest_method_output = CfnOutput(scope=self, id="ProducerAPIOutputAPIMethod", value=method.http_method )


    # Function to create the producer lambda and all necessary settings and authentications
    def init_proxy_lambda(
        self,
        vpc: ec2.IVpc,
        kafka_security_group: ec2.ISecurityGroup,
        bootstrap_broker: str,
        msk_arn: str,
        topic_name: str,
        app_config,
        serverless_kafka_producer_config
    ):
        
        # Create base policy to use for the Lambda function
        kafka_producer_policy = iam.ManagedPolicy(self, 
                                                serverless_kafka_producer_config.get("function_id", "ProducerLambda") + "Policy",
                                                managed_policy_name=serverless_kafka_producer_config.get("function_name", "ServerlessKafkaProducer") + "Policy",
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
        # Create base role to use for the Lambda function
        kafka_producer_role = iam.Role(scope=self, 
                                      id=serverless_kafka_producer_config.get("function_id", "ProducerLambda") + "Role",
                                      assumed_by =iam.ServicePrincipal('lambda.amazonaws.com'),
                                      role_name=serverless_kafka_producer_config.get("function_name", "ServerlessKafkaProducer") + "Role",
                                      managed_policies=[kafka_producer_policy]
                                    )
        
        
        # Create base role to use for the Lambda function that performs log retention
        kafka_producer_log_retention_role = iam.Role(scope=self, 
                                      id=serverless_kafka_producer_config.get("function_id", "ProducerLambda") + "LogRetentionRole",
                                      assumed_by =iam.ServicePrincipal('lambda.amazonaws.com'),
                                      role_name=serverless_kafka_producer_config.get("function_name", "ServerlessKafkaProducer") + "LogRetentionRole",
                                      managed_policies=[kafka_producer_policy]
                                    )

        # Add policies to log retention role 
        add_permissions_to_policy(role=kafka_producer_log_retention_role, permissions= {
                "logs:PutRetentionPolicy": ["arn:aws:logs:*:*:*"] ,
                "logs:DeleteRetentionPolicy": ["arn:aws:logs:*:*:*"]
        })

        # Define the AWS Lambda function
        kafka_producer_lambda = _lambda.Function(
            self,
            serverless_kafka_producer_config.get("function_id", "ProducerLambda"),
            function_name=serverless_kafka_producer_config.get("function_name", "ServerlessKafkaProducer"),
            runtime=_lambda.Runtime.JAVA_17,
            handler="software.amazon.samples.kafka.lambda.SimpleApiGatewayKafkaProxy::handleRequest",
            timeout=Duration.seconds(serverless_kafka_producer_config.get("function_timeout_seconds", 150)),
            log_retention=map_string_to_retention_days(serverless_kafka_producer_config.get("function_log_retention_enum", "ONE_DAY")),
            code=self.build_mvn_package(),
            tracing=_lambda.Tracing.ACTIVE if serverless_kafka_producer_config.get("function_tracing_enabled", "yes") else _lambda.Tracing.DISABLED,
            
            role=kafka_producer_role,
            log_retention_role=kafka_producer_log_retention_role,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[kafka_security_group],
            reserved_concurrent_executions=serverless_kafka_producer_config.get("function_max_concurrency", 60),
            environment={
                "BOOTSTRAP_SERVER": str(bootstrap_broker),
                "TOPIC_NAME": topic_name,
                "JAVA_TOOL_OPTIONS": serverless_kafka_producer_config.get("function_java_tool_options", "-XX:+TieredCompilation -XX:TieredStopAtLevel=1 -DLOG_LEVEL=INFO"),
                "POWERTOOLS_LOG_LEVEL": serverless_kafka_producer_config.get("function_powertools_log_level", "INFO"),
                "POWERTOOLS_METRICS_NAMESPACE": app_config.get('application_tag', "ServerlessKafka"),                
                "POWERTOOLS_SERVICE_NAME": serverless_kafka_producer_config.get("function_powertools_service_name", "ServerlessKafkaProducer")
            },
            memory_size=serverless_kafka_producer_config.get("function_memory_size", 256)
        )
        # Configuring SnapStart properties
        snap_start_property = _lambda.CfnFunction.SnapStartProperty(
            apply_on="PublishedVersions"
        )
        l1_function:_lambda.CfnFunction = kafka_producer_lambda.node.default_child
        l1_function.snap_start = snap_start_property



                # Define an X-Ray Sampling Rule
        # xray.CfnSamplingRule(self, id=serverless_kafka_producer_config.get("function_id", "ProducerLambda") + "XRaySamplingRule",
        #     rule_name=serverless_kafka_producer_config.get("function_id", "ProducerLambda") + "XRay",
        #     sampling_rule=xray.CfnSamplingRule.SamplingRuleProperty(
        #         resource_arn="*",  #kafka_producer_lambda.function_arn,
        #         priority=10,
        #         fixed_rate=0.05,  
        #         reservoir_size=50,
        #         service_type="*",
        #         service_name="*",
        #         host="*",
        #         http_method="*",
        #         url_path="*",
        #         version=1,
        #     )
        # )


        # Defining the permissions for the Lambda function
        permissions = {
            "kafka-cluster:Connect": [msk_arn],
            "kafka-cluster:DescribeCluster": [msk_arn],
            "kafka-cluster:DescribeClusterDynamicConfiguration": [msk_arn],
            "kafka-cluster:DescribeGroup": [get_group_name(msk_arn, '*')],
            "kafka-cluster:DescribeTopic": [get_topic_name(msk_arn, topic_name)],
            "kafka-cluster:DescribeTopicDynamicConfiguration": [get_topic_name(msk_arn, topic_name)],
            "kafka-cluster:ReadData": [get_topic_name(msk_arn, topic_name)],
            "kafka-cluster:WriteData": [get_topic_name(msk_arn, topic_name)],
            "kafka-cluster:WriteDataIdempotently": [msk_arn]
        }

        # Adding permissions to role policy
        add_permissions_to_role_policy(permissions=permissions,object=kafka_producer_lambda)

        return kafka_producer_lambda

    # Function to build the Maven package
    def build_mvn_package(self):
        

        # Defining the Maven home directory
        home = str(Path.home())
        m2_home = os.path.join(home, ".m2/")
        log.info(f"Building Java Project ServerlessKafkaProducer using M2 home from directory: {m2_home}")

        # Building the code
        code = _lambda.Code.from_asset(
            path=os.path.join("..", "api-gateway-lambda-proxy"),
            bundling=BundlingOptions(
                image=_lambda.Runtime.JAVA_17.bundling_image,
                command=[
                    "/bin/sh",
                    "-c",
                    "mvn clean install -q -Dmaven.test.skip=true && cp /asset-input/target/ApiGatewayLambdaProxy.zip /asset-output/",
                ],
                user="root",
                output_type=BundlingOutput.ARCHIVED,
                volumes=[DockerVolume(host_path=m2_home, container_path="/root/.m2/")],
            ),
        )
        return code



   