import os

DJANGO_SRC = os.path.join(os.path.dirname(__file__), 'django')
TRAC_URL = 'http://code.djangoproject.com/'
TICKET_URL = 'http://code.djangoproject.com/ticket/%s'
TRAC_XMLRPC_URL = "%slogin/xmlrpc" % TRAC_URL
COUCH_DB_URL = 'http://localhost:5984/'
COUCH_DB_NAME = 'django_awesome_bot'

try:
    from local_settings import *
except ImportError:
    pass # use default settings then
