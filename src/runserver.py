#!/usr/bin/env python

from patch_reporter.web import simple_app
from djng import serve

if __name__ == '__main__':
    serve(simple_app, '127.0.0.1', 9000)
