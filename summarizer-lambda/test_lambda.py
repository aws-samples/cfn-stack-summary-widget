import datetime
from contextlib import contextmanager

from boto3.session import Session
from botocore import stub

import lambda_src
from resource_types.common import StackResourceSummary


@contextmanager
def stubbed_client(client_name):
    client = Session(region_name="us-east-1").client(client_name)
    stubber = stub.Stubber(client)

    with stubber:
        yield (client, stubber)
    stubber.assert_no_pending_responses()


def test_get_stack_resources_by_type():
    with stubbed_client("cloudformation") as (client, stubber):
        stubber.add_response("list_stack_resources", {"StackResourceSummaries": [
            {
                "ResourceType": "AWS::S3::Bucket",
                "PhysicalResourceId": "mybucket-1293847127232",
                "LogicalResourceId": "MyBucket",
                "LastUpdatedTimestamp": datetime.datetime.now(),
                "ResourceStatus": "CREATE_COMPLETE"
            },
            {
                "ResourceType": "AWS::S3::Bucket",
                "PhysicalResourceId": "mybucket-1293847127232",
                "LogicalResourceId": "MyBucket",
                "LastUpdatedTimestamp": datetime.datetime.now(),
                "ResourceStatus": "CREATE_COMPLETE"
            },
            {
                "ResourceType": "AWS::Lambda::Function",
                "PhysicalResourceId": "mybucket-1293847127232",
                "LogicalResourceId": "MyBucket",
                "LastUpdatedTimestamp": datetime.datetime.now(),
                "ResourceStatus": "CREATE_COMPLETE"
            }
        ]})
        resources = lambda_src.get_stack_resources_by_type(client, "MyStack")
    assert len(resources["AWS::S3::Bucket"]) == 2
    assert len(resources["AWS::Lambda::Function"]) == 1


def test_populate_resource_links():
    resource_a = lambda_src.StackResourceSummary("bucket-abc", "SomeBucket", "us-east-1")
    resource_b = lambda_src.StackResourceSummary("bucket-123", "OtherBucket", "us-east-1")
    lambda_src.summarize_resource({"AWS::S3::Bucket": [resource_a, resource_b]})
    assert resource_a.label == "bucket-abc"
    assert resource_b.label == "bucket-123"


def test_summarize_resource():
    r = StackResourceSummary("my-bucket", "MyBucket", "us-west-1")
    lambda_src.populate_resource_summary({
        "label": "{{ physical_id }}",
        "resource_link": "https://us-east-1.console.aws.amazon.com/s3/buckets/{{ physical_id }}?region={{ region }}&tab=objects",
        "links": {
            "Metrics": "https://us-east-1.console.aws.amazon.com/s3/buckets/{{ physical_id }}?region={{ region }}&tab=metrics"
        }
    }, r)
    assert r.label == "my-bucket"
    assert r.href == f"https://us-east-1.console.aws.amazon.com/s3/buckets/{r.physical_id}?region={r.aws_region}&tab=objects"
    assert r.links["Metrics"]["href"] == f"https://us-east-1.console.aws.amazon.com/s3/buckets/{r.physical_id}?region={r.aws_region}&tab=metrics"
