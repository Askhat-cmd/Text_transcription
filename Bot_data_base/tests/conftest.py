import importlib
import sys
import types
from importlib.machinery import ModuleSpec


try:
    importlib.import_module("yt_dlp")
except Exception:
    yt_dlp_stub = types.ModuleType("yt_dlp")
    yt_dlp_stub.__spec__ = ModuleSpec(name="yt_dlp", loader=None)

    class DummyYoutubeDL:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, *args, **kwargs):
            return {}

    yt_dlp_stub.YoutubeDL = DummyYoutubeDL
    sys.modules["yt_dlp"] = yt_dlp_stub
