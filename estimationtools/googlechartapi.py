from trac.core import Component, implements
from trac.web.api import IRequestFilter
from trac.web.chrome import add_script

class GoogleChartApi(Component):
    implements(IRequestFilter)

    def pre_process_request(self, req, handler):
	return handler

    def post_process_request(self, req, template, data, content_type):
	add_script(req, 'https://www.google.com/jsapi')
	add_script(req, 'estimationtools/googlechart.js')
	return template, data, content_type
