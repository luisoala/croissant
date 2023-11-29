import enum

import streamlit as st

from core.state import Metadata
from events.metadata import handle_metadata_change
from events.metadata import MetadataEvent

# List from https://www.kaggle.com/discussions/general/116302.
licenses = [
    "Other",
    "Public Domain",
    "Public",
    "CC-0",
    "PDDL",
    "CC-BY",
    "CDLA-Permissive-1.0",
    "ODC-BY",
    "CC-BY-SA",
    "CDLA-Sharing-1.0",
    "ODC-ODbL",
    "CC BY-NC",
    "CC BY-ND",
    "CC BY-NC-SA",
    "CC BY-NC-ND",
]


def render_metadata():
    metadata = st.session_state[Metadata]
    try:
        index = licenses.index(metadata.license)
    except ValueError:
        index = None
    key = "metadata-license"
    st.selectbox(
        label="License",
        help="More information on license names and meaning can be found [here](https://www.kaggle.com/discussions/general/116302).",
        key=key,
        options=licenses,
        index=index,
        on_change=handle_metadata_change,
        args=(MetadataEvent.LICENSE, metadata, key),
    )
    key = "metadata-citation"
    st.text_area(
        label="Citation",
        key=key,
        value=metadata.citation,
        placeholder="@book{\n  title={Title}\n}",
        on_change=handle_metadata_change,
        args=(MetadataEvent.CITATION, metadata, key),
    )
