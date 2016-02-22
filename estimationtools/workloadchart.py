import copy
import random
from datetime import timedelta

from genshi.builder import tag
from trac.util.text import unicode_quote, unicode_urlencode, \
                           obfuscate_email_address
from trac.util.presentation import to_json
from trac.wiki.macros import WikiMacroBase

from estimationtools.utils import parse_options, execute_query, \
                                  get_estimation_suffix, get_closed_states, \
                                  EstimationToolsBase

DEFAULT_OPTIONS = {'width': '400', 'height': '150'}


class WorkloadChart(EstimationToolsBase, WikiMacroBase):
    """Creates workload chart for the selected tickets.

    This macro creates a pie chart that shows the remaining estimated workload per ticket owner,
    and the remaining work days.
    It has the following parameters:
     * a comma-separated list of query parameters for the ticket selection, in the form "key=value" as specified in TracQuery#QueryLanguage.
     * `width`: width of resulting diagram (defaults to 400)
     * `height`: height of resulting diagram (defaults to 150)

    Examples:
    {{{
        [[WorkloadChart(milestone=Sprint 1)]]
        [[WorkloadChart(milestone=Sprint 1, width=600, height=100)]]
    }}}
    """

    estimation_suffix = get_estimation_suffix()
    closed_states = get_closed_states()

    def expand_macro(self, formatter, name, content):
        req = formatter.req
        db = self.env.get_db_cnx()
        # prepare options
        options, query_args = parse_options(db, content, copy.copy(DEFAULT_OPTIONS))

        query_args[self.estimation_field + "!"] = None
        query_args['col'] = '|'.join([self.totalhours_field, 'owner'])
        tickets = execute_query(self.env, req, query_args)

        sum = 0.0
        estimations = {}
        for ticket in tickets:
            if ticket['status'] in self.closed_states:
                continue
            try:
                estimation = float(ticket[self.estimation_field]) - float(ticket[self.totalhours_field])
                owner = ticket['owner']
                sum += estimation
                if estimations.has_key(owner):
                    estimations[owner] += estimation
                else:
                    estimations[owner] = estimation
            except:
                pass

        data = []
        data.append(['Owner', 'Workload'])

        for owner, estimation in estimations.iteritems():
            estimation = max(0, estimation)
            label = "%s %g%s" % (obfuscate_email_address(owner),
                            round(estimation, 2),
                            self.estimation_suffix)
            data.append([label, float(estimation)])

        # Title
        title = 'Workload'

        # calculate remaining work time
        if options.get('today') and options.get('enddate'):
            currentdate = options['today']
            day = timedelta(days=1)
            days_remaining = 0
            while currentdate <= options['enddate']:
                if currentdate.weekday() < 5:
                    days_remaining += 1
                currentdate += day
            title += ' %g%s (~%s workdays left)' % (round(sum, 2),
                                    self.estimation_suffix, days_remaining)

        element_id = 'chart-%d' % random.randint(0, 0xffffffff)
        args = {
            'containerId': element_id,
            'chartType': 'PieChart',
            'options': {
                'width': int(options['width']),
                'height': int(options['height']),
                'title': title,
                'legend': { 'position': 'labeled' },
                'pieSliceText': 'none',
                'tooltip': 'percentage',
            },
        }
        script = "EstimationCharts.push(function() {\n"
        script += 'var data=' + to_json(data) + ";\n"
        script += 'var args=' + to_json(args) + ";\n"
        script += 'DrawWorkloadChart(data, args);'
        script += '});'

        return tag.div(tag.div(id=element_id), tag.script(script))
