"""base_node_test module."""

import dataclasses

from ml_croissant._src.structure_graph import base_node
from ml_croissant._src.tests.nodes import create_test_node


def test_there_exists_at_least_one_property():
    @dataclasses.dataclass
    class Node(base_node.Node):
        property1: str = ""
        property2: str = ""

        def check(self):
            pass

    node = create_test_node(
        Node,
        property1="property1",
        property2="property2",
    )
    assert base_node.there_exists_at_least_one_property(
        node, ["property0", "property1"]
    )
    assert not base_node.there_exists_at_least_one_property(node, [])
    assert not base_node.there_exists_at_least_one_property(node, ["property0"])
