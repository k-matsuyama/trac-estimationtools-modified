# -*- coding: utf-8 -*-

import unittest

from trac.test import EnvironmentStub, Mock, MockPerm
from trac.ticket.model import Ticket
from trac.web.href import Href

from estimationtools.hoursremaining import HoursRemaining


class HoursRemainingTestCase(unittest.TestCase):
    
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
       
    def _insert_ticket(self, estimation, fields=None):
        fields = fields or {}
        ticket = Ticket(self.env)
        ticket['summary'] = 'Test Ticket'
        ticket['hours_remaining'] = estimation
        ticket['milestone'] = 'milestone1'
        ticket['status'] = 'open'
        for field, value in fields.items():
            ticket[field] = value
        ticket.insert()
        return ticket

    def test_basic(self):
        hoursRemaining = HoursRemaining(self.env)
        self._insert_ticket('10')
        self._insert_ticket('20')
        self._insert_ticket('30')
        result = hoursRemaining.expand_macro(self.formatter, "", "milestone=milestone1")
        self.assertEqual(result, '60')

    def test_real(self):
        hoursRemaining = HoursRemaining(self.env)
        self._insert_ticket('10')
        self._insert_ticket('20.1')
        self._insert_ticket('30')
        result = hoursRemaining.expand_macro(self.formatter, "", "milestone=milestone1")
        self.assertEqual(result, '60.1')

    def test_invalid(self):
        hoursRemaining = HoursRemaining(self.env)
        self._insert_ticket('10')
        self._insert_ticket('20')
        self._insert_ticket('30')
        self._insert_ticket('xxx')
        result = hoursRemaining.expand_macro(self.formatter, "", "milestone=milestone1")
        self.assertEqual(result, '60')

    def test_closed_tickets(self):
        hoursRemaining = HoursRemaining(self.env)
        self._insert_ticket('10')
        self._insert_ticket('20.1')
        self._insert_ticket('30')
        self._insert_ticket('30', fields={'status': 'closed'})
        result = hoursRemaining.expand_macro(self.formatter, "", "status!=closed, milestone=milestone1")
        self.assertEqual(result, '60.1')

    def test_to_many_tickets(self):
        hoursRemaining = HoursRemaining(self.env)
        for _ in range(200):
            self._insert_ticket('1')
        result = hoursRemaining.expand_macro(self.formatter, "", "milestone=milestone1")
        self.assertEqual(result, '200')

    def test_url_encode(self):
        hoursRemaining = HoursRemaining(self.env)
        self._insert_ticket('10', fields={'summary': 'Test#One'})
        result = hoursRemaining.expand_macro(self.formatter, "", "summary=Test#One")
        self.assertEquals(result, '10')


def suite():
    return unittest.makeSuite(HoursRemainingTestCase)


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
