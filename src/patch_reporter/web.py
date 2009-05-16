#!/usr/bin/env python

from wsgiref.util import request_uri
from urlparse import urlparse

try:
    from urlparse import parse_qsl # Python >=2.6
except ImportError:
    from cgi import parse_qsl # Python <2.5

from django.template.loader import render_to_string
from django.conf import settings

import os
settings.configure(
  TEMPLATE_DIRS=(os.path.join(os.path.dirname(__file__), 'templates'), ),
)

from common import get_from_couch, couchqueries

def simple_app(environ, start_response):
    def make_response(content, content_type='text/html'):
        status = '200 OK'
        headers = [('Content-type', content_type)]
        start_response(status, headers)

        return [str(content)]

    url = urlparse(request_uri(environ, include_query=1))

    if not url.query:
       return make_response(render_to_string("index.html", {'query': couchqueries}))

    query = dict(parse_qsl(url.query))

    if not query or not query.has_key('ticket'):
       return make_response(render_to_string("index.html", {'query': CouchQueries()}))

    context = get_from_couch(int(query['ticket']))
    return make_response(render_to_string("detail_report.html", context))
