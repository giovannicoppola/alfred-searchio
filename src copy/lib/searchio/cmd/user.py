#!/usr/bin/env python
# encoding: utf-8
#
# Copyright (c) 2016 Dean Jackson <deanishe@deanishe.net>
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2016-12-17
#

"""searchio user [options] [<query>]

View and edit user searches.

Usage:
    searchio user [-t] [<query>]
    searchio -h

Options:
    -t, --text     Print results as text, not Alfred JSON
    -h, --help     Display this help message
"""

from __future__ import print_function, absolute_import

from operator import attrgetter
import sys

from docopt import docopt

from searchio.core import Context
from searchio.engines import Search
from searchio import util

log = util.logger(__name__)

_text_help = """\
You have saved the following searches.

"""


def usage(wf=None):
    """CLI usage instructions."""
    return __doc__


def run(wf, argv):
    """Run ``searchio user`` sub-command."""
    args = docopt(usage(wf), argv)
    ctx = Context(wf)
    query = wf.decode(args.get('<query>') or '').strip()
    ICON_BACK = ctx.icon('back')
    # log.debug('args=%r', args)

    # Load both default and user searches
    searches = []
    
    # Get list of deleted default engines from workflow settings
    deleted_defaults = set()
    deleted_config = wf.settings.get('deleted_defaults', '')
    if deleted_config:
        deleted_defaults = set(deleted_config.split(','))
    
    # First, load default searches (excluding deleted ones)
    from .reload import DEFAULTS
    for default_data in DEFAULTS:
        if default_data['uid'] not in deleted_defaults:
            searches.append(Search.from_dict(default_data))
    
    # Then, load user searches (these will override defaults if same UID)
    f = util.FileFinder([ctx.searches_dir], ['json'])
    user_searches = [Search.from_file(p) for p in f]
    
    # Merge user searches with defaults, with user searches taking precedence
    user_uids = {s.uid for s in user_searches}
    searches = [s for s in searches if s.uid not in user_uids] + user_searches
    
    searches.sort(key=attrgetter('title'))

    if query:
        searches = wf.filter(query, searches, key=attrgetter('title'))
    else:
        it = wf.add_item(
            u'Configuration',
            'Back to configuration',
            arg='back',
            valid=True,
            icon=ICON_BACK)
        it.setvar('action', 'back')

    log.debug('%d search(es)', len(searches))

    if args.get('--text') or util.textmode():  # Display for terminal

        print(_text_help, file=sys.stderr)

        table = util.Table([u'ID', u'Title'])
        for s in searches:
            table.add_row((s.uid, s.title))

        print(table)
        print()

    else:  # Display for Alfred
        for s in searches:
            it = wf.add_item(
                s.title,
                'Reveal configuration in Finder',
                autocomplete=s.title,
                arg=s.uid,
                valid=True,
                icon=s.icon,
            )
            it.setvar('search', s.uid)
            it.setvar('action', 'reveal')
            m = it.add_modifier('cmd', u'Delete search')
            m.setvar('action', 'delete')
            m.setvar('search', s.uid)  # Ensure search UID is passed to delete action

        wf.send_feedback()
