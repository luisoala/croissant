"""FileObject module."""

import dataclasses
from typing import Any

from ml_croissant._src.core.json_ld import remove_none_values
from ml_croissant._src.structure_graph.base_node import Node
from ml_croissant._src.structure_graph.nodes.source import Source


@dataclasses.dataclass(eq=False, repr=False)
class FileObject(Node):
    """Nodes to describe a dataset FileObject (distribution)."""

    content_url: str = ""
    content_size: str = ""
    contained_in: list[str] = dataclasses.field(default_factory=list)
    description: str | None = None
    encoding_format: str = ""
    md5: str | None = None
    name: str = ""
    sha256: str | None = None
    source: Source | None = None

    def check(self):
        """Implements checks on the node."""
        self.assert_has_mandatory_properties("content_url", "encoding_format", "name")
        if not self.contained_in:
            self.assert_has_exclusive_properties(["md5", "sha256"])

    def to_json(self) -> dict[str, Any]:
        if isinstance(self.contained_in, list) and len(self.contained_in) == 1:
            contained_in = self.contained_in[0]
        else:
            contained_in = self.contained_in
        return remove_none_values(
            {
                "@type": "sc:FileObject",
                "name": self.name,
                "description": self.description,
                "contentSize": self.content_size,
                "contentUrl": self.content_url,
                "containedIn": contained_in,
                "encodingFormat": self.encoding_format,
                "md5": self.md5,
                "sha256": self.sha256,
                "source": self.source.to_json() if self.source else None,
            }
        )
