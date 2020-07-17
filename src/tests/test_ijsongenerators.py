# coding: utf-8

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


def test_empty_map():
    assert len(list(ijsongenerators.parse(io.BytesIO(b"{}")))) == 0


def test_empty_list():
    assert len(list(ijsongenerators.parse(io.BytesIO(b"[]")))) == 0


def test_map_nested():
    expected = {"a": 1, "b": 2, "c": 3}
    for k, v in ijsongenerators.parse(io.BytesIO(b'{"moose": [{"a": 1}, {"b": 2}, {"c": 3}]}')):
        assert k == "moose"
        for _, o in v:
            for x, y in o:
                assert expected[x] == y


def test_skip_index():
    for k, v in ijsongenerators.parse(io.BytesIO(b'{"moose": [{"a": 1}, {"b": {"nested": [1, 2, 3]}}, {"c": 3}]}')):
        assert k == "moose"
        assert list(n for (n, _) in v) == [0, 1, 2]


def test_skip_array():
    for k, v in ijsongenerators.parse(
        io.BytesIO(b'{"moose": {"a": [1, 2, 3], "b": {"nested": [1, 2, 3]}, "c": [1, 2, 3]}}')
    ):
        assert k == "moose"
        assert list(k for (k, _) in v) == ["a", "b", "c"]


def test_search():
    for path, v in ijsongenerators.search(
        io.BytesIO(b'{"moose": {"a": [1, 2, 3], "b": {"nested": [1, 2, 3]}, "c": [1, 2, 3]}}'), "moose", "a", 2,
    ):
        assert v == 3

    for path, v in ijsongenerators.search(
        io.BytesIO(b'{"moose": {"a": [1, 2, 3], "b": {"nested": [1, 2, 3]}, "c": [1, 2, 3], "d": 1}}'),
        "moose",
        "b",
        "nested",
        0,
    ):
        assert v == 1


def test_search_wildcard():
    gen = ijsongenerators.search(
        io.BytesIO(b'{"moose": {"a": [1, 2, 3], "b": {"nested": [1, 2, 3]}, "c": [4, 5, 6]}, "d": 1}'),
        ijsongenerators.WILDCARD,  # match moose / b / c
        ijsongenerators.WILDCARD,  # match a / nested / array
    )
    assert next(gen) == (("moose", "a"), [1, 2, 3])
    assert next(gen) == (("moose", "b"), {"nested": [1, 2, 3]})
    assert next(gen) == (("moose", "c"), [4, 5, 6])


def test_search_nested():
    path = (
        "moose",  # {}
        ijsongenerators.WILDCARD,  # []
        ijsongenerators.WILDCARD,  # {}
    )
    gen = ijsongenerators.search(io.BytesIO(b"""{"moose":[{"goose":[{"house":[{"truce":0}]}]}]}"""), *path)
    assert list(gen) == [(("moose", 0, "goose"), [{"house": [{"truce": 0}]}])]


def test_search_miss():
    for path, v in ijsongenerators.search(io.BytesIO(b'{"moose": 1}'),):
        print(path)


def test_skip_nested():
    expected = {"d": 1, "e": 2, "f": 3}
    for k, v in ijsongenerators.parse(
        io.BytesIO(b'{"moose": [{"a": 1}, {"b": 2}, {"c": 3}], "goose": [{"d": 1}, {"e": 2}, {"f": 3}]}')
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


def test_search_literal():
    assert list(ijsongenerators.search(io.BytesIO(b"1"), "*")) == []


def test_parse_path():
    path = ijsongenerators.parse_path("level-1.[0].*.[0].level-3a.*.b")
    assert path == ("level-1", 0, ijsongenerators.WILDCARD, 0, "level-3a", ijsongenerators.WILDCARD, "b")

    jsonio = io.BytesIO(
        b'{"level-1":[{"level-2":[{"level-3a":[{"a":1,"b":"moose","c":"goose"},{"a":2,"b":"truce","c":"deduce"},{"a":3,"b":"house","c":"flute"}]},{"level-3b":[{"x":9,"b":"10"}]}]}]}'
    )

    assert list(ijsongenerators.search(jsonio, *path)) == [
        (("level-1", 0, "level-2", 0, "level-3a", 0, "b"), "moose"),
        (("level-1", 0, "level-2", 0, "level-3a", 1, "b"), "truce"),
        (("level-1", 0, "level-2", 0, "level-3a", 2, "b"), "house"),
    ]
