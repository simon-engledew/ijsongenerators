import ijson
import functools
import typing
import contextlib
import types
import collections


@contextlib.contextmanager
def _drain_unused(generator):
    yield generator
    if isinstance(generator, types.GeneratorType):
        collections.deque(generator, maxlen=0)


def _ijson_value(parser, current):
    """
    dispatches the current event to the correct reader or returns value if it is a literal
    """
    current_prefix, current_event, current_value = current

    if current_event == "start_map":
        return _ijson_map_reader(parser, current_prefix, current=current)
    elif current_event == "start_array":
        return _ijson_array_reader(parser, current_prefix, current=current)
    else:
        return current_value


def _ijson_array_reader(parser, prefix, current=None):
    """
    reads items from the stream until the end_array is matched

    ignores any items from unconsumed generators that do not have the expected prefix
    """
    if current is None:
        current = next(parser, None)

    if current is None:
        return

    current_prefix, current_event, current_value = current

    assert current_prefix == prefix
    assert current_event == "start_array"
    assert current_value == None

    item_prefix = f"{current_prefix}.item"

    idx = 0

    for current in parser:
        current_prefix, current_event, current_value = current

        if current_prefix == prefix and current_event == "end_array":
            return

        assert current_prefix == item_prefix

        with _drain_unused(_ijson_value(parser, current)) as value:
            yield (idx, value)

        idx += 1


def _ijson_map_reader(parser, prefix, current=None):
    """
    reads pairs from the stream until the end_map is matched

    ignores any pairs from unconsumed generators that do not have the expected prefix
    """
    if current is None:
        current = next(parser, None)

    if current is None:
        return

    current_prefix, current_event, current_value = current

    assert current_prefix == prefix
    assert current_event == "start_map"
    assert current_value == None

    for key_prefix, key_event, key in parser:
        assert key_prefix == prefix

        if key_event == "end_map":
            return

        assert key_event == "map_key"

        current = next(parser, None)

        if current is None:
            return

        with _drain_unused(_ijson_value(parser, current)) as value:
            yield (key, value)


def parse(fileobj: typing.IO):
    """
    parse a JSON document and return the results as nested generators
    """
    return _ijson_map_reader(ijson.parse(fileobj), "")


__all__ = ["parse"]

