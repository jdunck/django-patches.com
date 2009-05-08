#!/usr/bin/env python

import os
import sys
import git
import tempfile
import time
import xmlrpclib

DJANGO_SRC = os.path.join(os.path.dirname(__file__), 'django')
TRAC_URL = 'http://code.djangoproject.com'
TICKET_URL = 'http://code.djangoproject.com/ticket/%s'

class PatchDoesNotApplyException(Exception):
    def __init__(self, tried_dirs):
        self.tried_dirs = tried_dirs

def fetch_ticket(ticket_num):
    server = xmlrpclib.ServerProxy("http://djangorocks@code.djangoproject.com/login/xmlrpc") 

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
    try:
        patch_file = tempfile.NamedTemporaryFile()
        patch_file.write(patch['content'])
        patch_file.flush()

        if directory:
            repo.git.apply(patch_file.name, directory=directory)
        else:
            repo.git.apply(patch_file.name)

        patch['applies'] = True
        patch['applies_to_dir'] = directory

        return patch

    except git.GitCommandError, error:
        fail = PatchDoesNotApplyException({directory: error.stderr, })

        if 'No such file or directory' in error.stderr and directory == None:
            # this is a patch that was created diffing against a subdirectory,
            # let's find out, where it applies.
            affected_files = list( line.split('\t')[2] for line in repo.git.apply(patch_file.name, '--numstat').split('\n') )
            tracked_files = repo.git.ls_tree("-r", '--name-only', 'master').split('\n')

            possible_root_dirs = set()
            for tf in tracked_files:
                for af in affected_files:
                    if tf.endswith(af):
                        possible_root_dirs.add(tf[:-len(af)])

            tried_everything = fail.tried_dirs
            for possible_root_dir in possible_root_dirs:
                try:
                    return apply_patch_to_git(repo, patch, directory=possible_root_dir)
                except PatchDoesNotApplyException, doesnotapplyexception:
                    tried_everything.update(doesnotapplyexception.tried_dirs)

            raise PatchDoesNotApplyException(tried_everything)

        if 'patch does not apply' in error.stderr: # FIXME: test whether all lines contain that
            raise fail

        assert False, 'unknown error while applying patch: %s' % error.stderr

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


from couchdb.client import Server
server = Server('http://localhost:5984/')
COUCH_DB_NAME = 'django_awesome_bot'

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

def update_ticket(ticket_num):
    ticket_info = create_git_branches_from_patches(fetch_ticket(ticket_num))
    put_on_couch(ticket_num, ticket_info)
    return ticket_info

if __name__ == '__main__':
    print update_ticket(int(sys.argv[1]))

