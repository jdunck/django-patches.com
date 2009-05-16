#!/usr/bin/env python

from settings import COUCH_DB_URL, COUCH_DB_NAME

from couchdb.client import Server, ResourceNotFound
server = Server(COUCH_DB_URL)

if not COUCH_DB_NAME in server:
    server.create(COUCH_DB_NAME)

db = server[COUCH_DB_NAME]

def put_on_couch(ticket_num, ticket_dict):
    id = "ticket_%d" % ticket_num

    if id in db: # update then
        _ticket_dict = db[id]
        _ticket_dict.update(ticket_dict)
        ticket_dict = _ticket_dict

    db[id] = ticket_dict

def get_from_couch(ticket_num):
    id = "ticket_%d" % ticket_num
    return db[id]

class CouchQueries(object):
    DESIGN_DOCUMENT_NAME = '_design/queries'

    QUERIES = {
      'applying_patches': {
        'map': '''
          function(ticket) {
            for (var i in ticket.patches) {
              var thispatch = ticket.patches[i];
              if (thispatch.applies) {
                emit(ticket.num, {name: thispatch['name']});
              }
            }
          }
          ''',
        },
      'failing_patches': {
        'map': '''
          function(ticket) {
            for (var i in ticket.patches) {
              var thispatch = ticket.patches[i];
              if (!thispatch.applies) {
                emit(ticket.num, {name: thispatch['name']});
              }
            }
          }
          ''',
        },
      'failing_vs_breaking': {
        'map': '''
          function(ticket) {
            for (var i in ticket.patches) {
              emit([ticket.patches[i].applies, ticket.num], ticket.patches[i]);
            }
          }
          ''',
        },
    }

    def __init__(self):
        self.create_permanent_views()

    def query(self, name):
        return db.view('_view/queries/%s' % name)

    __getattr__ = query

    @classmethod
    def create_permanent_views(cls):
        try:
            doc = db[cls.DESIGN_DOCUMENT_NAME]
        except ResourceNotFound:
            doc = {'views': {}}

        if doc['views'] == cls.QUERIES:
           print "not updating permanent views"
           return # no need to update then

        print "updating permanent views"
        doc['views'] = cls.QUERIES
        db[cls.DESIGN_DOCUMENT_NAME] = doc

        # prewarm the cache
        for key in cls.QUERIES.keys():
            [x for x in cls.query(key)]

couchqueries = CouchQueries()
