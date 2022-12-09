#!/usr/bin/env python3
import os

from aws_cdk import App, Environment

from deployment.deployment_stack import CloudFormationSummarizerStack

app = App()
CloudFormationSummarizerStack(app, "CloudFormationSummarizer", env=Environment(
    account=os.getenv('CDK_DEFAULT_ACCOUNT'),
    region=os.getenv('CDK_DEFAULT_REGION')
))
app.synth()
