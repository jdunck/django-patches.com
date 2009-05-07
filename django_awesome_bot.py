#!/usr/bin/env python

import os
import sys
import urllib2
import BeautifulSoup
import commands
from optparse import OptionParser
from urlparse import urljoin
import subprocess
import git
import tempfile
import time

DJANGO_SRC = os.path.join(os.path.dirname(__file__), 'django')
TRAC_URL = 'http://code.djangoproject.com'
TICKET_URL = 'http://code.djangoproject.com/ticket/%s'

class PatchDoesNotApplyException(Exception):
    pass

def fetch_ticket(ticket_num):
    soup = BeautifulSoup.BeautifulSoup(urllib2.urlopen(TICKET_URL % ticket_num).read())

    links = soup.findAll('a', title="View attachment")

    patches = {}

    for link in links:
      patches[link.string] = {
        'content': urllib2.urlopen(urljoin(TICKET_URL, link['href'] + '?format=raw')).read(),
        'name': link.string,
      }

    return {
      'patches': patches,
      'title': soup.find('title').find(text=True),
      'num': ticket_num,
    }

def apply_patch_to_git(repo, patch, directory=None):
    try:
        patch_file = tempfile.NamedTemporaryFile()
        patch_file.write(patch['content'])
        patch_file.flush()
        if directory:
            repo.git.apply(patch_file.name, directory=directory)
        else:
            repo.git.apply(patch_file.name)
        return patch

    except git.GitCommandError, error:
        if 'No such file or directory' in error.stderr and directory == None:
            print "PATCH is not against the root dir, trying to figure out where it does apply"

            # this is a patch that was created diffing against a subdirectory,
            # let's find out, where it applies.
            affected_files = list( line.split('\t')[2] for line in repo.git.apply(patch_file.name, '--numstat').split('\n') )
            tracked_files = repo.git.ls_tree("-r", '--name-only', 'master').split('\n')

            possible_root_dirs = set()
            for tf in tracked_files:
                for af in affected_files:
                    if tf.endswith(af):
                        possible_root_dirs.add(tf[:-len(af)])

            for possible_root_dir in possible_root_dirs:
                print "test", possible_root_dir
                try:
                    return apply_patch_to_git(repo, patch, directory=possible_root_dir)
                except PatchDoesNotApplyException, doesnotapplyexception:
                    print "does not apply against", possible_root_dir, doesnotapplyexception.args
                    pass # didn't guess right

            raise PatchDoesNotApplyException(error.stderr)

        if 'patch does not apply' in error.stderr: # FIXME: test whether all lines contain that
            raise PatchDoesNotApplyException(error.stderr)

        assert False, 'unknown error while applying patch'

    finally:
        patch_file.close()

def create_git_branches_from_patches(ticket_dict, branch_prefix='triage/'):
    # prepare repo
    repo = git.Repo(DJANGO_SRC)

    for name, patch in ticket_dict['patches'].items():
        patch['applies'] = False

        repo.git.reset("--hard", "master")

        try:
            patch = apply_patch_to_git(repo, patch)
        except PatchDoesNotApplyException, doesnotapplyexception:
            continue

        try:
            repo.git.checkout("master", b="%s%s/%s" % (branch_prefix, time.time(), name))

            message_file = tempfile.NamedTemporaryFile()
            message_file.write('%(num)d: %(name)s' % {'num': ticket_dict['num'], 'name': name, })
            message_file.flush()

            repo.git.add("--update")
            repo.git.commit("-F", message_file.name)
        except git.GitCommandError, error:
            assert False, (error, error.stderr, )
        finally:
            message_file.close()
            repo.git.checkout("master")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Please provide a ticket number", sys.argv
        sys.exit()

    ticket_num = sys.argv[1]

    patches = fetch_ticket(int(ticket_num))
    create_git_branches_from_patches(patches)

