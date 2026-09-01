"""Locale-safe text emission shared by MathHead's command boundaries."""

from __future__ import annotations

import codecs
import sys
from typing import Any


ENCODING_CONTRACT_ID = "MH-C-ENCODING-001"
ENCODING_CONTRACT_SHA256 = \
    "b47e07c259a8357000d57cde4238b61ea11a872113d713165515dc86a54cf210"


def safe_text(text: str, encoding: str | None) -> str:
    """Return text that the declared destination encoding can represent visibly."""
    if not isinstance(text, str):
        raise TypeError("text must be str")
    if encoding is not None and not isinstance(encoding, str):
        raise TypeError("encoding must be str or None")
    if encoding is None:
        return text
    codec = codecs.lookup(encoding)
    if codec.name.startswith(("utf-8", "utf-16", "utf-32")):
        return text
    try:
        text.encode(codec.name, errors="strict")
    except UnicodeEncodeError:
        return text.encode(codec.name, errors="backslashreplace").decode(codec.name)
    return text


def safe_print(*values: Any, sep: str | None = " ", end: str | None = "\n",
               file: Any = None, flush: bool = False) -> None:
    """A print-compatible boundary that changes only unencodable code points."""
    if sep is None:
        sep = " "
    elif not isinstance(sep, str):
        raise TypeError("sep must be None or a string")
    if end is None:
        end = "\n"
    elif not isinstance(end, str):
        raise TypeError("end must be None or a string")
    stream = sys.stdout if file is None else file
    payload = sep.join(str(value) for value in values) + end
    stream.write(safe_text(payload, getattr(stream, "encoding", None)))
    if flush:
        stream.flush()


__all__ = [
    "ENCODING_CONTRACT_ID",
    "ENCODING_CONTRACT_SHA256",
    "safe_print",
    "safe_text",
]
