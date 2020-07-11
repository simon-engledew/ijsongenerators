import ijson
import functools
import typing


def _ijson_value(parser, current):
    current_prefix, current_event, current_value = current

    if current_event == "start_map":
        return _ijson_map_reader(parser, current_prefix, current=current)
    elif current_event == "start_array":
        return _ijson_array_reader(parser, current_prefix, current=current)
    else:
        return current_value


def _ijson_array_reader(parser, prefix, current=None):
    if current is None:
        current = next(parser, None)

    if current is None:
        return

    current_prefix, current_event, current_value = current

    assert current_prefix == prefix
    assert current_event == "start_array"
    assert current_value == None

    item_prefix = f"{current_prefix}.item"

    for current in parser:
        current_prefix, current_event, current_value = current

        if current_prefix == prefix and current_event == "end_array":
            return

        if current_prefix != item_prefix:
            continue

        yield _ijson_value(parser, current)


class PairsIterator:
    def __init__(self, generator):
        self.generator = generator

    def __iter__(self):
        return (k for k, _ in self.generator)

    def items(self):
        return self.generator


def pairsiterator(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        return PairsIterator(fn(*args, **kwargs))

    return wrapped


@pairsiterator
def _ijson_map_reader(parser, prefix, current=None):
    if current is None:
        current = next(parser, None)

    if current is None:
        return

    current_prefix, current_event, current_value = current

    assert current_prefix == prefix
    assert current_event == "start_map"
    assert current_value == None

    for key_prefix, key_event, key in parser:
        if key_prefix != prefix:
            continue

        if key_event == "end_map":
            return

        assert key_event == "map_key"

        current = next(parser, None)

        if current is None:
            return

        value_prefix, value_event, value = current

        yield (key, _ijson_value(parser, current))


def parse(fileobj: typing.IO):
    """
    parse a JSON document and return the results as nested generators
    """
    return _ijson_map_reader(ijson.parse(fileobj), "")


__all__ = ["parse"]

