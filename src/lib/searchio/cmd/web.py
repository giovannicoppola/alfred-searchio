#!/usr/bin/env python
# encoding: utf-8
#
# Copyright (c) 2017 Dean Jackson <deanishe@deanishe.net>
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2017-12-10
#

"""searchio web [<url>]

Import an OpenSearch websearch from a URL.

Usage:
    searchio web [<url>]
    searchio web -h

Options:
    -h, --help   Display this help message

"""

from __future__ import print_function, absolute_import

import json
import os
import subprocess
from urllib.parse import urlparse

from docopt import docopt
from workflow import ICON_ERROR, ICON_WARNING
from workflow.background import run_in_background, is_running

from searchio.core import Context
from searchio import util
from searchio.cmd.fetch import import_search

log = util.logger(__name__)

wf = None

# JXA script to test whether specified apps are running.
# App names are passed in ARGV; returns a {name: bool} JSON object.
JXA_RUNNING = """
function run(argv) {
    var apps = {};
    argv.forEach(function(name) {
        if (Application(name).running()) {
            apps[name] = true;
        } else {
            apps[name] = false;
        }
    });
    return JSON.stringify(apps);
}
"""

# JXA script for Safari-like browsers to get title and URL of current
# tab. Returns a JSON object.
JXA_SAFARI = """
function run(argv) {
    var doc = Application('%(appname)s').documents[0];

    return JSON.stringify({
        title: doc.name(),
        url: doc.url()
    });
}
"""

# JXA script for Chrome-like browsers to get title and URL of current
# tab. Returns a JSON object.
JXA_CHROME = """
function run(argv) {
    var tab = Application('%(appname)s').windows[0].activeTab;

    return JSON.stringify({
        title: tab.name(),
        url: tab.url()
    });
}
"""

BROWSERS = {
    # app name: (app path, JXA script)
    'Safari': ('/Applications/Safari.app', JXA_SAFARI),
    'Google Chrome': ('/Applications/Google Chrome.app', JXA_CHROME),
}


def usage(wf):
    """CLI usage instructions."""
    return __doc__


def clipboard_url():
    """Fetch URL from clipboard."""
    cmd = ['pbpaste', '-Prefer', 'txt']
    output = subprocess.check_output(cmd)
    
    # Decode the output properly, handling encoding issues
    try:
        # Try UTF-8 first
        decoded_output = output.decode('utf-8')
    except UnicodeDecodeError:
        try:
            # Fall back to latin-1 if UTF-8 fails
            decoded_output = output.decode('latin-1')
        except UnicodeDecodeError:
            # If all else fails, use error handling
            decoded_output = output.decode('utf-8', errors='ignore')
    
    # Strip whitespace and check if it looks like a URL
    decoded_output = decoded_output.strip()
    if not decoded_output or not (decoded_output.startswith('http://') or decoded_output.startswith('https://')):
        return None

    url = urlparse(decoded_output)
    if url.scheme not in ('http', 'https'):
        return None



    return decoded_output


def do_get_url(wf, args):
    """Check clipboard and browsers for a URL."""
    ctx = Context(wf)
    ICON_CLIPBOARD = ctx.icon('clipboard')

    items = []
    url = clipboard_url()
    if url:
        items.append(dict(title='Clipboard', subtitle=url, autocomplete=url,
                          icon=ICON_CLIPBOARD))

    # Browsers
    cmd = ['/usr/bin/osascript', '-l', 'JavaScript', '-e', JXA_RUNNING] + list (BROWSERS.keys())
    output = subprocess.check_output(cmd)
    running = json.loads(output)

    for name in BROWSERS:
        app, script = BROWSERS[name]
        if not running[name]:
            log.debug('"%s" not running', name)
            continue
        log.debug('fetching current tab from "%s" ...', name)

        script = script % dict(appname=name)
        cmd = ['/usr/bin/osascript', '-l', 'JavaScript', '-e', script]
        output = subprocess.check_output(cmd)
        data = json.loads(output)
        if not data:
            log.debug('no URL for "%s"', name)
            continue
        title = data['title'] or 'Untitled'
        url = data['url']
        items.append(dict(title=title, subtitle=url, autocomplete=url,
                          icon=app, icontype='fileicon'))

    if not items:
        wf.add_item('No Clipboard or Browser URL',
                    'Enter a URL or copy one to clipboard.',
                    icon=ICON_WARNING)

    for item in items:
        wf.add_item(**item)

    wf.send_feedback()


def do_import_search(wf, url):
    """Parse URL for OpenSearch config."""
    ctx = Context(wf)
    # ICON_IMPORT = ctx.icon('import')
    ICONS_PROGRESS = [
        ctx.icon('progress-1'),
        ctx.icon('progress-2'),
        ctx.icon('progress-3'),
        ctx.icon('progress-4'),
    ]

    data = wf.cached_data('import', None, max_age=0, session=True)
    
    if data:
        error = data['error']
        search = data['search']
        # Clear cache data
        wf.cache_data('import', None, session=True)
        wf.cache_data('import-status', None, session=True)

        if error:
            wf.add_item(error, icon=ICON_ERROR)
            wf.send_feedback()
            return

        it = wf.add_item(u'Add "{}"'.format(search['name']),
                         u'↩ to add search',
                         valid=True,
                         icon=search['icon'])

        for k, v in search.items():
            it.setvar(k, v)

    else:
        # Run import synchronously instead of background job
        log.debug('running import synchronously for: %s', url)
        search, error = import_search(wf, url)
        
        if error:
            wf.add_item(error, icon=ICON_ERROR)
        elif search:
            it = wf.add_item(u'Add "{}"'.format(search['name']),
                             u'↩ to add search',
                             valid=True,
                             icon=search['icon'])

            for k, v in search.items():
                it.setvar(k, v)
        else:
            wf.add_item('Import failed', 'Unknown error occurred', icon=ICON_ERROR)

    wf.send_feedback()


def run(wf, argv):
    """Run ``searchio web`` sub-command."""
    args = docopt(usage(wf), argv)
    url = args.get('<url>')
    if not url:
        return do_get_url(wf, args)

    return do_import_search(wf, url)
