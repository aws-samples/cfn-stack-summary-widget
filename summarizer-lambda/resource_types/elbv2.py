from resource_types.common import StackResourceSummary


def enrich_load_balancer_summary(resource: StackResourceSummary) -> dict:
    arn_parts = resource.physical_id.split(':')[-1].split('/')
    load_balancer_type, name, id = arn_parts[1:4]
    variables = {
        "name": name,
        "load_balancer_type": load_balancer_type,
        "cloudwatch_id": '*2f'.join((load_balancer_type, name, id))
    }
    return variables
