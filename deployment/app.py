#!/usr/bin/env python3
import os

from aws_cdk import core as cdk

from deployment.deployment_stack import CloudFormationSummarizerStack

app = cdk.App()
CloudFormationSummarizerStack(app, "CloudFormationSummarizer", env=cdk.Environment(
    account=os.getenv('CDK_DEFAULT_ACCOUNT'),
    region=os.getenv('CDK_DEFAULT_REGION')
))
app.synth()
