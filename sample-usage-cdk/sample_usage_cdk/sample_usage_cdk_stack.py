import json

from aws_cdk import Aws, CfnOutput, Stack
from aws_cdk.aws_cloudwatch import CfnDashboard
from constructs import Construct


class SampleUsageCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        summarizer_lambda_name = "CloudFormationStackSummarizer"
        dashboard_body = {
            "widgets": [
                {
                    "height": 9,
                    "width": 9,
                    "type": "custom",
                    "x": 0,
                    "y": 0,
                    "properties": {
                        "endpoint": f"arn:{Aws.PARTITION}:lambda:{Aws.REGION}:{Aws.ACCOUNT_ID}:function:{summarizer_lambda_name}",
                        "title": "CloudFormation Resources",
                        "params": {
                            "stacks": [
                                "CloudFormationSummarizer"
                            ]
                        }
                    }
                },
                {
                    "type": "log",
                    "x": 9,
                    "y": 0,
                    "width": 15,
                    "height": 9,
                    "properties": {
                        "query": f"SOURCE '/aws/lambda/{summarizer_lambda_name}' | fields @timestamp, @message\n| sort @timestamp desc\n| limit 20",
                        "region": Aws.REGION,
                        "stacked": False,
                        "view": "table"
                    }
                }
            ]
        }

        dashboard = CfnDashboard(self, "Dashboard", dashboard_body=json.dumps(dashboard_body))

        CfnOutput(self, "DashboardUrl",
                  value=f"https://{Aws.REGION}.console.aws.amazon.com/cloudwatch/home?region={Aws.REGION}#dashboards:name={dashboard.ref}"
                  )
