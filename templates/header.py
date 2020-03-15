#!/usr/bin/env python3
"""
    ...
    {date}
"""
# Lines with '# ignore' at the end are not part of the template. # ignore
# Template placeholders and other globals are set to None so this # ignore
# can be linted while editing. # ignore
requires = None  # ignore

import os
import sys
from gi import require_version as gi_require_version
from gi.repository import Gtk
gi_require_version('Gtk', '3.0')
{requires}
