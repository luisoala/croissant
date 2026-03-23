# Croissant Tasks

This library provides a SHACL validation toolkit and ontology for extending schema.org and Croissant with Task descriptions. It is part of the `mlcommons/croissant` universe.

## Installation

You can install this package locally using `pip`:

```bash
pip install .
```

For development (which installs dependencies needed to run tests):

```bash
pip install -e .[dev]
```

## Usage

This package includes a validator script to check if data (in `.jsonld` format) conforms to the Croissant Tasks SHACL shapes.

```bash
python validator.py <path_to_data.jsonld>
```

For example, to test against the included example data:
```bash
python validator.py testdata/valid_solution.jsonld
```

## Running Tests

To run the full suite of unit tests, you can use `pytest`:

```bash
pytest validator_test.py
```
