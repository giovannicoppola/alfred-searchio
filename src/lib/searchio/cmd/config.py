#!/usr/bin/env python
# encoding: utf-8
#
# Copyright (c) 2016 Dean Jackson <deanishe@deanishe.net>
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2016-12-17
#

"""searchio config [<query>]

Display (and optionally filter) workflow configuration
options.

Usage:
    searchio config [<query>]
    searchio config -h

Options:
    -h, --help     Display this help message
"""

from __future__ import absolute_import, print_function

from operator import itemgetter

from docopt import docopt
from workflow import ICON_WARNING  # ICON_SETTINGS,

# from searchio.engines import Manager as EngineManager
from searchio import util
from searchio.core import Context

log = util.logger(__name__)


def usage(wf=None):
    """CLI usage instructions."""
    return __doc__


def run(wf, argv):
    """Run ``searchio list`` sub-command."""
    ctx = Context(wf)
    ICON_ACTIVE = ctx.icon("searches-active")

    ICON_HELP = ctx.icon("help")
    ICON_IMPORT = ctx.icon("import")
    ICON_RELOAD = ctx.icon("reload")
    ICON_ON = ctx.icon("toggle-on")
    ICON_OFF = ctx.icon("toggle-off")

    args = docopt(usage(wf), argv)

    log.debug("args=%r", args)
    query = wf.decode(args.get("<query>") or "").strip()

    # ---------------------------------------------------------
    # Configuration items

    items = []

    items.append(
        dict(
            title="Installed Searches \U00002026",
            subtitle="Your configured searches",
            arg="user",
            valid=True,
            icon=ICON_ACTIVE,
        )
    )

    items.append(
        dict(
            title="All Engines \U00002026",
            subtitle="View supported engines and add new searches",
            arg="engines",
            valid=True,
            icon="icon.png",
        )
    )

    items.append(
        dict(
            title="Reload",
            subtitle="Re-create your searches",
            arg="reload",
            valid=True,
            # autocomplete=u'workflow:help',
            # valid=False,
            icon=ICON_RELOAD,
        )
    )

    icon = ICON_ON if ctx.getbool("SHOW_QUERY_IN_RESULTS") else ICON_OFF
    items.append(
        dict(
            title="Show Query in Results",
            subtitle="Always add query to end of results",
            arg="toggle-show-query",
            valid=True,
            # autocomplete=u'workflow:help',
            # valid=False,
            icon=icon,
        )
    )

    icon = ICON_ON if ctx.getbool("ALFRED_SORTS_RESULTS") else ICON_OFF
    items.append(
        dict(
            title="Alfred Sorts Results",
            subtitle="Apply Alfred's knowledge to suggestions",
            arg="toggle-alfred-sorts",
            valid=True,
            # autocomplete=u'workflow:help',
            # valid=False,
            icon=icon,
        )
    )

    items.append(
        dict(
            title="Online Help",
            subtitle="Open the help page in your browser",
            arg="help",
            valid=True,
            # autocomplete=u'workflow:help',
            # valid=False,
            icon=ICON_HELP,
        )
    )

    # ---------------------------------------------------------
    # Show results

    if query:
        items = wf.filter(query, items, key=itemgetter("title"))

    if not items:
        wf.add_item("No matching items", "Try a different query?", icon=ICON_WARNING)

    for d in items:
        wf.add_item(**d)

    wf.send_feedback()
    return
