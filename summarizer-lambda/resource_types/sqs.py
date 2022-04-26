import urllib.parse

from resource_types.common import StackResourceSummary


def enrich_sqs_queue(resource: StackResourceSummary) -> dict:
    return {
        "queue_path": resource.physical_id.split('/')[-1],
        "encoded_url": urllib.parse.quote_plus(resource.physical_id)
    }
