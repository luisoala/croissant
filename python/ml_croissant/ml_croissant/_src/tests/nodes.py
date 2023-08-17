"""Testing utils for `Node`."""

import functools
from typing import Any, Callable

from etils import epath
import networkx as nx

from ml_croissant._src.core.issues import Context
from ml_croissant._src.core.issues import Issues
from ml_croissant._src.structure_graph.base_node import Node
from ml_croissant._src.structure_graph.nodes.field import Field
from ml_croissant._src.structure_graph.nodes.file_object import FileObject
from ml_croissant._src.structure_graph.nodes.file_set import FileSet
from ml_croissant._src.structure_graph.nodes.record_set import RecordSet


class _EmptyNode(Node):
    def check(self):
        pass


def _node_params(**kwargs):
    params = {
        "issues": Issues(),
        "context": Context(),
        "graph": nx.MultiDiGraph(),
        "name": "node_name",
        "folder": epath.Path(),
        "parents": [],
    }
    for key, value in kwargs.items():
        params[key] = value
    return params


def create_test_node(cls: type[Any], **kwargs):
    """Utils to easily create new nodes in tests.

    Usage:

    Instead of writing:
    ```python
    node = FileSet(
        issues=...,
        graph=...,
        name=...,
        folder=...,
        parents=...,
        description="Description"
    )
    ```

    Use:
    ```python
    node = test_node(FileSet, description="Description")
    ```
    """
    return cls(**_node_params(**kwargs))


create_test_field: Callable[..., Field] = functools.partial(
    create_test_node, Field, name="field_name"
)
create_test_file_object: Callable[..., FileObject] = functools.partial(
    create_test_node, FileObject, name="file_object_name"
)
create_test_file_set: Callable[..., FileSet] = functools.partial(
    create_test_node, FileSet, name="file_set_name"
)
create_test_record_set: Callable[..., RecordSet] = functools.partial(
    create_test_node, RecordSet, name="record_set_name"
)


empty_field: Field = create_test_node(Field, name="field_name")
empty_file_object: FileObject = create_test_node(FileObject, name="file_object_name")
empty_file_set: FileSet = create_test_node(FileSet, name="file_set_name")
empty_node: Node = create_test_node(_EmptyNode)
empty_record_set: RecordSet = create_test_node(RecordSet, name="record_set_name")
