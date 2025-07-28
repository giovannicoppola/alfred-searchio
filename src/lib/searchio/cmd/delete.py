#!/usr/bin/env python
# encoding: utf-8
#
# Copyright (c) 2025 
#
# MIT Licence. See http://opensource.org/licenses/MIT
#

"""searchio delete <search_uid>

Delete a search engine (default or user).

Usage:
    searchio delete <search_uid>
    searchio delete -h

Options:
    -h, --help     Display this help message
"""

from __future__ import print_function, absolute_import

import os
from docopt import docopt
from workflow import Variables

from searchio.core import Context
from searchio import util

log = util.logger(__name__)


def usage(wf=None):
    """CLI usage instructions."""
    return __doc__


def run(wf, argv):
    """Run ``searchio delete`` sub-command."""
    args = docopt(usage(wf), argv)
    search_uid = args.get('<search_uid>')
    
    if not search_uid:
        raise ValueError('Search UID is required')
    
    ctx = Context(wf)
    
    # Check if this is a default engine
    from .reload import DEFAULTS
    default_uids = {d['uid'] for d in DEFAULTS}
    is_default = search_uid in default_uids
    
    if is_default:
        # For default engines, add to deleted list in settings
        deleted_config = wf.settings.get('deleted_defaults', '')
        deleted_defaults = set()
        if deleted_config:
            deleted_defaults = set(deleted_config.split(','))
        
        deleted_defaults.add(search_uid)
        wf.settings['deleted_defaults'] = ','.join(deleted_defaults)
        log.info('Marked default search "%s" as deleted', search_uid)
        
        # Also remove any user search file with the same UID
        search_file = os.path.join(ctx.searches_dir, search_uid + '.json')
        if os.path.exists(search_file):
            os.remove(search_file)
            log.info('Removed user search file "%s"', search_file)
        
        print(Variables(title='Default Engine Deleted', 
                       text='Default search engine has been removed'))
    else:
        # For user engines, delete the JSON file
        search_file = os.path.join(ctx.searches_dir, search_uid + '.json')
        if os.path.exists(search_file):
            os.remove(search_file)
            log.info('Deleted user search file "%s"', search_file)
            
            print(Variables(title='Engine Deleted', 
                           text='Search engine has been removed'))
        else:
            log.warning('Search file not found: %s', search_file)
            print(Variables(title='Search Not Found', 
                           text='Could not find search engine to delete'))
