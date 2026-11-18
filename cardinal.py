"""Compatibility imports for plugins written for FunPay Cardinal."""

from funpaynext import FunPayNEXT as Cardinal, PluginData, get_app as get_cardinal

__all__ = ["Cardinal", "PluginData", "get_cardinal"]
