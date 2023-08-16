"""Structure graph module.

The goal of this module is the static analysis of the JSON file. We convert the initial
JSON to a so-called "structure graph", which is a Python representation of the JSON
containing the nodes (Metadata, FileObject, etc) and the hierarchy between them. In the
process of parsing all the nodes, we also check that no information is missing and raise
issues (errors or warnings) when necessary. See the docstring of
`from_nodes_to_structure_graph` for more information.

The important functions of this module are:
- from_file_to_json             file -> JSON
- from_json_to_rdf              JSON -> RDF
- from_rdf_to_nodes             RDF -> nodes
- from_nodes_to_structure_graph nodes -> structure graph

TODO(https://github.com/mlcommons/croissant/issues/114):
A lot of methods in this file share common data structures (issues, graph, folder, etc),
so they should be grouped under a common `StructureGraph` class.
"""

from __future__ import annotations

import collections
import dataclasses
import json
from typing import Any

from etils import epath
import networkx as nx
import rdflib
from rdflib import term

from ml_croissant._src.core import constants
from ml_croissant._src.core.issues import Context
from ml_croissant._src.core.issues import Issues
from ml_croissant._src.core.json_ld import _is_dataset_node
from ml_croissant._src.core.json_ld import _sort_dict
from ml_croissant._src.core.json_ld import expand_json_ld
from ml_croissant._src.core.json_ld import recursively_populate_fields
from ml_croissant._src.structure_graph.base_node import Node
from ml_croissant._src.structure_graph.nodes.field import Field
from ml_croissant._src.structure_graph.nodes.field import ParentField
from ml_croissant._src.structure_graph.nodes.file_object import FileObject
from ml_croissant._src.structure_graph.nodes.file_set import FileSet
from ml_croissant._src.structure_graph.nodes.metadata import Metadata
from ml_croissant._src.structure_graph.nodes.record_set import RecordSet
from ml_croissant._src.structure_graph.nodes.source import Source

Json = dict[str, Any]


def from_file_to_jsonld(filepath: epath.PathLike) -> tuple[epath.Path, Json]:
    """Loads the file as a JSON.

    Args:
        filepath: The path to the file as a str or a path. The path can be absolute or
            relative.

    Returns:
        A tuple with the absolute path to the file and the JSON.
    """
    filepath = epath.Path(filepath).expanduser().resolve()
    if not filepath.exists():
        raise ValueError(f"File {filepath} does not exist.")
    with filepath.open() as f:
        data = json.load(f)
    graph = rdflib.Graph()
    graph.parse(
        data=data,
        format="json-ld",
    )
    # `graph.serialize` outputs a stringified list of JSON-LD nodes.
    nodes = graph.serialize(format="json-ld")
    nodes = json.loads(nodes)
    return filepath, nodes


# In jsonld.py?
def from_jsonld_to_json(jsonld: list[Json]) -> Json:
    # Check jsonld is not empty
    id_to_node: dict[str, Json] = {}
    for node in jsonld:
        node_id = node.get("@id")
        id_to_node[node_id] = node
    # Find the entry node (schema.org/Dataset).
    entry_node = next(
        (record for record in jsonld if _is_dataset_node(record)), jsonld[0]
    )
    recursively_populate_fields(entry_node, id_to_node)
    return entry_node


# This shluld be a classmethod: Field.from_jsonld? Same for all.
def new_field(
    issues: Issues, context: Context, field: Json, is_sub_field: bool = False
) -> Field:
    check_expected_type(
        issues,
        field,
        constants.ML_COMMONS_FIELD_TYPE,
    )
    references_jsonld = field.get(str(constants.ML_COMMONS_REFERENCES))
    references = Source.from_json_ld(issues, references_jsonld)
    source_jsonld = field.get(str(constants.ML_COMMONS_SOURCE))
    source = Source.from_json_ld(issues, source_jsonld)
    data_type = field.get(str(constants.ML_COMMONS_DATA_TYPE), {})
    is_enumeration = field.get(str(constants.SCHEMA_ORG_IS_ENUMERATION))
    if isinstance(data_type, dict):
        data_type = data_type.get("@id")
    elif isinstance(data_type, list):
        data_type = [d.get("@id") for d in data_type]
    else:
        data_type = None
    field_name = field.get(str(constants.SCHEMA_ORG_NAME), "")
    if is_sub_field:
        context.sub_field_name = field_name
    else:
        context.field_name = field_name
    sub_fields = field.get(str(constants.ML_COMMONS_SUB_FIELD), [])
    if isinstance(sub_fields, dict):
        sub_fields = [sub_fields]
    sub_fields = [
        new_field(issues, context, sub_field, is_sub_field=True)
        for sub_field in sub_fields
    ]
    parent_field = ParentField.from_json(
        issues, field.get(str(constants.SCHEMA_ORG_PARENT_FIELD))
    )
    repeated = field.get(str(constants.SCHEMA_ORG_REPEATED))
    return Field(
        issues=issues,
        context=context,
        description=field.get(str(constants.SCHEMA_ORG_DESCRIPTION)),
        data_type=data_type,
        is_enumeration=is_enumeration,
        name=field_name,
        parent_field=parent_field,
        references=references,
        repeated=repeated,
        source=source,
        sub_fields=sub_fields,
    )


def check_expected_type(issues: Issues, json_: Json, expected_type: str):
    node_name = json_.get(str(constants.SCHEMA_ORG_NAME), "<unknown node>")
    node_type = json_.get("@type")
    if node_type != str(expected_type):
        issues.add_error(
            f'"{node_name}" should have an attribute "@type": "{expected_type}". Got'
            f" {node_type} instead."
        )


def json_to_nodes(issues: Issues, json_: Json, folder: epath.Path) -> Metadata:
    file_sets: list[FileSet] = []
    file_objects: list[FileObject] = []
    record_sets: list[RecordSet] = []
    params = {"issues": issues, "folder": folder}
    json_distributions = json_.pop(str(constants.SCHEMA_ORG_DISTRIBUTION), [])
    dataset_name = json_.get(str(constants.SCHEMA_ORG_NAME), "")
    for json_distribution in json_distributions:
        content_url = json_distribution.get(str(constants.SCHEMA_ORG_CONTENT_URL))
        contained_in = json_distribution.get(str(constants.SCHEMA_ORG_CONTAINED_IN))
        name = json_distribution.get(str(constants.SCHEMA_ORG_NAME), "")
        if contained_in is not None and not isinstance(contained_in, list):
            contained_in = [contained_in]
        distribution_type = json_distribution.get("@type")
        if distribution_type == str(constants.SCHEMA_ORG_FILE_OBJECT):
            content_size = json_distribution.get(str(constants.SCHEMA_ORG_CONTENT_SIZE))
            description = json_distribution.get(str(constants.SCHEMA_ORG_DESCRIPTION))
            encoding_format = json_distribution.get(
                str(constants.SCHEMA_ORG_ENCODING_FORMAT)
            )
            file_object = FileObject(
                **params,
                context=Context(dataset_name=dataset_name, distribution_name=name),
                content_url=content_url,
                content_size=content_size,
                contained_in=contained_in,
                description=description,
                encoding_format=encoding_format,
                md5=json_distribution.get(str(constants.SCHEMA_ORG_MD5)),
                name=name,
                sha256=json_distribution.get(str(constants.SCHEMA_ORG_SHA256)),
                source=json_distribution.get(str(constants.ML_COMMONS_SOURCE)),
            )
            file_objects.append(file_object)
        elif distribution_type == str(constants.SCHEMA_ORG_FILE_SET):
            file_set = FileSet(
                **params,
                context=Context(dataset_name=dataset_name, distribution_name=name),
                contained_in=contained_in,
                description=json_distribution.get(
                    str(constants.SCHEMA_ORG_DESCRIPTION)
                ),
                encoding_format=json_distribution.get(
                    str(constants.SCHEMA_ORG_ENCODING_FORMAT)
                ),
                includes=json_distribution.get(str(constants.ML_COMMONS_INCLUDES)),
                name=name,
            )
            file_sets.append(file_set)
        else:
            issues.add_error(
                f'"{name}" should have an attribute "@type":'
                f' "{str(constants.SCHEMA_ORG_FILE_OBJECT)}" or "@type":'
                f' "{str(constants.SCHEMA_ORG_FILE_SET)}". Got'
                f" {distribution_type} instead."
            )
    json_record_sets = json_.pop(str(constants.ML_COMMONS_RECORD_SET), [])
    for json_record_set in json_record_sets:
        record_set_name = json_record_set.get(str(constants.SCHEMA_ORG_NAME), "")
        context = Context(dataset_name=dataset_name, record_set_name=record_set_name)
        fields = json_record_set.pop(str(constants.ML_COMMONS_FIELD), [])
        if isinstance(fields, dict):
            fields = [fields]
        fields = [new_field(issues, context, field) for field in fields]
        json_key = json_record_set.get(str(constants.SCHEMA_ORG_KEY))
        if isinstance(json_key, list):
            key = tuple(json_key)
        else:
            key = json_key
        data = json_record_set.get(str(constants.ML_COMMONS_DATA))
        is_enumeration = json_record_set.get(str(constants.SCHEMA_ORG_IS_ENUMERATION))
        check_expected_type(
            issues, json_record_set, constants.ML_COMMONS_RECORD_SET_TYPE
        )
        record_set = RecordSet(
            **params,
            context=Context(dataset_name=dataset_name, record_set_name=record_set_name),
            data=data,
            description=json_record_set.get(str(constants.SCHEMA_ORG_DESCRIPTION)),
            is_enumeration=is_enumeration,
            key=key,
            fields=tuple(fields),
            name=record_set_name,
        )
        record_sets.append(record_set)
    check_expected_type(issues, json_, constants.SCHEMA_ORG_DATASET)
    metadata = Metadata(
        **params,
        context=Context(dataset_name=dataset_name),
        citation=json_.get(str(constants.SCHEMA_ORG_CITATION)),
        description=json_.get(str(constants.SCHEMA_ORG_DESCRIPTION)),
        file_objects=tuple(file_objects),
        file_sets=tuple(file_sets),
        language=json_.get(str(constants.SCHEMA_ORG_LANGUAGE)),
        license=json_.get(str(constants.SCHEMA_ORG_LICENSE)),
        name=dataset_name,
        record_sets=tuple(record_sets),
        url=json_.get(str(constants.SCHEMA_ORG_URL)),
    )
    # Define parents
    for node in metadata.distribution:
        node.parents = [metadata]
    for record_set in metadata.record_sets:
        record_set.parents = [metadata]
        for field in record_set.fields:
            field.parents = [metadata, record_set]
            for sub_field in field.sub_fields:
                sub_field.parents = [metadata, record_set, field]
    # Check that nodes are consistent
    for node in metadata.nodes():
        node.check()
    return metadata


def from_nodes_to_graph(metadata: Metadata) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    # Bind graph to nodes:
    for node in metadata.nodes():
        node.graph = graph
        graph.add_node(node)
    uid_to_node = _check_no_duplicate(metadata)
    for node in metadata.distribution:
        if node.contained_in:
            for uid in node.contained_in:
                _add_edge(graph, uid_to_node, uid, node)
    for record_set in metadata.record_sets:
        for field in record_set.fields:
            if record_set.data:
                _add_edge(graph, uid_to_node, record_set.uid, field)
            # Ici on pourrait checker que field.source != None
            for origin in [field.source, field.references]:
                if origin:
                    _add_edge(graph, uid_to_node, origin.uid, field)
            for sub_field in field.sub_fields:
                for origin in [sub_field.source, sub_field.references]:
                    if origin:
                        _add_edge(graph, uid_to_node, origin.uid, sub_field)
    # `Metadata` are used as the entry node.
    _add_node_as_entry_node(graph, metadata)
    return graph


def from_json_to_rdf(data: Json) -> rdflib.Graph:
    """Converts the JSON to an RDF graph with expanded JSON-LD attributes using RDFLib.

    We use RDFLib instead of reinventing a JSON-LD parser. This may be more cumbersome
    short-term, but will prove handy long-term, when we integrate more advanced feature
    of RDF/JSON-LD, or other parsers (e.g., YAML-LD).

    We prefer the RDF graph representation over the JSON-LD representation because the
    former is easier to traverse the graph than the JSON.

    Args:
        data: The JSON dict.

    Returns:
        A tuple with the RDF namespace manager (see:
            https://rdflib.readthedocs.io/en/stable/namespaces_and_bindings.html) and
            the RDF graph.
    """
    graph = rdflib.Graph()
    graph.parse(
        data=data,
        format="json-ld",
    )
    return graph


@dataclasses.dataclass
class StructureGraph:
    issues: Issues
    graph: nx.MultiDiGraph
    metadata: Metadata
    filepath: epath.Path | None

    def to_json(self):
        json_ = self.metadata.to_json()
        return _sort_dict(json_)

    def to_jsonld(self):
        json_ = self.to_json()
        return expand_json_ld(json_)

    @classmethod
    def from_json(
        cls, issues: Issues, json_: Json, filepath: epath.Path | None = None
    ) -> StructureGraph:
        folder = filepath.parent
        metadata = json_to_nodes(issues, json_, folder)
        graph = from_nodes_to_graph(metadata)
        return cls(issues=issues, graph=graph, metadata=metadata, filepath=filepath)

    @classmethod
    def from_file(cls, issues: Issues, file: epath.PathLike) -> StructureGraph:
        filepath, jsonld = from_file_to_jsonld(file)
        json_ = from_jsonld_to_json(jsonld)
        return cls.from_json(issues, json_, filepath=filepath)

    def check_graph(self):
        """Checks the integrity of the structure graph.

        The rules are the following:
        - The graph is directed.
        - All fields have a data type: either directly specified, or on a parent.

        Args:
            issues: The issues to populate in case of problem.
            graph: The structure graph to be checked.
        """
        # Check that the graph is directed.
        if not self.graph.is_directed():
            self.issues.add_error("The structure graph is not directed.")
        fields = [node for node in self.graph.nodes if isinstance(node, Field)]
        # Check all fields have a data type: either on the field, on a parent.
        for field in fields:
            field.actual_data_type


def get_entry_nodes(graph: nx.MultiDiGraph) -> list[Node]:
    """Retrieves the entry nodes (without predecessors) in a graph."""
    entry_nodes: list[Node] = []
    for node, indegree in graph.in_degree(graph.nodes()):
        if indegree == 0:
            entry_nodes.append(node)
    # Fields should usually not be entry nodes, except if they have subFields. So we
    # check for this:
    for node in entry_nodes:
        if isinstance(node, Field) and not node.sub_fields and not node.data:
            if not node.source:
                node.add_error(
                    f'Node "{node.uid}" is a field and has no source. Please, use'
                    f" {constants.ML_COMMONS_SOURCE} to specify the source."
                )
            else:
                uid = node.source.uid
                node.add_error(
                    f"Malformed source data: {uid}. It does not refer to any existing"
                    f" node. Have you used {constants.ML_COMMONS_FIELD} or"
                    f" {constants.SCHEMA_ORG_DISTRIBUTION} to indicate the source field"
                    " or the source distribution? If you specified a field, it should"
                    " contain all the names from the RecordSet separated by `/`, e.g.:"
                    ' "record_set_name/field_name"'
                )
    return entry_nodes


def _check_no_duplicate(metadata: Metadata) -> dict[str, Node]:
    """Checks that no node has duplicated UID and returns the mapping `uid`->`Node`."""
    uid_to_node: dict[str, Node] = {}
    for node in metadata.nodes():
        if node.uid in uid_to_node:
            node.add_error(
                f"Duplicate nodes with the same identifier: {uid_to_node[node.uid].uid}"
            )
        uid_to_node[node.uid] = node
    return uid_to_node


def _add_node_as_entry_node(graph: nx.MultiDiGraph, node: Node):
    """Add `node` as the entry node of the graph by updating `graph` in place."""
    graph.add_node(node, parent=None)
    entry_nodes = get_entry_nodes(graph)
    for entry_node in entry_nodes:
        if isinstance(node, (FileObject, FileSet)):
            graph.add_edge(entry_node, node)


def _add_edge(
    graph: nx.MultiDiGraph,
    uid_to_node: dict[str, Node],
    uid: str,
    node: Node,
):
    """Adds an edge in the structure graph."""
    if uid not in uid_to_node:
        node.add_error(
            f'There is a reference to node named "{uid}" in node "{node.uid}", but this'
            " node doesn't exist."
        )
        return
    graph.add_edge(uid_to_node[uid], node)
