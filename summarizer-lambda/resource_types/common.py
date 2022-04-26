from collections import OrderedDict
from dataclasses import dataclass, field


@dataclass
class StackSummary:
    """A summary with rendered-html for a single stack."""
    html: str
    name: str


@dataclass
class StackResourceSummary:
    """An single resource of a CFN stack."""
    physical_id: str
    logical_id: str
    aws_region: str
    links: OrderedDict = field(default_factory=OrderedDict)
    label: str = None
    href: str = None

    def set_resource_link(self, label: str, href: str):
        self.label = label
        self.href = href

    def add_link(self, label: str, href: str):
        self.links[label] = {"label": label, "href": href}
