import typing

MapGenerator = typing.Generator[typing.Tuple[str, "aliases.IterValue"], None, None]
ArrayGenerator = typing.Generator[typing.Tuple[int, "aliases.IterValue"], None, None]
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


__all__ = ["IterValue", "Value", "NestedGenerator"]
