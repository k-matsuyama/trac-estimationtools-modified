from trac.core import implements, Component
from trac.web.api import IRequestFilter, IRequestHandler
from trac.web.chrome import ITemplateProvider, add_script

from estimationtools.utils import EstimationToolsBase


class HoursInPlaceEditor(EstimationToolsBase):
    """A filter to implement in-place editing for estimated hours field in
    query page.
    
    Requires Trac XML-RPC Plug-in.
    """

    implements(IRequestFilter, IRequestHandler, ITemplateProvider)
    
    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info == '/estimationtools/edithours.js'

    def process_request(self, req):
        data = {'field': self.estimation_field}
        return 'edithours.html', {'data': data}, 'text/javascript'

    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        return handler
            
    def post_process_request(self, req, template, data, content_type):
        try:
            realm = data['context'].resource.realm
        except:
            realm = None
        if realm in ('query', 'report', 'wiki', 'milestone') \
                and (not 'preview' in req.args) \
                and req.perm.has_permission('TICKET_MODIFY') \
                and req.perm.has_permission('XML_RPC'):
            add_script(req, 'estimationtools/jquery.jeditable.mini.js')
            add_script(req, '/estimationtools/edithours.js')
        return template, data, content_type

    # ITemplateProvider methods
    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('estimationtools', resource_filename(__name__, 'htdocs'))]
            
    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]
