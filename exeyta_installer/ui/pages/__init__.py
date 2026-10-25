# -*- coding: utf-8 -*-
"""Шаги мастера установки."""
from .done import DonePage
from .license import LicensePage
from .path import PathPage
from .progress import ProgressPage
from .shortcuts import ShortcutsPage
from .welcome import WelcomePage

__all__ = ["WelcomePage", "LicensePage", "PathPage", "ShortcutsPage",
           "ProgressPage", "DonePage"]
