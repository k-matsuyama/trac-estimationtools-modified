# -*- coding: utf-8 -*-

import unittest

from estimationtools.tests import burndownchart, hoursremaining, \
                                  workloadchart, utils


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(burndownchart.suite())
    suite.addTest(hoursremaining.suite())
    suite.addTest(workloadchart.suite())
    suite.addTest(utils.suite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
