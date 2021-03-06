import urllib
import urllib2
from datetime import datetime
from time import strptime

from trac.config import Option, ListOption, BoolOption
from trac.core import TracError, Component, implements
from trac.ticket.query import Query
from trac.util.text import unicode_urlencode
from trac.web.api import IRequestHandler, RequestDone
from trac.wiki.api import parse_args

# 0.12 stores timestamps as microseconds. Pre-0.12 stores as seconds.
from trac.util.datefmt import utc
try:
    from trac.util.datefmt import from_utimestamp as from_timestamp
except ImportError:
    def from_timestamp(ts):
        return datetime.fromtimestamp(ts, utc)

AVAILABLE_OPTIONS = ['startdate', 'enddate', 'today', 'width', 'height',
                     'color', 'bgcolor', 'wecolor', 'weekends', 'gridlines',
                     'expected', 'colorexpected', 'title']


def get_estimation_field():
    return Option('estimation-tools', 'estimation_field', 'estimatedhours',
        doc="""Defines what custom field should be used to calculate
        estimation charts. Defaults to 'estimatedhours'""")

def get_totalhours_field():
    return Option('estimation-tools', 'totalhours_field', 'totalhours',
        doc="""Defines what custom field should be used to calculate
        estimation charts. Defaults to 'totalhours'""")


def get_closed_states():
    return ListOption('estimation-tools', 'closed_states', 'closed',
        doc="""Set to a comma separated list of workflow states that count
        as "closed", where the effort will be treated as zero, e.g.
        closed_states=closed,another_state. Defaults to closed.""")


def get_estimation_suffix():
    return Option('estimation-tools', 'estimation_suffix', 'h',
        doc="""Suffix used for estimations. Defaults to 'h'""")


class EstimationToolsBase(Component):
    """ Base class EstimationTools components that auto-disables if
    estimation field is not properly configured. """

    abstract = True
    estimation_field = get_estimation_field()
    totalhours_field = get_totalhours_field()

    def __init__(self, *args, **kwargs):
        if not self.env.config.has_option('ticket-custom',
                                          self.estimation_field):
            # No estimation field configured. Disable plugin and log error.
            self.log.error("EstimationTools (%s): "
                           "Estimation field not configured. "
                           "Component disabled.", self.__class__.__name__)
            self.env.disable_component(self)


def parse_options(db, content, options):
    """Parses the parameters, makes some sanity checks, and creates default values
    for missing parameters.
    """
    cursor = db.cursor()

    # check arguments
    _, parsed_options = parse_args(content, strict=False)

    options.update(parsed_options)
    today = datetime.now().date()

    startdatearg = options.get('startdate')
    if startdatearg:
        options['startdate'] = \
            datetime(*strptime(startdatearg, "%Y-%m-%d")[0:5]).date()

    enddatearg = options.get('enddate')
    options['enddate'] = None
    if enddatearg:
        options['enddate'] = \
            datetime(*strptime(enddatearg, "%Y-%m-%d")[0:5]).date()

    if not options['enddate'] and options.get('milestone'):
        # use first milestone
        milestone = options['milestone'].split('|')[0]
        # try to get end date from db
        cursor.execute("SELECT completed, due FROM milestone WHERE name = %s",
                       (milestone,))
        row = cursor.fetchone()
        if not row:
            raise TracError("Couldn't find milestone %s" % milestone)
        if row[0]:
            options['enddate'] = from_timestamp(row[0]).date()
        elif row[1]:
            due = from_timestamp(row[1]).date()
            if due >= today:
                options['enddate'] = due

    options['enddate'] = options['enddate'] or today
    options['today'] = options.get('today') or today

    if options.get('weekends'):
        options['weekends'] = parse_bool(options['weekends'] )

    # all arguments that are no key should be treated as part of the query
    query_args = {}
    for key in options.keys():
        if not key in AVAILABLE_OPTIONS:
            query_args[key] = options[key]
    return options, query_args


def execute_query(env, req, query_args):
    # set maximum number of returned tickets to 0 to get all tickets at once
    query_args['max'] = 0
    def encode(params):
        from trac.util.text import empty
        if isinstance(params, dict):
            params = params.iteritems()
        l = []
        for k, v in params:
            if v is empty:
                l.append(k)
            else:
                l.append(k + '=' + unicode(v))
        return '&'.join(l)
    query_string = encode(query_args)
    env.log.debug("query_string: %s", query_string)
    query = Query.from_string(env, query_string)

    tickets = query.execute(req)

    tickets = [t for t in tickets
               if ('TICKET_VIEW' or 'TICKET_VIEW_CC')
               in req.perm('ticket', t['id'])]

    return tickets


def parse_bool(s):
    if s is True or s is False:
        return s
    s = str(s).strip().lower()
    return not s in ['false','f','n','0','']


def urldecode(query):
    # Adapted from example on Python mailing lists
    d = {}
    a = query.split('&')
    for s in a:
        if s.find('='):
            k,v = map(urllib.unquote, s.split('='))
            try:
                d[k].append(v)
            except KeyError:
                d[k] = [v]
    return d
