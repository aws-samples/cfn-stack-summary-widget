from resource_types.common import StackResourceSummary


def enrich_task_definition(resource: StackResourceSummary) -> dict:
    arn_parts = resource.physical_id.split(":", maxsplit=7)
    name = arn_parts[5].split('/')[-1]
    version = arn_parts[6]
    return {
        "name": name,
        "version": version
    }


def enrich_service(resource: StackResourceSummary) -> dict:
    arn_parts = resource.physical_id.split("/", maxsplit=3)
    service_name = arn_parts[-1]
    cluster_name = arn_parts[-2]
    base_url = f"https://console.aws.amazon.com/ecs/home?region={resource.aws_region}#/clusters/{cluster_name}/services/{service_name}"
    return {
        "service_name": service_name,
        "cluster_name": cluster_name,
        "base_url": base_url
    }
