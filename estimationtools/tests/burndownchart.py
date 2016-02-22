# -*- coding: utf-8 -*-

import unittest
from decimal import Decimal
from datetime import datetime, timedelta

from genshi.builder import QName
from trac.test import EnvironmentStub, MockPerm, Mock
from trac.ticket.model import Ticket
from trac.util.datefmt import utc
from trac.web.href import Href

from estimationtools.burndownchart import BurndownChart
from estimationtools.utils import parse_options, urldecode


class BurndownChartTestCase(unittest.TestCase):
    
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
        
    def _insert_ticket(self, estimation):
        ticket = Ticket(self.env)
        ticket['summary'] = 'Test Ticket'
        ticket['hours_remaining'] = estimation
        ticket['milestone'] = 'milestone1'
        ticket['status'] = 'new'
        return ticket.insert()

    def _change_ticket_estimations(self, id, history):
        ticket = Ticket(self.env, id)
        keys = history.keys()
        keys.sort()
        for key in keys:
            ticket['hours_remaining'] = history[key]
            ticket.save_changes("me", "testing", datetime.combine(key, datetime.now(utc).timetz()))
            
    def _change_ticket_states(self, id, history):
        ticket = Ticket(self.env, id)
        keys = history.keys()
        keys.sort()
        for key in keys:
            ticket['status'] = history[key]
            ticket.save_changes("me", "testing", datetime.combine(key, datetime.now(utc).timetz()))       
            
    def _extract_query(self, image):
        """ Parses <image/> element, urldecodes the query and returns it as dict. """
        for t, v in image.attrib:
            if t == QName('src'):
                return urldecode(v.split('?')[1])
        return {}

    def test_parse_options(self):
        db = self.env.get_db_cnx()
        options, query_args = parse_options(db, "milestone=milestone1, startdate=2008-02-20, enddate=2008-02-28", {})
        self.assertNotEqual(query_args['milestone'], None)
        self.assertNotEqual(options['startdate'], None)
        self.assertNotEqual(options['enddate'], None)
        
    def test_build_empty_chart(self):
        chart = BurndownChart(self.env)
        db = self.env.get_db_cnx()
        options, query_args = parse_options(db, "milestone=milestone1, startdate=2008-02-20, enddate=2008-02-28", {})
        timetable = chart._calculate_timetable(options, query_args, self.req)
        xdata, ydata, maxhours = chart._scale_data(timetable, options)
        self.assertEqual(xdata, ['0.00', '12.50', '25.00', '37.50', '50.00', '62.50', '75.00', '87.50', '100.00'])
        self.assertEqual(ydata, ['0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00'])
        self.assertEqual(maxhours, Decimal(100))
        
    def test_build_zero_day_chart(self):
        chart = BurndownChart(self.env)
        # shouldn't throw
        chart.expand_macro(self.formatter, "", "startdate=2008-01-01, enddate=2008-01-01")
        
    def test_calculate_timetable_simple(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        options = {'today': day3, 'startdate': day1, 'enddate': day3, 'closedstates': ['closed']}
        query_args = {'milestone': "milestone1"}
        self._insert_ticket('10')
        timetable = chart._calculate_timetable(options, query_args, self.req)
        self.assertEqual(timetable, {day1: Decimal(10), day2: Decimal(10), day3: Decimal(10)})
        
    def test_calculate_timetable_without_milestone(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        options = {'today': day3, 'startdate': day1, 'enddate': day3, 'closedstates': ['closed']}
        self._insert_ticket('10')
        timetable = chart._calculate_timetable(options, {}, self.req)
        self.assertEqual(timetable, {day1: Decimal(10), day2: Decimal(10), day3: Decimal(10)})
        
    def test_calculate_timetable_with_simple_changes(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        options = {'today': day3, 'startdate': day1, 'enddate': day3, 'closedstates': ['closed']}
        query_args = {'milestone': "milestone1"}
        ticket1 = self._insert_ticket('10')
        self._change_ticket_estimations(ticket1, {day2:'5', day3:'0'})
     
        timetable = chart._calculate_timetable(options, query_args, self.req)
        self.assertEqual(timetable, {day1: Decimal(10), day2: Decimal(5), day3: Decimal(0)})
        
    def test_calculate_timetable_with_closed_ticket(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        options = {'today': day3, 'startdate': day1, 'enddate': day3, 'closedstates': ['closed']}
        query_args = {'milestone': "milestone1"}
        ticket1 = self._insert_ticket('10')
        self._change_ticket_estimations(ticket1, {day2:'5'})
        self._change_ticket_states(ticket1, {day3: 'closed'})
        timetable = chart._calculate_timetable(options, query_args, self.req)
        self.assertEqual(timetable, {day1: Decimal(10), day2: Decimal(5), day3: Decimal(0)})

    def test_calculate_timetable_with_closed_ticket2(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        options = {'today': day3, 'startdate': day1, 'enddate': day3, 'closedstates': ['closed']}
        query_args = {'milestone': "milestone1"}
        ticket1 = self._insert_ticket('10')
        self._change_ticket_states(ticket1, {day2: 'closed'})
        self._change_ticket_estimations(ticket1, {day3:'5'})
        timetable = chart._calculate_timetable(options, query_args, self.req)
        self.assertEqual(timetable, {day1: Decimal(10), day2: Decimal(0), day3: Decimal(0)})

    def test_calculate_timetable_with_closed_and_reopened_ticket(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        day4 = day3 + timedelta(days=1)
        options = {'today': day4, 'startdate': day1, 'enddate': day4, 'closedstates': ['closed']}
        query_args = {'milestone': "milestone1"}
        ticket1 = self._insert_ticket('10')
        self._change_ticket_estimations(ticket1, {day3:'5'})
        self._change_ticket_states(ticket1, {day2: 'closed', day4: 'new'})
        timetable = chart._calculate_timetable(options, query_args, self.req)
        self.assertEqual(timetable, {day1: Decimal(10), day2: Decimal(0), day3: Decimal(0), day4: Decimal(5)})
        
    def test_calculate_timetable_with_simple_changes_2(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        options = {'today': day3, 'startdate': day1, 'enddate': day3, 'closedstates': ['closed']}
        query_args = {'milestone': "milestone1"}
        ticket1 = self._insert_ticket('10')
        self._change_ticket_estimations(ticket1, {day2:'5', day3:''})
        ticket2 = self._insert_ticket('0')
        self._change_ticket_estimations(ticket2, {day2:'1', day3:'2'})
     
        timetable = chart._calculate_timetable(options, query_args, self.req)
        self.assertEqual(timetable, {day1: Decimal(10), day2: Decimal(6), day3: Decimal(2)})

    def test_calculate_timetable_with_recent_changes(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        day4 = day3 + timedelta(days=1)
        options = {'today': day3, 'startdate': day1, 'enddate': day3, 'closedstates': ['closed']}
        query_args = {'milestone': "milestone1"}
        ticket1 = self._insert_ticket('10')
        self._change_ticket_estimations(ticket1, {day2:'5', day4:''})
     
        timetable = chart._calculate_timetable(options, query_args, self.req)
        self.assertEqual(timetable, {day1: Decimal(10), day2: Decimal(5), day3: Decimal(5)})
    
    def test_calculate_timetable_with_gibberish_estimates(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        options = {'today': day3, 'startdate': day1, 'enddate': day3, 'closedstates': ['closed']}
        query_args = {'milestone': "milestone1"}
        ticket1 = self._insert_ticket('10')
        self._change_ticket_estimations(ticket1, {day2: 'IGNOREME', day3:'5'})
        timetable = chart._calculate_timetable(options, query_args, self.req)
        self.assertEqual(timetable, {day1: Decimal(10), day2: Decimal(10), day3: Decimal(5)})

    def test_url_encode(self):
        start = datetime.now(utc).date()
        end = (start + timedelta(days=5)).strftime('%Y-%m-%d')
        start = start.strftime('%Y-%m-%d')
        chart = BurndownChart(self.env)
        t = Ticket(self.env, self._insert_ticket('12'))
        result = chart.expand_macro(self.formatter, 'BurndownChart',
                        "milestone=milestone1, startdate=%s, enddate=%s" % (start, end))
        self.failUnless("&amp;chtt=milestone1&amp;" in str(result))
        result = chart.expand_macro(self.formatter, 'BurndownChart',
                        "milestone=One & Two, startdate=%s, enddate=%s" % (start, end))
        self.failUnless("&amp;chtt=One+%26+Two&amp;" in str(result))

    def test_url_encode_parenthesis(self):
        # http://trac-hacks.org/ticket/8299
        start = (datetime.now(utc).date() - timedelta(days=1)).strftime('%Y-%m-%d')
        end = (datetime.now(utc).date() + timedelta(days=1)).strftime('%Y-%m-%d')
        chart = BurndownChart(self.env)
        def verify_milestone(milestone):
            t = Ticket(self.env, self._insert_ticket('12'))
            t['milestone'] = milestone
            t.save_changes('', '')
            result = chart.expand_macro(self.formatter, 'BurndownChart',
                        "milestone=%s, startdate=%s, enddate=%s" \
                        % (milestone, start, end))
            args = self._extract_query(result)
            # data
            self.assertEquals((milestone, args['chd']),
                              (milestone, [u't:0.00,50.00,100.00|0.00,100.00,-1']))
            # scaling / axis
            self.assertEquals((milestone, args['chxr']), (milestone, [u'2,0,12']))
            # title
            self.assertEquals(args['chtt'], [milestone])
        verify_milestone('Test')
        verify_milestone('T(es)t')
        verify_milestone('(Test)')

    def test_expected_y_axis(self):
        start = datetime.now(utc).date()
        end = (start + timedelta(days=5)).strftime('%Y-%m-%d')
        start = start.strftime('%Y-%m-%d')
        chart = BurndownChart(self.env)
        t = Ticket(self.env, self._insert_ticket('12'))
        # Test without expected
        result = chart.expand_macro(self.formatter, 'BurndownChart',
                        "startdate=%s, enddate=%s" % (start, end))
        self.assertEquals(self._extract_query(result)['chxr'], [u'2,0,12'])
        # Confirm Y axis changes with new higher expected
        result = chart.expand_macro(self.formatter, 'BurndownChart',
                        "startdate=%s, enddate=%s, expected=200" % (start, end))
        self.assertEquals(self._extract_query(result)['chxr'], [u'2,0,200'])

    def test_scale_weekends(self):
        chart = BurndownChart(self.env)
        # 7 days, monday -> sunday this week
        now = datetime.now(utc).date()
        day1 = now - timedelta(days=now.weekday())
        day2 = day1 + timedelta(days=1)
        day3 = day1 + timedelta(days=2)
        day4 = day1 + timedelta(days=3)
        day5 = day1 + timedelta(days=4)
        day6 = day1 + timedelta(days=5)
        day7 = day1 + timedelta(days=6)
        options = {'startdate': day1, 'enddate': day7, 'today': day7}
        timetable = {day1: Decimal(70), day2: Decimal(60), day3: Decimal(50),
                day4: Decimal(40), day5: Decimal(30), day6: Decimal(20),
                day7: Decimal(10)}
        self.assertEquals(chart._scale_data(timetable, options),
               (['0.00', '16.67', '33.33', '50.00', '66.67', '83.33', '100.00'],
                ['100.00', '85.71', '71.43', '57.14', '42.86', '28.57', '14.29'],
                Decimal('70')))

    def test_scale_no_weekends(self):
        chart = BurndownChart(self.env)
        # 7 days, monday -> friday this week
        now = datetime.now(utc).date()
        day1 = now - timedelta(days=now.weekday())
        day2 = day1 + timedelta(days=1)
        day3 = day1 + timedelta(days=2)
        day4 = day1 + timedelta(days=3)
        day5 = day1 + timedelta(days=4)
        day6 = day1 + timedelta(days=5)
        day7 = day1 + timedelta(days=6)
        options = {'startdate': day1, 'enddate': day7, 'today': day7}
        # no weekends option, so day6 and day7 not included
        timetable = {day1: Decimal(70), day2: Decimal(60), day3: Decimal(50),
                day4: Decimal(40), day5: Decimal(30)}
        self.assertEquals(chart._scale_data(timetable, options),
               (['0.00', '25.00', '50.00', '75.00', '100.00'],
                ['100.00', '85.71', '71.43', '57.14', '42.86'],
                Decimal('70')))


def suite():
    return unittest.makeSuite(BurndownChartTestCase)


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
