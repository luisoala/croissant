"""FileSet module."""

import dataclasses
from typing import Any

from ml_croissant._src.core.json_ld import remove_none_values
from ml_croissant._src.structure_graph.base_node import Node


@dataclasses.dataclass(eq=False, repr=False)
class FileSet(Node):
    """Nodes to describe a dataset FileSet (distribution)."""

    contained_in: list[str] = dataclasses.field(default_factory=list)
    description: str | None = None
    encoding_format: str = ""
    includes: str = ""
    name: str = ""

    def check(self):
        """Implements checks on the node."""
        self.assert_has_mandatory_properties("includes", "encoding_format", "name")

    def to_json(self) -> dict[str, Any]:
        if isinstance(self.contained_in, list) and len(self.contained_in) == 1:
            contained_in = self.contained_in[0]
        else:
            contained_in = self.contained_in
        return remove_none_values(
            {
                "@type": "sc:FileSet",
                "name": self.name,
                "description": self.description,
                "containedIn": contained_in,
                "encodingFormat": self.encoding_format,
                "includes": self.includes,
            }
        )
