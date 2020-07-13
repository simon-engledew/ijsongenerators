import ijson
import typing
import contextlib
import types
import collections


END = object()

MapGenerator = typing.Generator[typing.Tuple[str, "T"], None, None]
ArrayGenerator = typing.Generator[typing.Tuple[int, "T"], None, None]
T = typing.Union[MapGenerator, ArrayGenerator, str, int, None, bool]


@contextlib.contextmanager
def _drain_unused(v: T):
    """
    drain the remaining values after a generator leaves the context
    """
    yield v
    if isinstance(v, types.GeneratorType):
        collections.deque(v, maxlen=0)


def with_materialize(
    generator: typing.Union[MapGenerator, ArrayGenerator], value: typing.Optional[bool]
):
    """
    Configure the way a JSON generator returns its values

    False: return nested generators
    True: return nested Python objects
    None: return nested generators but do not configure them
    """
    generator.send(None)
    try:
        yield generator.send(value)
    except StopIteration:
        return
    yield from generator


def _ijson_value(parser, current, materialize):
    """
    dispatches the current event to the correct reader or returns value if it is a literal
    """
    event, value = current

    if event == "start_map":
        reader = _ijson_map_reader(parser, current=current)
        if materialize is False:
            return with_materialize(reader, False)
        if materialize is True:
            return dict((k, v) for k, v in with_materialize(reader, True))
        return reader
    elif event == "start_array":
        reader = _ijson_array_reader(parser, current=current)
        if materialize is False:
            return with_materialize(reader, False)
        if materialize is True:
            return [v for _, v in with_materialize(reader, True)]
        return reader
    else:
        return value


def _ijson_array_reader(parser, current=None):
    """
    reads items from the stream until the end_array is matched
    """
    materialize = yield

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

        with _drain_unused(_ijson_value(parser, current, materialize)) as value:
            yield (idx, value)

        idx += 1


def _ijson_map_reader(parser, current=None):
    """
    reads pairs from the stream until the end_map is matched
    """
    materialize = yield

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

        with _drain_unused(_ijson_value(parser, current, materialize)) as value:
            yield (key, value)


def parse(fileobj: typing.IO, materialize=False) -> MapGenerator:
    """
    parse a JSON document and return the results as nested generators
    """
    return with_materialize(_ijson_map_reader(ijson.basic_parse(fileobj)), materialize)


class WILDCARD:
    """
    Match any other value in an equality check
    """

    def __str__(self):
        return "*"

    def __eq__(self, other):
        return True


WILDCARD = WILDCARD()


def search(
    fileobj: typing.IO, *path: typing.Union[str, int]
) -> typing.Generator[
    typing.Union[typing.Dict, typing.List, bool, str, int, None], None, None
]:
    """
    return a list of all matching items at path, where path is a list of keys

    e.g: search(json, 'users' ijsongenerators.WILDCARD, 'sessions', 0, 'hash')
    """
    return _search(_ijson_map_reader(ijson.basic_parse(fileobj)), *path)


def _search(
    generator: typing.Union[MapGenerator, ArrayGenerator], *path: typing.Union[str, int]
) -> typing.Generator[
    typing.Union[typing.Dict, typing.List, bool, str, int, None], None, None
]:
    head, *rest = path
    leaf = True if len(rest) == 0 else None

    for k, v in with_materialize(generator, leaf):
        if k == head:
            if leaf:
                if isinstance(v, types.GeneratorType):
                    yield from v
                else:
                    yield v
            else:
                if isinstance(v, types.GeneratorType):
                    yield from _search(v, *rest)


__all__ = ["parse", "search", "WILDCARD"]

