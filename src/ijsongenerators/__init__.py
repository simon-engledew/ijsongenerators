# coding: utf-8
"""
This module wraps the ijson_ library with some convienence functions.

`search` allows you to wildcard index into a document::

  for path, found in ijsongenerators.search(jsonio, *ijsongenerators.parse_path("level-1.[0].*"):
        print(found, " at ", path)

and will only resolve the search results into Python objects. The rest of the document will
not be deserialized.

`parse` will create nested generators that allow you to iterate through each level of the document::

  for key, values in ijsongenerators.parse(jsonio):
      for index, value in values:
          print(key, value)

With this you can happily traverse JSON that is much larger than the available system memory.

.. _ijson: https://pypi.org/project/ijson/

"""

import abc
import collections
import contextlib
import types
import typing
import re

import ijson


MapGenerator = typing.Generator[typing.Tuple[str, "IterValue"], typing.Optional[bool], None]
ArrayGenerator = typing.Generator[typing.Tuple[int, "IterValue"], typing.Optional[bool], None]
NestedGenerator = typing.Union[MapGenerator, ArrayGenerator]
"""
Generates array (int, T) or object (str, T) values during parsing of a JSON document.
"""

Value = typing.Union[typing.Dict, typing.List, bool, str, int, float, None]
"""
A value in the JSON document that has been deserialized into a Python object
"""

IterValue = typing.Union[NestedGenerator, str, int, None, bool]
"""
A leaf value in the JSON document or a generator into another nested value.
"""
ValueGenerator = typing.Generator[
    typing.Tuple[typing.Union[str, int], typing.Union[IterValue, Value]], typing.Optional[bool], None
]


@contextlib.contextmanager
def _drain_unused(v: IterValue):
    """
    Drain the remaining values after a generator leaves the context

    :param v: A value or iterable of values
    """
    yield v
    if isinstance(v, types.GeneratorType):
        collections.deque(v, maxlen=0)


def materialize(generator: NestedGenerator, value: typing.Optional[bool]) -> ValueGenerator:
    """
    Configure the way a JSON generator returns its values

    :param NestedGenerator generator: A reader created with _materialize=None
    :param value: *False:* Always return nested generators. *True:* Read the document into full Python objects. *None:* return nested generators but do not configure them.
    :rtype: typing.Generator[typing.Union[IterValue, Value], None, None]
    """
    generator.send(None)
    try:
        yield generator.send(value)
    except StopIteration:
        return
    yield from generator


def _ijson_value(parser, current, _materialize):
    """
    Dispatches the current event to the correct reader or returns value if it is a literal
    """
    event, value = current

    if event == "start_map":
        reader = _ijson_map_reader(parser, current=current)
        if _materialize is False:
            return materialize(reader, False)
        if _materialize is True:
            return dict((k, v) for k, v in materialize(reader, True))
        return reader
    elif event == "start_array":
        reader = _ijson_array_reader(parser, current=current)
        if _materialize is False:
            return materialize(reader, False)
        if _materialize is True:
            return [v for _, v in materialize(reader, True)]
        return reader
    else:
        return value


def _ijson_array_reader(parser, current=None):
    """
    Reads items from the stream until the end_array is matched
    """
    _materialize = yield

    assert current == ("start_array", None)

    idx = 0

    for current in parser:
        event, value = current

        if event == "end_array":
            return

        with _drain_unused(_ijson_value(parser, current, _materialize)) as value:
            yield (idx, value)

        idx += 1


def _ijson_map_reader(parser, current):
    """
    Reads pairs from the stream until the end_map is matched
    """
    _materialize = yield

    assert current == ("start_map", None)

    for event, key in parser:
        if event == "end_map":
            return

        current = next(parser)

        with _drain_unused(_ijson_value(parser, current, _materialize)) as value:
            yield (key, value)


def parse(fileobj: typing.IO, materialize=False) -> ValueGenerator:
    """
    parse a JSON document and return the results as nested generators

    :rtype: ValueGenerator
    """
    stream = ijson.basic_parse(fileobj)
    return _ijson_value(stream, next(stream), materialize)


class Equality(typing.Protocol):
    @abc.abstractmethod
    def __eq__(self, other: typing.Any) -> bool:
        pass


def singleton(cls):
    return cls()


@singleton
class WILDCARD:
    """
    Match any other value in an equality check
    """

    def __eq__(self, _):
        return True

    def __repr__(self):
        return "*"


ARRAY_INDEX = re.compile("^\[\d+\]$")


def _parse_component(s: str) -> Equality:
    if s == "*":
        return WILDCARD
    if ARRAY_INDEX.match(s):
        return int(s[1:-1])
    return s


def parse_path(s: str) -> typing.Tuple[Equality, ...]:
    """
    Similar syntax to the ijson path, but supports array indexes::

        "key.[0]"

    And wildcards::

        "key.*"
    """
    return tuple(_parse_component(component) for component in s.split("."))


def search(fileobj: typing.IO, *path: typing.Any) -> typing.Generator[Value, None, None]:
    """
    Return a list of all matching items at `path`, where `path` is a list of keys:

    ::

        ijsongenerators.search(jsonio, 'users' ijsongenerators.WILDCARD, 'sessions', 0, 'hash')

    Will index into the document at: `users.*.sessions.*.hash`

    :param fileobj: an IO to read the JSON data from
    :param path: a path to a section of the document
    :rtype: Value
    """
    if len(path) == 0:
        return iter([])

    parsed = parse(fileobj, None)

    if not isinstance(parsed, types.GeneratorType):
        return iter([])

    return _search(typing.cast(NestedGenerator, parsed), 0, path)


def _search(
    generator: NestedGenerator, index: int, path: typing.List[typing.Any],
) -> typing.Generator[Value, None, None]:
    head, tail = path[: index + 1], path[index + 1 :]

    *head, current = head

    leaf = True if len(tail) == 0 else None

    for k, v in materialize(generator, leaf):
        if k == current:
            if leaf:
                yield (*head, k), v
            else:
                if isinstance(v, types.GeneratorType):
                    yield from _search(v, index + 1, (*head, k, *tail))


__all__ = ["parse", "search", "WILDCARD", "parse_path"]

