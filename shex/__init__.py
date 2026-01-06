"""
Shex - Natural language command-line assistant
"""

try:
    from importlib.metadata import version
    __version__ = version("shex")
except Exception:
    __version__ = "0.1.0"
