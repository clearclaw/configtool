#! /usr/bin/env python

import logging, pkg_resources, subprocess

LOG = logging.getLogger (__name__)
DEFAULT_GITCMD = "git describe --long --tags --match [0-9]*.[0-9]* --dirty"

def get_version ():
  try:
    o = subprocess.check_output (
      DEFAULT_GITCMD.split (),
      stderr = subprocess.PIPE,
      shell = False).decode ().strip ()
    s = o.replace ("-", ".", 1)
    return s, tuple (s.split ("."))
  except: # pylint: disable-msg=W0702
    # Likely not in a Git repo -- either way, punt
    s = pkg_resources.get_distribution (__name__.split (".")[0]).version
    return s, tuple (s.split ("."))

__all__ = ("__version__", "__version_info__")
__version__,  __version_info__ = get_version ()
