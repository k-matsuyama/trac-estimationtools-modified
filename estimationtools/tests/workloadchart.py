# -*- coding: utf-8 -*-

import unittest

from trac.test import EnvironmentStub, Mock, MockPerm
from trac.ticket.model import Ticket
from trac.web.href import Href

from estimationtools.workloadchart import WorkloadChart


class WorkloadChartTestCase(unittest.TestCase):
    
    def setUp(self):
        self.env = EnvironmentStub(default_data = True)
        self.env.config.set('ticket-custom', 'hours_remaining', 'text')
        self.env.config.set('estimation-tools', 'estimation_field', 'hours_remaining')
        self.req = Mock(href = Href('/'),
                        abs_href = Href('http://www.example.com/'),
                        locale=None,
                        perm = MockPerm(),
                        authname='anonymous',
                        tz='')
        self.formatter = Mock(req=self.req)
       
    def _insert_ticket(self, estimation, owner):
        ticket = Ticket(self.env)
        ticket['summary'] = 'Test Ticket'
        ticket['owner'] = owner
        ticket['hours_remaining'] = estimation
        ticket['milestone'] = 'milestone1'
        return ticket.insert()

    def test_basic(self):
        workload_chart = WorkloadChart(self.env)
        self._insert_ticket('10', 'A')
        self._insert_ticket('20', 'B')
        self._insert_ticket('30', 'C')
        result = workload_chart.expand_macro(self.formatter, "", "milestone=milestone1")
        # remaining days will vary if unittest is run on workday or weekend... Ignore...
        result = str(result).replace('0+workdays+left', '1+workdays+left')
        self.assertEqual(result, '<image src="http://chart.googleapis.com/chart?'
                'chd=t%3A10%2C30%2C20&amp;chf=bg%2Cs%2C00000000&amp;chco=ff9900&amp;'
                'chl=A+10h%7CC+30h%7CB+20h&amp;chs=400x100&amp;cht=p3&amp;'
                'chtt=Workload+60h+%28%7E1+workdays+left%29" alt="Workload Chart (client)"/>')

    def test_invalid_value(self):
        workload_chart = WorkloadChart(self.env)
        self._insert_ticket('10', 'A')
        self._insert_ticket('10', 'B')
        self._insert_ticket('10', 'B')
        self._insert_ticket('30', 'C')
        self._insert_ticket('xxx', 'D')
        result = workload_chart.expand_macro(self.formatter, "", "milestone=milestone1")
        # remaining days will vary if unittest is run on workday or weekend... Ignore...
        result = str(result).replace('0+workdays+left', '1+workdays+left')
        self.assertEqual(result, '<image src="http://chart.googleapis.com/chart?'
                'chd=t%3A10%2C30%2C20&amp;chf=bg%2Cs%2C00000000&amp;'
                'chco=ff9900&amp;chl=A+10h%7CC+30h%7CB+20h&amp;chs=400x100&amp;'
                'cht=p3&amp;chtt=Workload+60h+%28%7E1+workdays+left%29" alt="Workload Chart (client)"/>')

    def test_username_obfuscation(self):
        workload_chart = WorkloadChart(self.env)
        self._insert_ticket('10', 'user@example.org')
        result = workload_chart.expand_macro(self.formatter, "", "milestone=milestone1")
        self.failUnless("&amp;chl=user%40%E2%80%A6+10h&amp;" in str(result))


def suite():
    return unittest.makeSuite(WorkloadChartTestCase)


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
