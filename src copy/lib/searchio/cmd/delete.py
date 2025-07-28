#!/usr/bin/env python
# encoding: utf-8
#
# Copyright (c) 2016 Dean Jackson <deanishe@deanishe.net>
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2016-12-17
#

"""searchio delete <uid>

Delete a search engine.

Usage:
    searchio delete <uid>
    searchio delete -h

Options:
    -h, --help     Display this help message
"""

from __future__ import print_function, absolute_import

import os
import sys

from docopt import docopt

from searchio.core import Context
from searchio import util

log = util.logger(__name__)

# Default search UIDs that can be deleted
DEFAULT_UIDS = {'google-en', 'wikipedia-en', 'youtube-us'}


def usage(wf=None):
    """CLI usage instructions."""
    return __doc__


def run(wf, argv):
    """Run ``searchio delete`` sub-command."""
    args = docopt(usage(wf), argv)
    ctx = Context(wf)
    search_uid = wf.decode(args.get('<uid>') or '').strip()
    
    if not search_uid:
        log.error('No search UID provided')
        return 1
    
    log.debug('Deleting search: %s', search_uid)
    
    if search_uid in DEFAULT_UIDS:
        # Handle default engine deletion - just mark as deleted in settings
        deleted_defaults = set(wf.settings.get('deleted_defaults', '').split(','))
        deleted_defaults.add(search_uid)
        wf.settings['deleted_defaults'] = ','.join(filter(None, deleted_defaults))
        log.info('Marked default search "%s" as deleted', search_uid)
        print('Default search "{}" marked as deleted'.format(search_uid), file=sys.stderr)
    else:
        # Handle user engine deletion - remove the JSON file (existing behavior)
        file_path = os.path.join(ctx.searches_dir, search_uid + '.json')
        if os.path.exists(file_path):
            os.remove(file_path)
            log.info('Deleted user search file: %s', file_path)
            print('User search "{}" deleted'.format(search_uid), file=sys.stderr)
        else:
            log.error('Search file not found: %s', file_path)
            print('Search "{}" not found'.format(search_uid), file=sys.stderr)
            return 1
    
    return 0 