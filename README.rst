Django patch reports
====================

This code powers http://django-patches.com, a site that attempts to automate lots of django's patch triage process.

This is what I hacked on during the EuroDjangoCon sprints '09.

Requirements
------------

To run this yourself, you need:

- git [http://git-scm.com/]
- GitPython [http://gitorious.org/git-python]
- couchdb [http://couchdb.apache.org/]
- couchdb-python [http://code.google.com/p/couchdb-python/]

and for the web part

- django [http://couchdb.apache.org/]
- djng [http://simonwillison.net/2009/May/19/djng/]
- a wsgi compatible webserver (e.g. apache [http://httpd.apache.org/] with mod_wsgi [http://code.google.com/p/modwsgi/] )

TODO
----

1. Insert patches as attachments [http://wiki.apache.org/couchdb/HTTP_Document_API#head-63e138cce0b3ffd6b2cf9a6336eb90ddf05a5afe] to couchdb
2. Implement updating the couchdb and the repo if,

  - there is a new patch,
  - a patch changes or
  - the repository changes
  - optional: a user requests an explicit update via the web page

- Implement a nice querying interface for the front page that lets people answer questions like

  "All patches, that..
  - ".. broke in the last week because of a new change in trunk"
  - ".. are broken but marked as ready for checkin"
  - ".. are flagged needs_documentation, but don't contain any"


- Expose the repository readoonly to the public (with cherry-pick instructions on the site)

  - perhaps also a mercurial clone of it

- Test the patches automatically [http://github.com/jacobian/django-buildbots/tree/master] - Eric ?:

  1. create a buildbot master, and a lot of buildbot slaves (perhaps with amazon's EC2 ? [http://djmitche.github.com/buildbot/docs/0.7.10/#On_002dDemand-_0028_0022Latent_0022_0029-Buildslaves])
  2. use the try-scheduler [http://djmitche.github.com/buildbot/docs/0.7.10/#try] to send test jobs to buildmaster (who then sends it to the slaves)
  3. push the results back to the couch
  4. test whether patches actually solve the problem they claim to solve: apply patch without tests in the patch, test, apply patch in whole, then test

- Report stuff back to trac
  - as a user account, or
  - as a javascript-injected iframe or so
