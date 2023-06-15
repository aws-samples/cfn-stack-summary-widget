from pathlib import Path

from aws_cdk import (BundlingOptions, DockerImage, Duration, Environment,
                     Stack, aws_iam)
from aws_cdk import aws_s3_assets as assets
from aws_cdk import aws_sns, aws_sqs
from aws_cdk.aws_lambda import Code, Function, Runtime
from aws_cdk.aws_logs import RetentionDays
from aws_cdk.aws_sns_subscriptions import SqsSubscription
from constructs import Construct

VISIBILITY_TIMEOUT = Duration.seconds(120)


class CloudFormationSummarizerStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, env: Environment) -> None:
        super().__init__(scope, construct_id, env=env)

        topic = aws_sns.Topic(self, "CFNNotifications")
        queue = aws_sqs.Queue(self, "CFNNotificationQueue", visibility_timeout=VISIBILITY_TIMEOUT)

        code = assets.Asset(self, "SummarizerFunctionCode",
                            bundling=BundlingOptions(
                                image=DockerImage.from_build(
                                    path=Path.cwd().joinpath("../summarizer-lambda").as_posix()
                                ),
                                user="root",
                                command=["cp", "/root/lambda.zip", "/asset-output"]
                            ),
                            path=Path.cwd().joinpath("../summarizer-lambda").as_posix()
                            )

        function = Function(self, "SummarizerFunction",
                            code=Code.from_bucket(code.bucket, code.s3_object_key),
                            function_name="CloudFormationStackSummarizer",
                            handler="lambda_src.handler",
                            runtime=Runtime.PYTHON_3_10,
                            timeout=VISIBILITY_TIMEOUT,
                            log_retention=RetentionDays.TWO_WEEKS
                            )
        function.role.add_to_policy(aws_iam.PolicyStatement(
            actions=[
                "cloudformation:DescribeStacks",
                "cloudformation:ListStacks",
                "cloudformation:ListStackResources",
            ],
            resources=["*"]
        ))
        queue.grant_consume_messages(function.role)
        topic.add_subscription(SqsSubscription(queue))
        function.add_event_source_mapping("QueueSubscription", event_source_arn=queue.queue_arn)
