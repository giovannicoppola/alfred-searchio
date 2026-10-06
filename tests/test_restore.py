#!/usr/bin/env python3
# encoding: utf-8

"""Tests for restoring user searches after a workflow update (#5).

Run from the repo root with: python3 -m unittest discover tests
"""

import json
import os
import plistlib
import shutil
import subprocess
import tempfile
import unittest

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')

DDG = {
    'title': 'DuckDuckGo (US)',
    'icon': 'icons/engines/ddg.png',
    'jsonpath': '$[*].phrase',
    'keyword': 'ddg',
    'search_url': 'https://duckduckgo.com/?q={query}',
    'suggest_url': 'https://duckduckgo.com/ac/?q={query}',
}


class RestoreTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Fresh copy of the shipped workflow, as after an update
        self.wfdir = os.path.join(self.tmp, 'wf')
        shutil.copytree(SRC, self.wfdir, symlinks=True,
                        ignore=shutil.ignore_patterns('pkg', '__pycache__'))
        self.datadir = os.path.join(self.tmp, 'data')
        self.searches = os.path.join(self.datadir, 'searches')
        os.makedirs(self.searches)
        self.env = dict(os.environ,
                        alfred_workflow_bundleid='net.giovanni.alfred-searchio',
                        alfred_workflow_data=self.datadir,
                        alfred_workflow_cache=os.path.join(self.tmp, 'cache'),
                        alfred_workflow_version='9.9.9',
                        alfred_version='5.5')

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def save(self, uid, d):
        with open(os.path.join(self.searches, uid + '.json'), 'w') as fp:
            json.dump(d, fp)

    def searchio(self, *args):
        return subprocess.run(['./searchio'] + list(args), cwd=self.wfdir,
                              env=self.env, capture_output=True, text=True)

    def script_filters(self):
        with open(os.path.join(self.wfdir, 'info.plist'), 'rb') as fp:
            data = plistlib.load(fp)
        return {o['uid']: o['config'].get('keyword') for o in data['objects']
                if o['type'] == 'alfred.workflow.input.scriptfilter'}

    def restored_version(self):
        p = os.path.join(self.datadir, 'restored_version')
        if os.path.exists(p):
            with open(p) as fp:
                return fp.read()

    def test_restores_missing_search(self):
        self.save('ddg-us', DDG)
        self.assertNotIn('ddg-us', self.script_filters())

        self.searchio('config')

        self.assertEqual(self.script_filters().get('ddg-us'), 'ddg')
        self.assertEqual(self.restored_version(), '9.9.9')

    def test_no_change_when_nothing_missing(self):
        self.save('ddg-us', DDG)
        self.searchio('reload', '--if-needed')
        ip = os.path.join(self.wfdir, 'info.plist')
        mtime = os.stat(ip).st_mtime_ns

        self.searchio('reload', '--if-needed')

        self.assertEqual(os.stat(ip).st_mtime_ns, mtime)

    def test_search_without_icon(self):
        d = dict(DDG, title='Amazon (US)', keyword='az')
        del d['icon']
        self.save('amazon-us', d)
        self.save('ddg-us', DDG)

        r = self.searchio('reload', '--if-needed')

        self.assertEqual(r.returncode, 0, r.stderr)
        filters = self.script_filters()
        self.assertEqual(filters.get('amazon-us'), 'az')
        self.assertEqual(filters.get('ddg-us'), 'ddg')

    def test_plain_reload_with_search_without_icon(self):
        d = dict(DDG)
        del d['icon']
        self.save('ddg-us', d)

        r = self.searchio('reload')

        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.script_filters().get('ddg-us'), 'ddg')

    def test_broken_file_does_not_block_others(self):
        with open(os.path.join(self.searches, 'broken.json'), 'w') as fp:
            fp.write('{not json')
        self.save('no-url', {'title': 'No URL', 'keyword': 'nu'})
        self.save('ddg-us', DDG)

        r = self.searchio('reload', '--if-needed')

        self.assertEqual(r.returncode, 0, r.stderr)
        filters = self.script_filters()
        self.assertEqual(filters.get('ddg-us'), 'ddg')
        self.assertNotIn('broken', filters)
        self.assertNotIn('no-url', filters)
        self.assertEqual(self.restored_version(), '9.9.9')


if __name__ == '__main__':
    unittest.main()
