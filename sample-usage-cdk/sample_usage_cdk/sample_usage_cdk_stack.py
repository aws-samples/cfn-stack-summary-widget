import json

from aws_cdk import core as cdk
from aws_cdk.aws_cloudwatch import CfnDashboard


class SampleUsageCdkStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
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
                        "endpoint": f"arn:{cdk.Aws.PARTITION}:lambda:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:function:{summarizer_lambda_name}",
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
                        "region": cdk.Aws.REGION,
                        "stacked": False,
                        "view": "table"
                    }
                }
            ]
        }

        dashboard = CfnDashboard(self, "Dashboard", dashboard_body=json.dumps(dashboard_body))

        cdk.CfnOutput(self, "DashboardUrl",
                      value=f"https://{cdk.Aws.REGION}.console.aws.amazon.com/cloudwatch/home?region={cdk.Aws.REGION}#dashboards:name={dashboard.ref}"
                      )
