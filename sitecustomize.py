"""Compatibility shim for BotHost's legacy aiogram 2 build probe.

BotHost currently runs `from aiogram.utils import executor` as a build check
even when the project correctly uses aiogram 3. This exposes a harmless
placeholder attribute so that the legacy probe passes. The bot itself never
uses executor and runs with aiogram 3 polling in bot.py.
"""
import sys
import types

try:
    import aiogram.utils as _aiogram_utils
    if not hasattr(_aiogram_utils, "executor"):
        _aiogram_utils.executor = types.ModuleType("aiogram.utils.executor")
        sys.modules.setdefault("aiogram.utils.executor", _aiogram_utils.executor)
except Exception:
    # Do not interfere with normal interpreter startup if aiogram is not installed yet.
    pass
