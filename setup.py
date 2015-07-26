#! /usr/bin/env python

try:
  import pyver # pylint: disable=W0611
except ImportError:
  import os, subprocess
  try:
    environment = os.environ.copy()
    cmd = "pip install pyver".split (" ")
    subprocess.check_call (cmd, env = environment)
  except subprocess.CalledProcessError:
    import sys
    print >> sys.stderr, "Problem installing 'pyver' dependency."
    print >> sys.stderr, "Please install pyver manually."
    sys.exit (1)
  import pyver # pylint: disable=W0611

from setuptools import setup, find_packages

__version__, __version_info__ = pyver.get_version (pkg = "configtool")

setup (
  name = "configtool",
  version = __version__,
  description = "Configtool configuration management suite",
  long_description = "Confgtool configuration mangement suite",
  classifiers = [],
  keywords = "configuration management",
  author = "J C Lawrence",
  author_email = "claw@kanga.nu",
  url = "https://github.com/clearclaw/configtool",
  license = "Creative Commons Attribution-ShareAlike 3.0 Unported",
  packages = find_packages (exclude = ["tests",]),
  package_data = {
  },
  zip_safe = True,
  install_requires = [
    "configobj",
    "logtool",
    "psver",
  ],
  entry_points = {
    "console_scripts": [
      "configtool = configtool.configtool:main",
      "configmanage = configtool.configmanage:main",
      "configlocalise = configtool.configlocalise:main",
      ],
    },
  )
