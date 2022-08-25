import datetime
import json
import logging
import os
import pathlib
import sys
import traceback
import urllib.parse
from collections import defaultdict
from typing import List, Mapping, Optional

import boto3
import botocore.exceptions
import jinja2

from resource_types import ecs, elbv2, sqs
from resource_types.common import StackResourceSummary, StackSummary


def render_cloudwatch_logs_url(aws_region: str, log_group: str, log_stream: Optional[str] = None):
    """Returns a url to a cloudwatch logs stream."""
    log_group = urllib.parse.quote_plus(urllib.parse.quote_plus(log_group)).replace('%', '$')
    url = f"https://console.aws.amazon.com/cloudwatch/home?region={aws_region}#logsV2:log-groups/log-group/{log_group}"
    if log_stream:
        log_stream = urllib.parse.quote_plus(urllib.parse.quote_plus(log_stream)).replace('%', '$')
        url += f"/log-events/{log_stream}"
    return url


TEMPLATES = {
    "AWS::Route53::HostedZone": {
        "label": "{{ physical_id }}",
        "resource_link": "https://us-east-1.console.aws.amazon.com/route53/v2/hostedzones#ListRecordSets/{{ physical_id }}",
        "links": {
            "Query Metrics": "https://{{ region }}.console.aws.amazon.com/cloudwatch/home?region={{ region }}#metricsV2:graph=~(metrics~(~(~'AWS*2fRoute53~'DNSQueries~'HostedZoneId~'{{ physical_id }}~(region~'us-east-1)))~view~'timeSeries~stacked~false~region~'{{ region }}~stat~'Sum~period~300);query=~'*7bAWS*2fRoute53*2cHostedZoneId*7d;region=us-east-1;forwardXA=no"
        },
    },
    "AWS::CloudFront::Distribution": {
        "label": "{{ physical_id }}",
        "resource_link": "https://console.aws.amazon.com/cloudfront/v3/home#/distributions/{{ physical_id }}",
        "links": {
            "Metrics": "https://console.aws.amazon.com/cloudfront/v3/home#/monitoring/distribution/{{ physical_id }}"
        },
    },
    "AWS::S3::Bucket": {
        "label": "{{ physical_id }}",
        "resource_link": "https://us-east-1.console.aws.amazon.com/s3/buckets/{{ physical_id }}?region={{ region }}&tab=objects",
        "links": {
            "Metrics": "https://us-east-1.console.aws.amazon.com/s3/buckets/{{ physical_id }}?region={{ region }}&tab=metrics"
        },
    },
    "AWS::CloudWatch::Alarm": {
        "label": "{{ physical_id }}",
        "resource_link": "https://console.aws.amazon.com/cloudwatch/home?region={{ region }}#alarmsV2:alarm/{{ physical_id }}",
        "links": {},
    },
    "AWS::ElasticLoadBalancingV2::LoadBalancer": {
        "label": "{{ load_balancer_type }}: {{ physical_id }}",
        "resource_link": "https://console.aws.amazon.com/ec2/v2/home?region={{ region }}#LoadBalancers:search={{ name }};sort=loadBalancerName",
        "links": {
            "CloudWatch Metrics": "https://console.aws.amazon.com/cloudwatch/home?region={{ region }}#metricsV2:graph=~(view~'timeSeries~stacked~false~region~'{{ region }}~start~'-PT1H~end~'P0D);query=~'*7bAWS*2fApplicationELB*2cLoadBalancer*7d*20LoadBalancer*3d*22{{ cloudwatch_id }}*22"
        },
        "enrichers": [
            elbv2.enrich_load_balancer_summary
        ]
    },
    "AWS::Kinesis::Stream": {
        "label": "{{ physical_id }}",
        "resource_link": "https://console.aws.amazon.com/kinesis/home?region={{ region }}#/streams/details/{{ physical_id }}/details",
        "links": {
            "Metrics": "https://console.aws.amazon.com/kinesis/home?region={{ region }}#/streams/details/{{ physical_id }}/monitoring"
        }
    },
    "AWS::Logs::LogGroup": {
        "label": "{{ physical_id }}",
        "resource_link": "https://console.aws.amazon.com/cloudwatch/home?region={{ region }}#logsV2:log-groups/log-group/{{ physical_id }}",
        "links": {
            "Logs Insights": "https://console.aws.amazon.com/cloudwatch/home?region={{ region }}#logsV2:logs-insights$3FqueryDetail$3D~(end~0~start~-3600~timeType~'RELATIVE~unit~'seconds~editorString~'~isLiveTail~false~queryId~'~source~(~'{{ physical_id }}))",
        }
    },
    "AWS::SQS::Queue": {
        "label": "{{ queue_path }}",
        "resource_link": "https://console.aws.amazon.com/sqs/v2/home?region={{ region }}#/queues/{{ encoded_url }}",
        "links": {},
        "enrichers": [
            sqs.enrich_sqs_queue
        ]
    },
    "AWS::DynamoDB::Table": {
        "label": "{{ physical_id }}",
        "resource_link": "https://console.aws.amazon.com/dynamodb/home?region={{ region }}#tables:selected={{ physical_id }};tab=overview",
        "links": {
            "Metrics": "https://console.aws.amazon.com/dynamodb/home?region={{ region }}#tables:selected={{ physical_id }};tab=metrics"
        },
    },
    "AWS::Lambda::Function": {
        "label": "{{ physical_id }}",
        "resource_link": "https://console.aws.amazon.com/lambda/home?region={{ region }}#functions/{{ physical_id }}",
        "links": {
            "Logs Insights": "https://console.aws.amazon.com/cloudwatch/home?region={{ region }}#logsV2:logs-insights$3FqueryDetail$3D$257E$2528end$257E0$257Estart$257E-3600$257EtimeType$257E$2527RELATIVE$257Eunit$257E$2527seconds$257EeditorString$257E$2527fields*20*40timestamp*2c*20*40message*0a*7c*20sort*20*40timestamp*20desc*0a*7c*20limit*2020$257EisLiveTail$257Efalse$257EqueryId$257E$2527d2ee3780-2d3d-42c6-98cf-e483b2f3f85f$257Esource$257E$2528$257E$2527*2faws*2flambda*2f{{ physical_id }}$2529$2529",
            "Monitoring": "https://console.aws.amazon.com/lambda/home?region={{ region }}#/functions/{{ physical_id }}?tab=monitoring",
        },
    },
    "AWS::ECS::TaskDefinition": {
        "label": "{{ name }}:{{ version }}",
        "resource_link": "https://console.aws.amazon.com/ecs/home?region={{ region }}#/taskDefinitions/{{ name }}/{{ version }}",
        "links": {},
        "enrichers": [
            ecs.enrich_task_definition
        ]
    },
    "AWS::ECS::Service": {
        "label": "{{ service_name }}",
        "resource_link": "{{ base_url }}/details",
        "links": {
            "Events": "{{ base_url }}/events",
            "Metrics": "{{ base_url }}/metrics",
            "Logs": "{{ base_url }}/logs",
        },
        "enrichers": [
            ecs.enrich_task_definition
        ]
    }
}

TAG_GROUP = "StackSummarizer_Group"
TAG_NAME = "StackSummarizer_Name"

EVENT_TYPE_SUMMARIZE = "update"
EVENT_TYPE_DESCRIBE = "describe"


def render_template(template_source: str, template_vars: dict, template_type: str, resource_id: str):
    try:
        return jinja2.Template(template_source).render(**template_vars)
    except jinja2.TemplateSyntaxError as error:
        logger.error(
            f"error rendering {template_type} for '{resource_id}': {error.message}\nTemplate Source:{error.source}")
    return ''


def populate_resource_summary(template: dict, resource: StackResourceSummary) -> None:
    template_vars = {
        "physical_id": resource.physical_id,
        "logical_id": resource.logical_id,
        "region": resource.aws_region
    }

    for enricher in template.get("enrichers", []):
        template_vars.update(enricher(resource))

    resource.set_resource_link(
        render_template(template["label"], template_vars, 'resource label', resource.logical_id),
        render_template(template["resource_link"], template_vars, 'resource link', resource.logical_id),
    )
    for label in template["links"]:
        resource.add_link(label, render_template(template["links"][label], template_vars, label, resource.logical_id))


def render_stack_summary(stack_name: str, cloudformation) -> StackSummary:
    """
    Return a StackSummary for stack given by `stack_name`
    """
    logger.info("[%s] preparing to update stack document", stack_name)
    try:
        cloudformation.describe_stacks(StackName=stack_name)
    except botocore.exceptions.ClientError as e:
        if 'does not exist' in str(e):
            logger.warning("[%s] stack could not be found", stack_name)
            return StackSummary(f"<p style=\"padding: 10; text-align: center\">no CloudFormation stack named '{stack_name}'</p>", stack_name)

    logger.info("[%s] looking up stack resources", stack_name)
    all_resources = get_stack_resources_by_type(cloudformation, stack_name)
    resource_count = sum(len(all_resources[i]) for i in all_resources)
    logger.info("[%s] resources in stack: %d", stack_name, resource_count)
    region_name = cloudformation.meta.region_name
    filtered_resources = summarize_resource(all_resources)
    filtered_resources_count = sum(len(filtered_resources[i]) for i in filtered_resources)
    logger.info("[%s] resources for document: %d", stack_name, filtered_resources_count)
    html = render_html_summary(filtered_resources, stack_name, region_name, resource_count, filtered_resources_count)
    return StackSummary(html, stack_name)


def render_html_summary(resources: Mapping[str, List[StackResourceSummary]], stack_name: str, aws_region: str, resource_count: int, displayed_resources: int):
    """Return a string w/ an HTML document about a CFN stack and its resources."""
    j2env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(pathlib.Path(__file__).parent),
        autoescape=jinja2.select_autoescape(default=True, default_for_string=True)
    )
    template = j2env.get_template("stack-fragment-table.j2")

    template_vars = {
        "resources": resources,
        "date": datetime.datetime.now(),
        "stack_name": stack_name,
        "resource_count": resource_count,
        "displayed_resources": displayed_resources,
        "stack_link": f"https://console.aws.amazon.com/cloudformation/home?region={aws_region}#/stacks?filteringStatus=active&filteringText={stack_name}&viewNested=true&hideStacks=false&stackId="
    }

    return template.render(**template_vars)


def summarize_resource(resources_by_type: Mapping[str, List[StackResourceSummary]]) -> Mapping[str, List[StackResourceSummary]]:
    """
    For each StackResourceSummary, call the summarizer function for resource type.
    """
    resources_with_links = {}
    for cfn_type in resources_by_type:
        if cfn_type not in TEMPLATES:
            continue
        resources = resources_by_type[cfn_type]
        template = TEMPLATES[cfn_type]
        [populate_resource_summary(template, r) for r in resources]
        if len(resources) > 0:
            resources_with_links[cfn_type] = resources
    return resources_with_links


def get_stack_resources_by_type(cloudformation, stack_name):
    """Return a list of StackResourceSummary grouped by CFN resource type."""
    paginator = cloudformation.get_paginator('list_stack_resources')
    response_iterator = paginator.paginate(StackName=stack_name)
    resources_by_type = defaultdict(list)
    for page in response_iterator:
        for resource in page["StackResourceSummaries"]:
            resources_by_type[resource["ResourceType"]].append(StackResourceSummary(
                physical_id=resource["PhysicalResourceId"],
                logical_id=resource["LogicalResourceId"],
                aws_region=cloudformation.meta.region_name
            ))
    return resources_by_type


def get_event_type(event):
    """
    Given a lambda event, return the type of event received.
    """
    if 'describe' in event:
        logger.info("detected EVENT_TYPE_DESCRIBE")
        return EVENT_TYPE_DESCRIBE
    elif 'stacks' in event:
        logger.info("detected EVENT_TYPE_SUMMARIZE")
        return EVENT_TYPE_SUMMARIZE


def render_documentation():
    """
    Return markdown help text (used by CloudWatch console)
    """
    logging.info("rendering markdown documentation for 'describe' event")
    documentation_path = pathlib.Path(__file__).parent.joinpath('documentation.md')
    with open(documentation_path, 'r') as docs_file:
        docs_markdown = docs_file.read()
    return docs_markdown


def render(event, cloudformation):
    """
    Return HTML for rendering a custom widget.
    """
    event_type = get_event_type(event)
    summaries: List[StackSummary] = []
    stack_names = []
    if event_type == EVENT_TYPE_SUMMARIZE:
        stack_names += event["stacks"]
    elif event_type == EVENT_TYPE_DESCRIBE:
        return render_documentation()
    else:
        raise RuntimeError("unknown event type")
    result = ''

    for stack_name in stack_names:
        stack_summary = render_stack_summary(
            stack_name,
            cloudformation=cloudformation
        )
        summaries.append(stack_summary)

    for summary in summaries:
        logger.info("creating summary for %s", summary.name)
        result += summary.html
    return result


DEBUG = 'true'

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """Lambda entry point."""
    boto_session = boto3.Session()
    cloudformation = boto_session.client("cloudformation")
    logging.info("event: %r", event)

    try:
        return render(event, cloudformation)
    except BaseException as e:
        logger.error("exception during render", exc_info=e)
        response = {"event": event, "error": traceback.format_exception(type(e), e, sys.exc_info()[2])}
        error_message = "Error rendering widget"
        if context:
            log_url = render_cloudwatch_logs_url(
                boto_session.region_name,
                context.log_group_name,
                context.log_stream_name)
            error_message = "Error rendering widget: see error information in CloudWatch log stream: %s" % log_url
            response['error_message'] = "Error rendering widget: see error information in CloudWatch log stream: %s" % log_url
            response['log_url'] = log_url

        if os.getenv('DEBUG') == 'true':
            return json.dumps(response)
        else:
            raise Exception(error_message)
