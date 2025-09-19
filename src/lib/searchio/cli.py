#!/usr/bin/env python3
# encoding: utf-8
#
# Copyright (c) 2016 Dean Jackson <deanishe@deanishe.net>
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2016-03-13
#

"""searchio <command> [<options>] [<args>...]

Alfred 3 workflow to provide search completion suggestions
from various search engines in various languages.

Usage:
    searchio <command> [<args>...]
    searchio -h|--version

Options:
    -h, --help       Display this help message
    --version        Show version number and exit

Commands:
    add          Add a new search to the workflow
    clean        Delete stale cache files
    config       Display (filtered) settings
    delete       Delete a search engine
    help         Show help for a command
    list         Display (filtered) list of engines
    reload       Update info.plist
    search       Perform a search
    variants     Display (filtered) list of engine variants
    web          Import a new search from a URL
"""

from __future__ import absolute_import, print_function

import os
import sys

from searchio import util

log = util.logger(__name__)


def usage(wf=None):
    """CLI usage instructions."""
    return __doc__


def cli(wf):
    """Script entry point.

    Args:
        wf (worflow.Workflow3): Active workflow object.

    """
    from docopt import docopt

    vstr = "{} v{}".format(wf.name, wf.version)
    wf.args
    args = docopt(usage(wf), version=vstr, options_first=True)
    log.debug("args=%r", args)

    cmd = args.get("<command>")
    argv = [cmd] + args.get("<args>")

    # ---------------------------------------------------------
    # Initialise

    for fn in ("backups", "engines", "icons", "searches"):
        try:
            os.makedirs(wf.datafile(fn), 0o700)
        except Exception as err:
            if err.errno != 17:  # ignore file exists
                raise err

    # ---------------------------------------------------------
    # Call sub-command

    if cmd == "add":
        from searchio.cmd.add import run

        return run(wf, argv)

    elif cmd == "clean":
        from searchio.cmd.clean import run

        return run(wf, argv)

    elif cmd == "config":
        from searchio.cmd.config import run

        return run(wf, argv)

    elif cmd == "delete":
        from searchio.cmd.delete import run

        return run(wf, argv)

    elif cmd == "fetch":
        from searchio.cmd.fetch import run

        return run(wf, argv)

    elif cmd == "help":
        from searchio.cmd.help import run

        return run(wf, argv)

    elif cmd == "list":
        from searchio.cmd.list import run

        return run(wf, argv)

    elif cmd == "reload":
        from searchio.cmd.reload import run

        return run(wf, argv)

    elif cmd == "search":
        from searchio.cmd.search import run

        return run(wf, argv)

    elif cmd == "toggle":
        from searchio.cmd.toggle import run

        return run(wf, argv)

    elif cmd == "user":
        from searchio.cmd.user import run

        return run(wf, argv)

    elif cmd == "variants":
        from searchio.cmd.variants import run

        return run(wf, argv)

    elif cmd == "web":
        from searchio.cmd.web import run

        return run(wf, argv)

    else:
        raise ValueError('Unknown command "{}". Use -h for help.'.format(cmd))


def main():
    from workflow import Workflow3

    from searchio import HELP_URL

    wf = Workflow3(help_url=HELP_URL)
    sys.exit(wf.run(cli))
