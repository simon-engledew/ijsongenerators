import io
import pytest
import ijsongenerators


def test_map():
    for k in ijsongenerators.parse(io.BytesIO(b'{"moose": "goose"}')):
        assert k == "moose"


def test_map_items():
    for k, v in ijsongenerators.parse(io.BytesIO(b'{"moose": "goose"}')).items():
        assert k == "moose"
        assert v == "goose"


def test_map_array():
    for k, v in ijsongenerators.parse(io.BytesIO(b'{"moose": [1, 2, 3]}')).items():
        assert k == "moose"
        assert tuple(v) == (1, 2, 3)


def test_map_nested():
    expected = {"a": 1, "b": 2, "c": 3}
    for k, v in ijsongenerators.parse(
        io.BytesIO(b'{"moose": [{"a": 1}, {"b": 2}, {"c": 3}]}')
    ).items():
        assert k == "moose"
        for o in v:
            for x, y in o.items():
                assert expected[x] == y


def test_skip_nested():
    expected = {"d": 1, "e": 2, "f": 3}
    for k, v in ijsongenerators.parse(
        io.BytesIO(
            b'{"moose": [{"a": 1}, {"b": 2}, {"c": 3}], "goose": [{"d": 1}, {"e": 2}, {"f": 3}]}'
        )
    ).items():
        if k == "goose":
            for o in v:
                for x, y in o.items():
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
    for username, sessions in ijsongenerators.parse(data).items():
        for session in sessions:
            for session_name, groups in session.items():
                for group in groups:
                    for group_type, lines in group.items():
                        if group_type != "level-3a":
                            continue
                        for line in lines:
                            found.append(dict(line.items()))

    assert found == [
        {"a": 1, "b": "moose", "c": "goose"},
        {"a": 2, "b": "truce", "c": "deduce"},
        {"a": 3, "b": "house", "c": "flute"},
    ]
