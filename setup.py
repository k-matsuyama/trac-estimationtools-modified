#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-


import sys
from setuptools import setup
from pkg_resources import parse_version


name = 'EstimationTools'
version = '0.4.7'
min_trac = '0.11.3'
try:
    import trac
    if parse_version(trac.__version__) < parse_version(min_trac):
        print "%s %s requires Trac >= %s" % (name, version, min_trac)
        sys.exit(1)
except ImportError:
    pass

setup(
    name = name,
    author = 'Joachim Hoessler',
    author_email = 'hoessler@gmail.com',
    description = 'Trac plugin for visualizing and quick editing of effort estimations',
    version = version,
    license='BSD',
    packages=['estimationtools'],
    package_data = { 'estimationtools': ['htdocs/*.js', 'templates/*.html'] },
    entry_points = {
        'trac.plugins': [
            'estimationtools = estimationtools'
        ]
    },
    test_suite = 'estimationtools.tests.test_suite',
    tests_require = []
)
