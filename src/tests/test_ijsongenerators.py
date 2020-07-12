import io
import pytest
import ijsongenerators


def test_map_array():
    for k, v in ijsongenerators.parse(io.BytesIO(b'{"moose": [1, "a", 3]}')):
        assert k == "moose"
        assert list(v) == [(0, 1), (1, "a"), (2, 3)]


def test_map():
    for k, v in ijsongenerators.parse(io.BytesIO(b'{"moose": "goose"}')):
        assert k == "moose"
        assert v == "goose"


def test_map_nested():
    expected = {"a": 1, "b": 2, "c": 3}
    for k, v in ijsongenerators.parse(
        io.BytesIO(b'{"moose": [{"a": 1}, {"b": 2}, {"c": 3}]}')
    ):
        assert k == "moose"
        for _, o in v:
            for x, y in o:
                assert expected[x] == y


def test_skip_index():
    for k, v in ijsongenerators.parse(
        io.BytesIO(b'{"moose": [{"a": 1}, {"b": {"nested": [1, 2, 3]}}, {"c": 3}]}')
    ):
        assert k == "moose"
        assert list(n for (n, _) in v) == [0, 1, 2]


def test_skip_array():
    for k, v in ijsongenerators.parse(
        io.BytesIO(
            b'{"moose": {"a": [1, 2, 3], "b": {"nested": [1, 2, 3]}, "c": [1, 2, 3]}}'
        )
    ):
        assert k == "moose"
        assert list(k for (k, _) in v) == ["a", "b", "c"]


def test_skip_nested():
    expected = {"d": 1, "e": 2, "f": 3}
    for k, v in ijsongenerators.parse(
        io.BytesIO(
            b'{"moose": [{"a": 1}, {"b": 2}, {"c": 3}], "goose": [{"d": 1}, {"e": 2}, {"f": 3}]}'
        )
    ):
        if k == "goose":
            for _, o in v:
                for x, y in o:
                    assert expected[x] == y


@pytest.yield_fixture
def data():
    return io.BytesIO(
        b"""{
  "level-1": [
    {
      "level-2": [
        {
          "level-3a": [
            {
              "a": 1,
              "b": "moose",
              "c": "goose"
            },
            {
              "a": 2,
              "b": "truce",
              "c": "deduce"
            },
            {
              "a": 3,
              "b": "house",
              "c": "flute"
            }
          ]
        },
        {
          "level-3b": [
            {
              "x": 9,
              "b": "10"
            }
          ]
        }
      ]
    }
  ]
}
"""
    )


def test_basic(data):
    found = []
    for username, sessions in ijsongenerators.parse(data):
        for _, session in sessions:
            for session_name, groups in session:
                for _, group in groups:
                    for group_type, lines in group:
                        if group_type != "level-3a":
                            continue
                        for _, line in lines:
                            found.append(dict(line))

    assert found == [
        {"a": 1, "b": "moose", "c": "goose"},
        {"a": 2, "b": "truce", "c": "deduce"},
        {"a": 3, "b": "house", "c": "flute"},
    ]