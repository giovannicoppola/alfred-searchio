#!/usr/bin/env python
# encoding: utf-8
#
# Copyright (c) 2016 Dean Jackson <deanishe@deanishe.net>
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2016-12-17
#

"""searchio add [options] <title> <url>

Display help message for command(s).

Usage:
    searchio add [-s <url>] [-i <path>] [-j <jpath>] [-u <uid>] [-p] <keyword> <title> <url>
    searchio add --env
    searchio add -h

Options:
    -e, --env                  Read input from environment variables
    -i, --icon <path>          Path of icon for search
    -j, --json-path <jpath>    JSON path for results
    -p, --pcencode             Whether to percent-encode query
    -s, --suggest <url>        URL for suggestions
    -u, --uid <uid>            Search UID
    -h, --help                 Display this help message
"""

from __future__ import print_function, absolute_import

import json
import os
import plistlib

from docopt import docopt
from workflow.notify import notify

from searchio.core import Context
from searchio import engines
from searchio import util
from searchio.cmd.reload import remove_script_filters, add_script_filters, Search, link_icons

log = util.logger(__name__)


def usage(wf=None):
    """CLI usage instructions."""
    return __doc__


def parse_args(wf, args):
    """Build search `dict` from `docopt` ``args``.

    Args:
        wf (workflow.Workflow3): Current workflow
        args (docopt.Args): Arguments returned by `docopt`

    Returns:
        searchio.engines.Search: Search object

    """
    params = [
        # search dict key | envvar name | CLI option | default
        ('keyword', 'keyword', '<keyword>', ''),
        ('uid', 'uid', '--uid', util.uuid()),
        ('pcencode', 'pcencode', '--pcencode', False),
        ('title', 'title', '<title>', ''),
        ('search_url', 'search_url', '<url>', ''),
        ('suggest_url', 'suggest_url', '--suggest', ''),
        ('icon', 'icon', '--icon', ''),
        ('jsonpath', 'jsonpath', '--json-path', '[1]'),
    ]

    d = {}
    for k, kenv, opt, default in params:
        if args.get('--env'):
            v = os.getenv(kenv, default)
            if default in (True, False):
                if v == '1':
                    v = True
                else:
                    v = False
        else:
            v = args.get(opt) or default

        if default not in (True, False):
            v = wf.decode(v).strip()

        d[k] = v

    return d


def run(wf, argv):
    """Run ``searchio add`` sub-command."""
    args = docopt(usage(wf), argv)
    ctx = Context(wf)
    d = parse_args(wf, args)

    # Auto-generate icon path if not provided
    if not d.get('icon'):
        # Extract engine name from title (e.g., "Amazon United States" -> "amazon")
        engine_name = d.get('title', '').split()[0].lower()
        d['icon'] = f'icons/engines/{engine_name}.png'
        log.info(f"Auto-generated icon path: {d['icon']}")
    
    s = engines.Search.from_dict(d)

    if not util.valid_url(d['search_url']):
        raise ValueError('Invalid search URL: {!r}'.format(d['search_url']))

    if d['suggest_url'] and not util.valid_url(d['suggest_url']):
        raise ValueError('Invalid suggest URL: {!r}'.format(d['suggest_url']))

    p = ctx.search(s.uid)

    with open(p, 'w') as fp:
        json.dump(s.dict, fp, sort_keys=True, indent=2)

    log.debug('Adding new search to info.plist ...')
    
    # Update info.plist to include the new search
    ip = wf.workflowfile('info.plist')
    with open(ip, "rb") as file:
        data = plistlib.load(file)
    
    # Get all existing searches (both user and default)
    existing_searches = []
    
    # First, load default searches
    from .reload import DEFAULTS
    for default_data in DEFAULTS:
        existing_searches.append(Search.from_dict(default_data))
    
    # Then, load user searches (these will override defaults if same UID)
    searches_dir = wf.datadir + '/searches'
    if os.path.exists(searches_dir):
        for filename in os.listdir(searches_dir):
            if filename.endswith('.json'):
                search_id = filename[:-5]  # Remove .json extension
                search_path = os.path.join(searches_dir, filename)
                try:
                    with open(search_path, 'r') as f:
                        content = f.read().strip()
                        if not content:  # Skip empty files
                            log.warning(f"Skipping empty search file: {search_id}")
                            continue
                        search_data = json.loads(content)
                        search_data['uid'] = search_id
                        
                        # Auto-generate icon path if not provided
                        if not search_data.get('icon'):
                            engine_name = search_data.get('title', '').split()[0].lower()
                            search_data['icon'] = f'icons/engines/{engine_name}.png'
                            log.info(f"Auto-generated icon path for existing search {search_id}: {search_data['icon']}")
                        
                        # Remove any existing search with same UID (to allow override)
                        existing_searches = [s for s in existing_searches if s.uid != search_id]
                        existing_searches.append(Search.from_dict(search_data))
                except Exception as e:
                    log.warning(f"Failed to load search {search_id}: {e}")
                    # Remove corrupted file
                    try:
                        os.remove(search_path)
                        log.info(f"Removed corrupted search file: {search_id}")
                    except:
                        pass
    
    # Add the new search to the list
    existing_searches.append(s)
    
    # Update info.plist with all searches
    remove_script_filters(wf, data)
    add_script_filters(wf, data, existing_searches)
    
    with open(ip, "wb") as file:
        plistlib.dump(data, file)
    
    # Create symlinks for Script Filter icons
    link_icons(wf, existing_searches)
    
    log.info(f"Successfully added search: {s.title} ({s.uid})")
