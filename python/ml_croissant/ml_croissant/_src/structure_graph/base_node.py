"""Base node module."""

from __future__ import annotations

import abc
import dataclasses
import re
from typing import Any

from etils import epath
import networkx as nx

from ml_croissant._src.core import constants
from ml_croissant._src.core.issues import Context
from ml_croissant._src.core.issues import Issues

ID_REGEX = "[a-zA-Z0-9\\-_\\.]+"
_MAX_ID_LENGTH = 255


@dataclasses.dataclass(eq=False, repr=False)
class Node(abc.ABC):
    """Structure node in Croissant.

    This generic class will be inherited by the actual Croissant nodes:
    - Field
    - FileObject
    - FileSet
    - Metadata
    - RecordSet

    When building the node, `self.issues` are populated when issues are encountered.

    Args:
        issues: the issues that will be modified in-place.
        # Update me....
        graph: The structure graph.
        parents: The parent nodes in the Croissant JSON-LD as a tuple.
        folder: The path of the Croissant folder.
        name: The name of the node.
    """

    # CLEAN ME
    issues: Issues = dataclasses.field(hash=False)
    context: Context
    graph: nx.MultiDiGraph = dataclasses.field(
        default_factory=nx.MultiDiGraph, hash=False
    )
    parents: list[Node] = dataclasses.field(default_factory=list, hash=False)
    folder: epath.Path | None = None  # not needed anymore???
    name: str = dataclasses.field(default="<unknown>", hash=True)

    def __post_init__(self):
        """Checks for `name` (common property between all nodes)."""
        self.assert_has_mandatory_properties("name")
        validate_name(self.issues, self.name)

    def assert_has_mandatory_properties(self, *mandatory_properties: str):
        """Checks a node in the graph for existing properties with constraints.

        Args:
            mandatory_properties: A list of mandatory properties for the current node.
                If the node doesn't have one, it triggers an error.
        """
        for mandatory_property in mandatory_properties:
            value = getattr(self, mandatory_property)
            if not value:
                error = (
                    f'Property "{constants.FROM_CROISSANT.get(mandatory_property)}" is'
                    " mandatory, but does not exist."
                )
                self.add_error(error)

    def assert_has_optional_properties(self, *optional_properties: str):
        """Checks a node in the graph for existing properties with constraints.

        Args:
            optional_properties: A list of optional properties for the current node. If
                the node doesn't have one, it triggers a warning.
        """
        for optional_property in optional_properties:
            value = getattr(self, optional_property)
            if not value:
                error = (
                    f'Property "{constants.FROM_CROISSANT.get(optional_property)}" is'
                    " recommended, but does not exist."
                )
                self.add_warning(error)

    def assert_has_exclusive_properties(self, *exclusive_properties: list[str]):
        """Checks a node in the graph for existing properties with constraints.

        Args:
            exclusive_properties: A list of list of exclusive properties: the current
                node should have at least one.
        """
        for possible_exclusive_properties in exclusive_properties:
            if not there_exists_at_least_one_property(
                self, possible_exclusive_properties
            ):
                error = (
                    "At least one of these properties should be defined:"
                    f" {possible_exclusive_properties}."
                )
                self.add_error(error)

    def add_error(self, error: str):
        """Adds a new error."""
        self.issues.add_error(error, self.context)

    def add_warning(self, warning: str):
        """Adds a new warning."""
        self.issues.add_warning(warning, self.context)

    @abc.abstractmethod
    def check(self):
        """Abstract method to implement checks that will be performed on the node."""
        raise NotImplementedError()

    def __repr__(self) -> str:
        """Prints a simplified string representation of the node."""
        return f'{self.__class__.__name__}(uid="{self.uid}")'

    @property
    def uid(self) -> str:
        """Unique identifier for the node.

        For fields, the UID is the path from their RecordSet. For other nodes, it is
        their names.
        """
        if len(self.parents) <= 1:
            return self.name
        return f"{self.parents[-1].uid}/{self.name}"

    @property
    def parent(self) -> Node | None:
        """Direct parent of the node or None if no parent."""
        if not self.parents:
            return None
        return self.parents[-1]

    def to_json(self) -> dict[str, Any]:
        raise NotImplementedError()


def validate_name(issues: Issues, name: str):
    """Validates the name (which are used as unique identifiers in Croissant)."""
    if not isinstance(name, str):
        issues.add_error(f"The identifier should be a string. Got: {type(name)}.")
    if len(name) > _MAX_ID_LENGTH:
        issues.add_error(
            f'The identifier "{name}" is too long (>{_MAX_ID_LENGTH} characters).'
        )
    regex = re.compile(rf"^{ID_REGEX}$")
    if not regex.match(name):
        issues.add_error(f'The identifier "{name}" contains forbidden characters.')
    return name


def there_exists_at_least_one_property(node: Node, possible_properties: list[str]):
    """Checks for the existence of one of `possible_exclusive_properties` in `keys`."""
    for possible_property in possible_properties:
        if getattr(node, possible_property, None) is not None:
            return True
    return False


def _get_element(nodes: tuple[Node, ...], cls_names: list[str]):
    return next(
        (node.name for node in nodes if node.__class__.__name__ in cls_names), None
    )
