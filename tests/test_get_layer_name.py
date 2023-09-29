import os

import pytest
from geodense.lib import _get_valid_layer_name


def test_get_layer_name(test_dir):
    l_name = _get_valid_layer_name(os.path.join(test_dir, "data/polygons.json"), None)
    assert l_name == "polygonen"


def test_get_layer_name_not_existing(test_dir):
    with pytest.raises(
        ValueError,
        match=r"layer_name foobar not found in file .+, layers: .+",
    ):
        _ = _get_valid_layer_name(
            os.path.join(test_dir, "data/polygons.json"), "foobar"
        )


def test_get_layer_name_default_from_multi_file(test_dir):
    with pytest.raises(
        ValueError,
        match=(
            r"input_file .+ contains more than 1 layer: .+, "
            r"specify which layer to use with optional layer argument"
        ),
    ):
        _ = _get_valid_layer_name(os.path.join(test_dir, "data/linestrings.gpkg"), None)


def test_get_layer_name_from_multi_file(test_dir):
    layer_name = "polygonen"
    result = _get_valid_layer_name(
        os.path.join(test_dir, "data/linestrings.gpkg"), layer_name
    )
    assert result == layer_name
