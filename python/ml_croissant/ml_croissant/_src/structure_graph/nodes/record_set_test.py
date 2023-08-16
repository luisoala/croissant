"""record_set module."""

import pytest

from ml_croissant._src.core.issues import Context
from ml_croissant._src.core.issues import Issues
from ml_croissant._src.tests.nodes import create_test_field
from ml_croissant._src.tests.nodes import create_test_record_set


@pytest.mark.parametrize(
    ["data", "error"],
    [
        [
            {"foo": "bar"},
            (
                "[record_set(record_set_name)] http://mlcommons.org/schema/data should"
                " declare a list. Got: <class 'dict'>."
            ),
        ],
        [
            [],
            (
                "[record_set(record_set_name)] http://mlcommons.org/schema/data should"
                " declare a non empty list."
            ),
        ],
        [
            [[{"foo": "bar"}]],
            (
                "[record_set(record_set_name)] http://mlcommons.org/schema/data should"
                " declare a list of dict. Got: a list of <class 'list'>."
            ),
        ],
        [
            [{"foo": "bar"}],
            (
                "[record_set(record_set_name)] Line #0 doesn't have the expected"
                " columns. Expected: {'field_name'}. Got: {'foo'}."
            ),
        ],
    ],
)
def test_invalid_data(data, error):
    issues = Issues()
    field = create_test_field(issues=issues)
    record_set = create_test_record_set(
        issues=issues,
        context=Context(record_set_name="record_set_name"),
        data=data,
        fields=[field],
    )
    record_set.check()
    assert error in issues.errors
