#!/usr/bin/env python

from wsgiref.util import request_uri
from urlparse import urlparse

try:
    from urlparse import parse_qsl # Python >=2.6
except ImportError:
    from cgi import parse_qsl # Python <2.5

from django.template import Template, Context
from django.conf import settings
settings.configure()

from django_awesome_bot import fetch_ticket, create_git_branches_from_patches

TICKET_NUM_FORM = open("index.html").read()

def simple_app(environ, start_response):
    def make_response(content, content_type='text/html'):
        status = '200 OK'
        headers = [('Content-type', content_type)]
        start_response(status, headers)

        return [content]

    url = urlparse(request_uri(environ, include_query=1))

    if not url.query:
       return make_response(TICKET_NUM_FORM)

    query = dict(parse_qsl(url.query))

    if not query or not query.has_key('ticket'):
       return make_response(TICKET_NUM_FORM)

    t = Template(open("detail_report.html").read())
    c = Context(create_git_branches_from_patches(fetch_ticket(int(query['ticket']))))
    return make_response(str(t.render(c)))
