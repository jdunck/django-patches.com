#!/usr/bin/env python

from web import simple_app
from flup.server.fcgi import WSGIServer

if __name__ == '__main__':
    WSGIServer(simple_app).run()
