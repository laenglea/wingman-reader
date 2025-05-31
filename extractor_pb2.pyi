from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Format(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FORMAT_TEXT: _ClassVar[Format]
    FORMAT_IMAGE: _ClassVar[Format]
    FORMAT_PDF: _ClassVar[Format]
FORMAT_TEXT: Format
FORMAT_IMAGE: Format
FORMAT_PDF: Format

class ExtractRequest(_message.Message):
    __slots__ = ("file", "url", "format")
    FILE_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    FORMAT_FIELD_NUMBER: _ClassVar[int]
    file: File
    url: str
    format: Format
    def __init__(self, file: _Optional[_Union[File, _Mapping]] = ..., url: _Optional[str] = ..., format: _Optional[_Union[Format, str]] = ...) -> None: ...

class File(_message.Message):
    __slots__ = ("name", "content", "content_type")
    NAME_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    name: str
    content: bytes
    content_type: str
    def __init__(self, name: _Optional[str] = ..., content: _Optional[bytes] = ..., content_type: _Optional[str] = ...) -> None: ...
