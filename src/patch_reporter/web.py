#!/usr/bin/env python

from django.template.loader import render_to_string
from couch import get_from_couch, couchqueries

import djng
from django.conf import settings
import os
settings.TEMPLATE_DIRS=(os.path.join(os.path.dirname(__file__), 'templates'), )

def index(request):
    try:
        redir = djng.Response(status=301)
        redir['Location'] = '/ticket/%d' % int(request.GET['ticket'])
        return redir
    except:
        return djng.Response(render_to_string("index.html", {'query': couchqueries}))

def ticket_detail(request, num):
    context = get_from_couch(int(num))
    return djng.Response(render_to_string("detail_report.html", context))

def custom_500(request, e):
    print e
    return djng.Response('Internal server error', status=500)

simple_app = djng.ErrorWrapper(
   djng.Router(
       (r'^ticket/(\d+)$', ticket_detail),
       (r'^$', index),
   ),
   custom_404 = lambda request: djng.Response('File not found', status=404),
   custom_500 = custom_500,
)
