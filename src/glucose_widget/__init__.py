"""Small always-on-top Nightscout glucose widget."""

try:
    from ._version import version as __version__
except ImportError:
    # The generated file is available after installing/building the package.
    # This fallback keeps direct source checkouts importable as well.
    __version__ = "0+unknown"
