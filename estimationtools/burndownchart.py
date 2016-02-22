import copy
from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from genshi.builder import tag
from trac.core import TracError
from trac.util.text import unicode_quote, unicode_urlencode
from trac.wiki.macros import WikiMacroBase

from estimationtools.utils import parse_options, execute_query, \
                                  get_estimation_field, get_closed_states, \
                                  from_timestamp, get_serverside_charts,\
                                  EstimationToolsBase

DEFAULT_OPTIONS = {'width': '800', 'height': '200', 'color': 'ff9900',
                   'expected': '0', 'bgcolor': 'ffffff00',
                   'wecolor':'ccccccaa', 'colorexpected': 'ffddaa',
                   'weekends':'true', 'gridlines' : '0'}


class BurndownChart(EstimationToolsBase, WikiMacroBase):
    """Creates burn down chart for selected tickets.

    This macro creates a chart that can be used to visualize the progress in a milestone (e.g., sprint or
    product backlog).
    For a given set of tickets and a time frame, the remaining estimated effort is calculated.

    The macro has the following parameters:
     * a comma-separated list of query parameters for the ticket selection, in the form "key=value" as specified in TracQuery#QueryLanguage.
     * `startdate`: '''mandatory''' parameter that specifies the start date of the period (ISO8601 format)
     * `enddate`: end date of the period. If omitted, it defaults to either the milestones (if given) `completed' date,
       or `due` date, or today (in that order) (ISO8601 format)
     * `weekends`: include weekends in chart. Defaults to `true` 
     * `title`: chart title. Defaults to first milestone or 'Burndown Chart'
     * `expected`: show expected progress in chart, 0 or any number to define initial expected hours (defaults to 0).
     * `gridlines`: show gridlines in chart, 0 or any number to define hour steps (defaults to 0)
     * `width`: width of resulting diagram (defaults to 800)
     * `height`: height of resulting diagram (defaults to 200)
     * `color`: color specified as 6-letter string of hexadecimal values in the format `RRGGBB`.
       Defaults to `ff9900`, a nice orange.
     * `colorexpected`: color for expected hours graph specified as 6-letter string of hexadecimal values in the format `RRGGBB`.
       Defaults to ffddaa, a nice yellow.
     * `bgcolor`: chart drawing area background color specified as 6-letter string of hexadecimal values in the format `RRGGBB`.
       Defaults to `ffffff`.
     * `wecolor`: chart drawing area background color for weekends specified as 6-letter string of hexadecimal values in the format `RRGGBB`.
       Defaults to `ccccccaa`.

    Examples:
    {{{
        [[BurndownChart(milestone=Sprint 1, startdate=2008-01-01)]]
        [[BurndownChart(milestone=Release 3.0|Sprint 1, startdate=2008-01-01, enddate=2008-01-15,
            weekends=false, expected=100, gridlines=20, width=600, height=100, color=0000ff)]]
    }}}
    """

    closed_states = get_closed_states()
    serverside_charts = get_serverside_charts()

    def expand_macro(self, formatter, name, content):

        # prepare options
        req = formatter.req
        options, query_args = parse_options(self.env.get_db_cnx(), content,
                                            copy.copy(DEFAULT_OPTIONS))

        if not options['startdate']:
            raise TracError("No start date specified!")

        # minimum time frame is one day
        if (options['startdate'] >= options['enddate']):
            options['enddate'] = options['startdate'] + timedelta(days=1)

        # calculate data
        timetable = self._calculate_timetable(options, query_args, req)
        
        # remove weekends
        if not options['weekends']:
            for date in timetable.keys():
                if date.weekday() >= 5:
                    del timetable[date]

        # scale data
        xdata, ydata, maxhours = self._scale_data(timetable, options)

        # build html for google chart api
        dates = sorted(timetable.keys())
        bottomaxis = "0:|" + ("|").join([str(date.day) for date in dates]) + \
            "|1:|%s/%s|%s/%s" % (dates[0].month, dates[0].year,
                                 dates[ - 1].month, dates[ - 1].year)
        leftaxis = "2,0,%s" % maxhours
        
        # add line for expected progress
        if options['expected'] == '0':
            expecteddata = ""
        else:
            expecteddata = "|0,100|%s,0" % (round(Decimal(options['expected']) * 100 / maxhours, 2))

        # prepare gridlines
        if options['gridlines'] == '0':
            gridlinesdata = "100.0,100.0,1,0"  # create top and right bounding line by using grid
        else:
            gridlinesdata = "%s,%s" % (xdata[1], (round(Decimal(options['gridlines']) * 100 / maxhours, 4)))

        # mark weekends
        weekends = []
        saturday = None
        index = 0
        halfday = self._round(Decimal("0.5") / (len(dates) - 1))
        for date in dates:
            if date.weekday() == 5:
                saturday = index
            if saturday and date.weekday() == 6:
                weekends.append("R,%s,0,%s,%s" %
                                (options['wecolor'],
                                 self._round((Decimal(xdata[saturday]) / 100) - halfday),
                                 self._round((Decimal(xdata[index]) / 100) + halfday)))
                saturday = None
            index += 1
        # special handling if time period starts with Sundays...
        if len(dates) > 0 and dates[0].weekday() == 6:
            weekends.append("R,%s,0,0.0,%s" % (options['wecolor'], halfday))
        # or ends with Saturday
        if len(dates) > 0 and dates[ - 1].weekday() == 5:
            weekends.append("R,%s,0,%s,1.0" % (options['wecolor'], Decimal(1) - halfday))

        # chart title
        title = options.get('title', None)
        if title is None and options.get('milestone'):
            title = options['milestone'].split('|')[0]

        chart_args = unicode_urlencode(
                    {'chs': '%sx%s' % (options['width'], options['height']),
                     'chf': 'c,s,%s|bg,s,00000000' % options['bgcolor'],
                     'chd': 't:%s|%s%s' % (",".join(xdata), ",".join(ydata), expecteddata),
                     'cht': 'lxy',
                     'chxt': 'x,x,y',
                     'chxl': bottomaxis,
                     'chxr': leftaxis,
                     'chm': "|".join(weekends),
                     'chg': gridlinesdata,
                     'chco': '%s,%s' % (options['color'], options['colorexpected']),
                     'chtt': title})
        self.log.debug("BurndownChart data: %s" % repr(chart_args))
        if self.serverside_charts:
            return tag.image(src="%s?data=%s" % (req.href.estimationtools('chart'),
                                    unicode_quote(chart_args)),
                             alt="Burndown Chart (server)")
        else:
            return tag.image(src="http://chart.googleapis.com/chart?%s" % chart_args,
                             alt="Burndown Chart (client)")

    def _calculate_timetable(self, options, query_args, req):
        db = self.env.get_db_cnx()

        # create dictionary with entry for each day of the required time period
        timetable = {}

        current_date = options['startdate']
        while current_date <= options['enddate']:
            timetable[current_date] = Decimal(0)
            current_date += timedelta(days=1)

        # get current values for all tickets within milestone and sprints

        query_args[self.estimation_field + "!"] = None
        tickets = execute_query(self.env, req, query_args)

        # add the open effort for each ticket for each day to the timetable

        for t in tickets:

            # Record the current (latest) status and estimate, and ticket
            # creation date

            creation_date = t['time'].date()
            latest_status = t['status']
            latest_estimate = self._cast_estimate(t[self.estimation_field])
            if latest_estimate is None:
                latest_estimate = Decimal(0)

            # Fetch change history for status and effort fields for this ticket
            history_cursor = db.cursor()
            history_cursor.execute("SELECT "
                "DISTINCT c.field as field, c.time AS time, c.oldvalue as oldvalue, c.newvalue as newvalue "
                "FROM ticket t, ticket_change c "
                "WHERE t.id = %s and c.ticket = t.id and (c.field=%s or c.field='status')"
                "ORDER BY c.time ASC", [t['id'], self.estimation_field])

            # Build up two dictionaries, mapping dates when effort/status
            # changed, to the latest effort/status on that day (in case of
            # several changes on the same day). Also record the oldest known
            # effort/status, i.e. that at the time of ticket creation

            estimate_history = {}
            status_history = {}

            earliest_estimate = None
            earliest_status = None

            for row in history_cursor:
                row_field, row_time, row_old, row_new = row
                event_date = from_timestamp(row_time).date()
                if row_field == self.estimation_field:
                    new_value = self._cast_estimate(row_new)
                    if new_value is not None:
                        estimate_history[event_date] = new_value
                    if earliest_estimate is None:
                        earliest_estimate = self._cast_estimate(row_old)
                elif row_field == 'status':
                    status_history[event_date] = row_new
                    if earliest_status is None:
                        earliest_status = row_old

            # If we don't know already (i.e. the ticket effort/status was
            # not changed on the creation date), set the effort on the
            # creation date. It may be that we don't have an "earliest"
            # estimate/status, because it was never changed. In this case,
            # use the current (latest) value.

            if not creation_date in estimate_history:
                if earliest_estimate is not None:
                    estimate_history[creation_date] = earliest_estimate
                else:
                    estimate_history[creation_date] = latest_estimate
            if not creation_date in status_history:
                if earliest_status is not None:
                    status_history[creation_date] = earliest_status
                else:
                    status_history[creation_date] = latest_status

            # Finally estimates to the timetable. Treat any period where the
            # ticket was closed as estimate 0. We need to loop from ticket
            # creation date, not just from the timetable start date, since
            # it's possible that the ticket was changed between these two
            # dates.

            current_date = creation_date
            current_estimate = None
            is_open = None

            while current_date <= options['enddate']:
                if current_date in status_history:
                    is_open = (status_history[current_date] not in self.closed_states)

                if current_date in estimate_history:
                    current_estimate = estimate_history[current_date]

                if current_date >= options['startdate'] and is_open:
                    timetable[current_date] += current_estimate

                current_date += timedelta(days=1)

        return timetable

    def _scale_data(self, timetable, options):
        # create sorted list of dates
        dates = timetable.keys()
        dates.sort()

        maxhours = max(timetable.values() + [int(options.get('expected', 0))])

        if maxhours <= Decimal(0):
            maxhours = Decimal(100)
        ydata = [str(self._round(timetable[d] * Decimal(100) / maxhours))
                 for d in dates]
        xdata = [str(self._round(x * Decimal(100) / (len(dates) - 1)))
                 for x in range(len(dates))]

        # mark ydata invalid that is after today
        remaining_days = len([d for d in dates if d > options['today']])
        if remaining_days:
            ydata = ydata[: - remaining_days] + ['-1' for x in xrange(0, remaining_days)]

        return xdata, ydata, maxhours

    def _round(self, decimal_):
        return decimal_.quantize(Decimal("0.01"), ROUND_HALF_UP)

    def _cast_estimate(self, estimate):
        # Treat 0, empty string or None as 0.0
        if not estimate:
            return Decimal(0)
        try:
            return Decimal(estimate)
        except (TypeError, ValueError, InvalidOperation):
            # Treat other incorrect values as None
            return None
