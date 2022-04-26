import os

from aws_cdk import core as cdk

from sample_usage_cdk.sample_usage_cdk_stack import SampleUsageCdkStack

app = cdk.App()
SampleUsageCdkStack(app, "SampleUsageCdkStack", env=cdk.Environment(
    account=os.getenv('CDK_DEFAULT_ACCOUNT'),
    region=os.getenv('CDK_DEFAULT_REGION')
))
app.synth()
