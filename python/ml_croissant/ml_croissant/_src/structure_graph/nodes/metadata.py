"""Metadata module."""

from __future__ import annotations

import dataclasses
from typing import Any

from ml_croissant._src.core.json_ld import _make_context
from ml_croissant._src.core.json_ld import remove_none_values
from ml_croissant._src.structure_graph.base_node import Node
from ml_croissant._src.structure_graph.nodes.file_object import FileObject
from ml_croissant._src.structure_graph.nodes.file_set import FileSet
from ml_croissant._src.structure_graph.nodes.record_set import RecordSet


@dataclasses.dataclass(eq=False, repr=False)
class Metadata(Node):
    """Nodes to describe a dataset metadata."""

    citation: str | None = None
    description: str | None = None
    language: str | None = None
    license: str | None = None
    name: str = ""
    url: str = ""
    file_objects: list[FileObject] = dataclasses.field(default_factory=list)
    file_sets: list[FileSet] = dataclasses.field(default_factory=list)
    record_sets: list[RecordSet] = dataclasses.field(default_factory=list)

    def check(self):
        """Implements checks on the node."""
        self.assert_has_mandatory_properties("name", "url")
        self.assert_has_optional_properties("citation", "license")

    def to_json(self) -> dict[str, Any]:
        return remove_none_values(
            {
                "@context": _make_context(),
                "@language": self.language,
                "@type": "sc:Dataset",
                "name": self.name,
                "description": self.description,
                "citation": self.citation,
                "license": self.license,
                "url": self.url,
                "distribution": [f.to_json() for f in self.distribution],
                "recordSet": [record_set.to_json() for record_set in self.record_sets],
            }
        )

    @property
    def distribution(self) -> list[FileObject | FileSet]:
        return self.file_objects + self.file_sets

    def nodes(self) -> list[Node]:
        """List all nodes in metadata."""
        nodes: list[Node] = [self]
        nodes.extend(self.distribution)
        nodes.extend(self.record_sets)
        for record_set in self.record_sets:
            nodes.extend(record_set.fields)
            for field in record_set.fields:
                nodes.extend(field.sub_fields)
        return nodes
