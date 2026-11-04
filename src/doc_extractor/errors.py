"""Public, actionable error types. Never include private document content in errors."""


class DocExtractError(Exception):
    """Base error for expected failures in the public API."""


class UnsupportedFileError(DocExtractError):
    """The supplied document type or signature is unsupported."""


class InputLimitError(DocExtractError):
    """The input exceeds a configured resource limit."""


class DocumentReadError(DocExtractError):
    """A document cannot be opened or parsed safely."""


class ProfileError(DocExtractError):
    """A profile is missing, unsafe, malformed, or incompatible."""


class ExportError(DocExtractError):
    """An output format is unavailable or the output path is invalid."""
