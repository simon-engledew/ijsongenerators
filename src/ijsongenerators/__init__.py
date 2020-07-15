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

import collections
import contextlib
import types
import typing
import re

from . import aliases

import ijson


@contextlib.contextmanager
def _drain_unused(v: aliases.IterValue):
    """
    Drain the remaining values after a generator leaves the context

    :param v: A value or iterable of values
    """
    yield v
    if isinstance(v, types.GeneratorType):
        collections.deque(v, maxlen=0)


def materialize(
    generator: aliases.NestedGenerator, value: typing.Optional[bool]
) -> typing.Generator[typing.Union[aliases.IterValue, aliases.Value], None, None]:
    """
    Configure the way a JSON generator returns its values

    :param aliases.NestedGenerator generator: A reader created with _materialize=None
    :param value: *False:* Always return nested generators. *True:* Read the document into full Python objects. *None:* return nested generators but do not configure them.
    :rtype: typing.Generator[typing.Union[aliases.IterValue, aliases.Value], None, None]
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


def parse(fileobj: typing.IO, materialize=False) -> typing.Union[aliases.IterValue, aliases.Value]:
    """
    parse a JSON document and return the results as nested generators

    :rtype: typing.Union[aliases.IterValue, aliases.Value]
    """
    stream = ijson.basic_parse(fileobj)
    return _ijson_value(stream, next(stream), materialize)


class WILDCARD:
    def __eq__(self, other):
        return True

    def __repr__(self):
        return "*"


WILDCARD = WILDCARD()
"""
Match any other value in an equality check
"""


ARRAY_INDEX = re.compile("^\[\d+\]$")


def _parse_component(s: str) -> typing.Union[str, int]:
    if s == "*":
        return WILDCARD
    if ARRAY_INDEX.match(s):
        return int(s[1:-1])
    return s


def parse_path(s: str) -> typing.Tuple[typing.Union[str, WILDCARD.__class__]]:
    """
    Similar syntax to the ijson path, but supports array indexes::

        "key.[0]"

    And wildcards::

        "key.*"
    """
    return tuple(_parse_component(component) for component in s.split("."))


def search(fileobj: typing.IO, *path: typing.Any) -> typing.Generator[aliases.Value, None, None]:
    """
    Return a list of all matching items at `path`, where `path` is a list of keys:

    ::

        ijsongenerators.search(jsonio, 'users' ijsongenerators.WILDCARD, 'sessions', 0, 'hash')

    Will index into the document at: `users.*.sessions.*.hash`

    :param fileobj: an IO to read the JSON data from
    :param path: a path to a section of the document
    :rtype: aliases.Value
    """
    if len(path) == 0:
        return []
    return _search(parse(fileobj, None), 0, path)


def _search(
    generator: aliases.NestedGenerator, index: int, path: typing.List[typing.Any],
) -> typing.Generator[aliases.Value, None, None]:
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

