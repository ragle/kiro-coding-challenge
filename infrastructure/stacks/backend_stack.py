from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
)
from constructs import Construct
import os


class BackendStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # DynamoDB Table
        events_table = dynamodb.Table(
            self,
            "EventsTable",
            partition_key=dynamodb.Attribute(
                name="eventId", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # For dev/testing only
        )

        # Lambda Function
        lambda_function = _lambda.Function(
            self,
            "EventsApiFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lambda_handler.handler",
            code=_lambda.Code.from_asset(
                os.path.join(os.path.dirname(__file__), "../../backend/package")
            ),
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "EVENTS_TABLE_NAME": events_table.table_name,
            },
        )

        # Grant Lambda permissions to access DynamoDB
        events_table.grant_read_write_data(lambda_function)

        # API Gateway
        api = apigw.LambdaRestApi(
            self,
            "EventsApi",
            handler=lambda_function,
            proxy=True,
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["*"],
            ),
        )

        # Outputs
        CfnOutput(
            self,
            "ApiUrl",
            value=api.url,
            description="API Gateway URL",
        )

        CfnOutput(
            self,
            "TableName",
            value=events_table.table_name,
            description="DynamoDB Table Name",
        )
