"""Source module."""

from __future__ import annotations

import collections
import dataclasses
import enum
import logging
import re
from typing import Any, Literal

import jsonpath_rw
from jsonpath_rw import lexer

from ml_croissant._src.core import constants
from ml_croissant._src.core.issues import Issues
from ml_croissant._src.core.json_ld import remove_none_values


class FileProperty(enum.Enum):
    """Lists the intrinsic properties of a file that are accessible from Croissant."""

    # Note that at the moment there may be an overlap with existing columns if columns
    # have one of the following names:
    content = "__content__"
    filename = "__filename__"
    filepath = "__filepath__"
    fullpath = "__fullpath__"


def is_file_property(file_property: str):
    """Checks if a string is a FileProperty (e.g., "content"->FileProperty.content)."""
    for possible_file_property in FileProperty:
        if possible_file_property.name == file_property:
            return True
    return False


@dataclasses.dataclass(frozen=True)
class Extract:
    """Container for possible ways of extracting the data."""

    csv_column: str | None = None
    file_property: FileProperty | None = None
    json_path: str | None = None

    def to_json(self):
        return remove_none_values(
            {
                "csvColumn": self.csv_column,
                "fileProperty": self.file_property.name if self.file_property else None,
                "jsonPath": self.json_path,
            }
        )


@dataclasses.dataclass(frozen=True)
class Transform:
    """Container for transformation.

    Args:
        format: The format for a date, e.g. "%Y-%m-%d %H:%M:%S.%f".
        regex: A regex pattern with a capturing group to extract information in a
            string.
        replace: A replace pattern, e.g. "pattern_to_remove/pattern_to_add".
        separator: A separator in a string to yield a list.
    """

    format: str | None = None
    regex: str | None = None
    replace: str | None = None
    separator: str | None = None

    def to_json(self):
        return remove_none_values(
            {
                "format": self.format,
                "regex": self.regex,
                "replace": self.replace,
                "separator": self.separator,
            }
        )


@dataclasses.dataclass(frozen=True)
class Source:
    r"""Python representation of sources and references.

    Croissant accepts several manners to declare sources:

    When the origin is a field:

    ```json
    "source": {
        "field": "record_set/name",
    }
    ```

    When the origin is a FileSet or a FileObject:

    ```json
    "source": {
        "distribution": "my-csv",
        "dataExtraction": {
            "csvColumn": "my-csv-column"
        }
    }
    ```

    See the specs for all supported parameters by `dataExtraction`.

    You can also add one or more transformations with `applyTransform`:

    ```json
    "source": {
        "field": "record_set/name",
        "applyTransform": {
            "format": "yyyy-MM-dd HH:mm:ss.S",
            "regex": "([^\\/]*)\\.jpg",
            "separator": "|"
        }
    }
    ```
    """

    extract: Extract = dataclasses.field(default_factory=Extract)
    transforms: tuple[Transform, ...] = ()
    uid: str | None = None
    node_type: Literal["distribution", "field"] | None = None

    def to_json(self):
        transforms = [transform.to_json() for transform in self.transforms]
        if len(transforms) == 1:
            transforms = transforms[0]
        return remove_none_values(
            {
                self.node_type: self.uid,
                "applyTransform": transforms,
                "dataExtraction": self.extract.to_json(),
            }
        )

    @classmethod
    def from_json_ld(cls, issues: Issues, json_ld: Any) -> Source:
        """Creates a new source from a JSON-LD `field` and populates issues."""
        # Ctte fonction est juste trop longue...
        if json_ld is None:
            return Source()
        elif isinstance(json_ld, list):
            if len(json_ld) != 1:
                raise ValueError(f"Field {json_ld} should have one element.")
            return Source.from_json_ld(issues, json_ld[0])
        elif isinstance(json_ld, (dict, collections.defaultdict)):
            try:
                transforms = json_ld.get(str(constants.ML_COMMONS_APPLY_TRANSFORM), [])
                if not isinstance(transforms, list):
                    transforms = [transforms]
                transforms = tuple(
                    Transform(
                        format=transform.get(str(constants.ML_COMMONS_FORMAT)),
                        regex=transform.get(str(constants.ML_COMMONS_REGEX)),
                        replace=transform.get(str(constants.ML_COMMONS_REPLACE)),
                        separator=transform.get(str(constants.ML_COMMONS_SEPARATOR)),
                    )
                    for transform in transforms
                )
                # Safely access and check "data_extraction" from JSON-LD.
                data_extraction = json_ld.get(
                    str(constants.ML_COMMONS_DATA_EXTRACTION), {}
                )
                # Not useful anymore???
                if isinstance(data_extraction, list) and data_extraction:
                    data_extraction = data_extraction[0]
                # Remove the JSON-LD @id property if it exists:
                data_extraction.pop("@id", None)
                if len(data_extraction) > 1:
                    issues.add_error(
                        f"{constants.ML_COMMONS_DATA_EXTRACTION} should have one of the"
                        f" following properties: {constants.ML_COMMONS_FORMAT},"
                        f" {constants.ML_COMMONS_REGEX},"
                        f" {constants.CROISSANT_REPLACE} or"
                        f" {constants.ML_COMMONS_SEPARATOR}"
                    )
                # Safely access and check "uid" from JSON-LD.
                distribution = json_ld.get(str(constants.SCHEMA_ORG_DISTRIBUTION))
                field = json_ld.get(str(constants.ML_COMMONS_FIELD))
                if distribution is not None and field is None:
                    uid = distribution
                    node_type = "distribution"
                elif distribution is None and field is not None:
                    uid = field
                    node_type = "field"
                else:
                    uid = None
                    node_type = None
                    issues.add_error(
                        f"Every {constants.ML_COMMONS_SOURCE} should declare either"
                        f" {constants.ML_COMMONS_FIELD} or"
                        f" {constants.SCHEMA_ORG_DISTRIBUTION}"
                    )
                # Safely access and check "file_property" from JSON-LD.
                file_property = data_extraction.get(
                    str(constants.ML_COMMONS_FILE_PROPERTY)
                )
                if is_file_property(file_property):
                    file_property = FileProperty[file_property]
                elif file_property is not None:
                    issues.add_error(
                        f"Property {constants.ML_COMMONS_FILE_PROPERTY} can only have"
                        " values in `fullpath`, `filepath` and `content`. Got:"
                        f" {file_property}"
                    )
                # Build the source.
                json_path = data_extraction.get(str(constants.ML_COMMONS_JSON_PATH))
                csv_column = data_extraction.get(str(constants.ML_COMMONS_CSV_COLUMN))
                extract = Extract(
                    csv_column=csv_column,
                    file_property=file_property,
                    json_path=json_path,
                )
                return Source(
                    extract=extract,
                    transforms=transforms,
                    uid=uid,
                    node_type=node_type,
                )
            except TypeError as exception:
                issues.add_error(
                    f"Malformed `source`: {json_ld}. Got exception: {exception}"
                )
                return Source()
        else:
            issues.add_error(f"`source` has wrong type: {type(json_ld)} ({json_ld})")
            return Source()

    def __bool__(self):
        """Allows to write `if not node.source` / `if node.source`."""
        return self.uid is not None

    def get_field(self) -> str | FileProperty:
        """Retrieves the name of the field/column/query associated to the source."""
        if self.uid is None:
            # This case already rose an issue and should not happen at run time.
            raise ""
        if self.extract.csv_column:
            return self.extract.csv_column
        elif self.extract.file_property:
            return self.extract.file_property
        elif self.extract.json_path:
            return self.extract.json_path
        else:
            return self.uid.split("/")[-1]

    def check_source(self, add_error: Any):
        """Checks if the source is valid and adds error otherwise."""
        if self.extract.json_path:
            try:
                jsonpath_rw.parse(self.extract.json_path)
            except lexer.JsonPathLexerError as exception:
                add_error(
                    "Wrong JSONPath (https://goessner.net/articles/JsonPath/):"
                    f" {exception}"
                )


def _apply_transform_fn(value: str, transform: Transform) -> str:
    """Applies one transform to `value`."""
    if transform.regex is not None:
        source_regex = re.compile(transform.regex)
        match = source_regex.match(value)
        if match is None:
            logging.debug(f"Could not match {source_regex} in {value}")
            return value
        for group in match.groups():
            if group is not None:
                return group
    return value


def apply_transforms_fn(value: str, source: Source | None = None) -> str:
    """Applies all transforms in `source` to `value`."""
    if source is None:
        return value
    transforms = source.transforms
    for transform in transforms:
        value = _apply_transform_fn(value, transform)
    return value
