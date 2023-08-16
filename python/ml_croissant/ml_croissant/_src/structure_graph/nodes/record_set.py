"""RecordSet module."""

from __future__ import annotations

import dataclasses
from typing import Any

from ml_croissant._src.core import constants
from ml_croissant._src.core.json_ld import remove_none_values
from ml_croissant._src.structure_graph.base_node import Node
from ml_croissant._src.structure_graph.nodes.field import Field


@dataclasses.dataclass(eq=False, repr=False)
class RecordSet(Node):
    """Nodes to describe a dataset RecordSet."""

    # `data` is passed as a string for the moment, because dicts and lists are not
    # hashable.
    data: list[Any] | None = dataclasses.field(default=None, hash=True, repr=True)
    description: str | None = dataclasses.field(default=None, hash=True, repr=True)
    is_enumeration: bool | None = dataclasses.field(default=None, hash=True, repr=True)
    key: str | tuple[str] | None = dataclasses.field(default=None, hash=True, repr=True)
    name: str = dataclasses.field(default="", hash=True, repr=True)
    fields: list[Field] = dataclasses.field(
        default_factory=list, hash=False, repr=False
    )

    def check(self):
        """Implements checks on the node."""
        self.assert_has_mandatory_properties("name")
        self.assert_has_optional_properties("description")
        if self.data is not None:
            data = self.data
            if not isinstance(data, list):
                self.add_error(
                    f"{constants.ML_COMMONS_DATA} should declare a list. Got:"
                    f" {type(data)}."
                )
                return
            if not data:
                self.add_error(
                    f"{constants.ML_COMMONS_DATA} should declare a non empty list."
                )
            expected_keys = {field.name for field in self.fields}
            for i, line in enumerate(data):
                if not isinstance(line, dict):
                    self.add_error(
                        f"{constants.ML_COMMONS_DATA} should declare a list of dict."
                        f" Got: a list of {type(line)}."
                    )
                    return
                keys = set(line.keys())
                if keys != expected_keys:
                    self.add_error(
                        f"Line #{i} doesn't have the expected columns. Expected:"
                        f" {expected_keys}. Got: {keys}."
                    )

    def to_json(self) -> dict[str, Any]:
        return remove_none_values(
            {
                "@type": "ml:RecordSet",
                "name": self.name,
                "description": self.description,
                "isEnumeration": self.is_enumeration,
                "key": list(self.key) if isinstance(self.key, tuple) else self.key,
                "field": [field.to_json() for field in self.fields],
                "data": self.data,
            }
        )
