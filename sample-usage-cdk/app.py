import os

from aws_cdk import App, Environment

from sample_usage_cdk.sample_usage_cdk_stack import SampleUsageCdkStack

app = App()
SampleUsageCdkStack(app, "SampleUsageCdkStack", env=Environment(
    account=os.getenv('CDK_DEFAULT_ACCOUNT'),
    region=os.getenv('CDK_DEFAULT_REGION')
))
app.synth()
