#!/usr/bin/env python

from sys import path
print path

from web import simple_app

if __name__ == '__main__':

    from wsgiref.simple_server import make_server
    httpd = make_server('', 9000, simple_app)
    print "Serving on port 9000"
    httpd.serve_forever()
