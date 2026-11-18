"""Compatibility module for existing plugins."""

import sys

from . import bot_tools

sys.modules[__name__] = bot_tools
