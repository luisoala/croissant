"""Field module."""

from __future__ import annotations

import dataclasses
from typing import Any

from ml_croissant._src.core import constants
from ml_croissant._src.core.issues import Issues
from ml_croissant._src.core.json_ld import remove_none_values
from ml_croissant._src.structure_graph.base_node import Node
from ml_croissant._src.structure_graph.nodes.source import Source


@dataclasses.dataclass(frozen=True, repr=False)
class ParentField:
    references: Source | None = None
    source: Source | None = None

    @classmethod
    def from_json(cls, issues: Issues, json_) -> ParentField | None:
        if json_ is None:
            return None
        references = json_.get(str(constants.ML_COMMONS_REFERENCES))
        source = json_.get(str(constants.ML_COMMONS_SOURCE))
        return cls(
            references=Source.from_json_ld(issues, references),
            source=Source.from_json_ld(issues, source),
        )

    def to_json(self):
        return remove_none_values(
            {
                "references": self.references.to_json(),
                "source": self.source.to_json(),
            }
        )


@dataclasses.dataclass(eq=False, repr=False)
class Field(Node):
    """Nodes to describe a dataset Field."""

    description: str | None = None
    # `data_type` is different than `node.actual_data_type`. See `actual_data_type`.
    data_type: str | list[str] | None = None
    is_enumeration: bool | None = dataclasses.field(default=None, hash=True, repr=True)
    name: str = ""
    parent_field: ParentField | None = None
    references: Source = dataclasses.field(default_factory=Source)
    repeated: bool | None = None
    source: Source = dataclasses.field(default_factory=Source)
    sub_fields: tuple[Field, ...] = ()

    def check(self):
        """Implements checks on the node."""
        self.assert_has_mandatory_properties("name")
        self.assert_has_optional_properties("description")
        self.source.check_source(self.add_error)

    @property
    def actual_data_type(self) -> str | list[str] | None:
        """Recursively retrieves the actual data type of the node.

        The data_type can be either directly on the node (`data_type`) or on one
        of the parent fields.
        """
        if self.data_type is not None:
            return self.data_type
        parent = next(self.graph.predecessors(self), None)
        if parent is None or not isinstance(parent, Field):
            self.add_error(
                f"The field does not specify any {constants.ML_COMMONS_DATA_TYPE},"
                " neither does any of its predecessor."
            )
            return None
        return parent.actual_data_type

    @property
    def data(self) -> str | None:
        """The data of the parent RecordSet."""
        if hasattr(self.parent, "data"):
            return getattr(self.parent, "data")
        return None

    def to_json(self) -> dict[str, Any]:
        data_type = _data_type_to_json(self.data_type)
        parent_field = self.parent_field.to_json() if self.parent_field else None
        return remove_none_values(
            {
                "@type": "ml:Field",
                "name": self.name,
                "description": self.description,
                "dataType": data_type,
                "isEnumeration": self.is_enumeration,
                "parentField": parent_field,
                "repeated": self.repeated,
                "references": self.references.to_json() if self.references else None,
                "source": self.source.to_json() if self.source else None,
                "subField": [sub_field.to_json() for sub_field in self.sub_fields],
            }
        )


def _data_type_to_json(data_type: str | list[str] | None):
    # Find a clean alternative to this...
    WIKI = "https://www.wikidata.org/wiki/"
    if data_type is None:
        return None
    elif isinstance(data_type, list):
        return [_data_type_to_json(d) for d in data_type]
    elif isinstance(data_type, str) and data_type.startswith(constants.ML_COMMONS):
        return data_type.replace(constants.ML_COMMONS, "ml:")
    elif isinstance(data_type, str) and data_type.startswith(constants.SCHEMA_ORG):
        return data_type.replace(constants.SCHEMA_ORG, "sc:")
    # This is very ugly, please pass the context:
    elif isinstance(data_type, str) and data_type.startswith(WIKI):
        return data_type.replace(WIKI, "wd:")
    else:
        return data_type
