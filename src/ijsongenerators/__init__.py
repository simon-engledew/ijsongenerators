from typing import Generator
import ijson
import typing
import contextlib
import types
import collections
import threading


END = object()

options = threading.local()

MapGenerator = typing.Generator[typing.Tuple[str, "T"], None, None]
ArrayGenerator = typing.Generator[typing.Tuple[int, "T"], None, None]
T = typing.Union[MapGenerator, ArrayGenerator, str, int, None, bool]


@contextlib.contextmanager
def _drain_unused(generator):
    yield generator
    if isinstance(generator, types.GeneratorType):
        collections.deque(generator, maxlen=0)


def _ijson_value(parser, current):
    """
    dispatches the current event to the correct reader or returns value if it is a literal
    """
    event, value = current

    if event == "start_map":
        reader = _ijson_map_reader(parser, current=current)
        if options.consume:
            return dict((k, v) for k, v in reader)
        return reader
    elif event == "start_array":
        reader = _ijson_array_reader(parser, current=current)
        if options.consume:
            return [v for _, v in reader]
        return reader
    else:
        return value


def _ijson_array_reader(parser, current=None):
    """
    reads items from the stream until the end_array is matched
    """
    if current is None:
        current = next(parser, END)

    if current is END:
        return

    assert current == ("start_array", None)

    idx = 0

    for current in parser:
        event, value = current

        if event == "end_array":
            return

        with _drain_unused(_ijson_value(parser, current)) as value:
            yield (idx, value)

        idx += 1


def _ijson_map_reader(parser, current=None):
    """
    reads pairs from the stream until the end_map is matched
    """
    if current is None:
        current = next(parser, END)

    if current is END:
        return

    assert current == ("start_map", None)

    for event, key in parser:
        if event == "end_map":
            return

        current = next(parser, END)

        if current is END:
            return

        with _drain_unused(_ijson_value(parser, current)) as value:
            yield (key, value)


def parse(fileobj: typing.IO,) -> MapGenerator:
    """
    parse a JSON document and return the results as nested generators
    """
    options.consume = False
    return _ijson_map_reader(ijson.basic_parse(fileobj))


class WILDCARD:
    def __eq__(self, other):
        return True


WILDCARD = WILDCARD()


def search(
    generator: typing.Union[MapGenerator, ArrayGenerator],
    *paths: typing.Union[str, int]
):
    path, *rest = paths
    last = len(paths) == 1
    options.consume = last
    try:
        for k, v in generator:
            if k == path:
                if last:
                    if isinstance(v, types.GeneratorType):
                        yield from v
                    else:
                        yield v
                else:
                    yield from search(v, *rest)
    finally:
        options.consume = False


__all__ = ["parse", "search", "WILDCARD"]

