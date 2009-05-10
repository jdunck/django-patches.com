#!/usr/bin/env python

import os
import sys
import git
import tempfile
import time
import xmlrpclib

from settings import DJANGO_SRC, TRAC_URL, TICKET_URL,\
                     TRAC_XMLRPC_URL, COUCH_DB_URL, COUCH_DB_NAME

class PatchDoesNotApplyException(Exception):
    def __init__(self, tried_dirs):
        self.tried_dirs = tried_dirs

class PatchAlreadyApplied(PatchDoesNotApplyException):
    pass

def fetch_ticket(ticket_num):
    server = xmlrpclib.ServerProxy(TRAC_XMLRPC_URL)
    links =  server.ticket.listAttachments(ticket_num)

    patches = []
    for filename, description, size, timestamp, user in links:
      patches.append({
        'content': server.ticket.getAttachment(ticket_num, filename).data,
        'name': filename,
        'description': description,
        'timestamp': timestamp,
        'user': user,
      })

    num, somedate, somedate2, ticket_info = server.ticket.get(ticket_num)

    ticket_info.update({
      'num': ticket_num,
      'somedate': somedate,
      'somedate2': somedate2,
      'patches': patches,
    })

    return ticket_info

def apply_patch_to_git(repo, patch, directory=None):
    patch_file = tempfile.NamedTemporaryFile()
    patch_file.write(patch['content'])
    patch_file.flush()

    try:
        if directory:
            repo.git.apply(patch_file.name, '--index', directory=directory, )
        else:
            repo.git.apply(patch_file.name, '--index', )

        patch['applies'] = True
        patch['applies_to_dir'] = directory

        return patch

    except git.GitCommandError, error:
        fail = PatchDoesNotApplyException({directory: error.stderr, })

        if 'does not exist in index' in error.stderr:
            # this is a patch that was created diffing against a subdirectory,
            # let's find out, where it applies.
            if directory: raise fail

            affected_files = list( line.split('\t')[2] for line in repo.git.apply(patch_file.name, '--numstat').split('\n') )
            tracked_files = repo.git.ls_tree("-r", '--name-only', 'master').split('\n')

            possible_root_dirs = set()
            for tf in tracked_files:
                for af in affected_files:
                    if tf.endswith(af):
                        common_path = tf[:-len(af)]
                        if common_path:
                            possible_root_dirs.add(common_path)

            tried_everything = fail.tried_dirs
            for possible_root_dir in possible_root_dirs:
                assert possible_root_dir, ("FAIL", affected_files, possible_root_dirs)
                try:
                    return apply_patch_to_git(repo, patch, directory=possible_root_dir)
                except PatchDoesNotApplyException, doesnotapplyexception:
                    tried_everything.update(doesnotapplyexception.tried_dirs)

            raise PatchDoesNotApplyException(tried_everything)

        if error.stderr == 'error: No changes':
            raise fail # FIXME: should raise PatchAlreadyApplied

        if 'patch does not apply' in error.stderr: # FIXME: test whether all lines contain that
            raise fail
        elif 'corrupt patch at' in error.stderr:
            raise fail
        elif 'already exists in working directory' in error.stderr:
            raise fail
        elif 'patch fragment without header at line' in error.stderr:
            raise fail

        assert False, 'unknown error while applying patch: >>%s<<' % error.stderr

    finally:
        patch_file.close()

def create_git_branches_from_patches(ticket_dict, branch_prefix='triage/'):
    # prepare repo
    repo = git.Repo(DJANGO_SRC)

    for patch in ticket_dict['patches']:

        repo.git.reset("--hard", "master")

        try:
            patch = apply_patch_to_git(repo, patch)
        except PatchDoesNotApplyException, doesnotapplyexception:
            patch['applies'] = False
            patch['tried_applying_to_dir'] = doesnotapplyexception.tried_dirs
            continue

        try:
            repo.git.checkout("master", b="%s%s/%s" % (branch_prefix, time.time(), patch['name']))

            message_file = tempfile.NamedTemporaryFile()
            message_file.write('%(num)d: %(name)s' % {'num': ticket_dict['num'], 'name': patch['name'], })
            message_file.flush()

            repo.git.add("--update")
            repo.git.commit("-F", message_file.name)
        except git.GitCommandError, error:
            assert False, (error, error.stderr, )
        finally:
            message_file.close()
            repo.git.checkout("master")

    return ticket_dict


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
              if (ticket.patches[i].applies) {
                emit(ticket.num, ticket.patches[i]);
              }
            }
          }
          ''',
        },
      'failing_patches': {
        'map': '''
          function(ticket) {
            for (var i in ticket.patches) {
              if (!ticket.patches[i].applies) {
                emit(ticket.num, ticket.patches[i]);
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

    def __getattr__(self, name):
        return db.view('_view/queries/%s' % name)

    @classmethod
    def create_permanent_views(cls):
        try:
            doc = db[cls.DESIGN_DOCUMENT_NAME]
        except ResourceNotFound:
            doc = {}

        doc['views'] = cls.QUERIES
        db[cls.DESIGN_DOCUMENT_NAME] = doc

CouchQueries.create_permanent_views()

def update_ticket(ticket_num):
    ticket_info = create_git_branches_from_patches(fetch_ticket(ticket_num))
    try:
        put_on_couch(ticket_num, ticket_info)
    except UnicodeDecodeError:
        pass # FIXME: put as attachement then
    return ticket_info

if __name__ == '__main__':
    print update_ticket(int(sys.argv[1]))

