#! /usr/bin/env python

from setuptools import setup, find_packages

__version__ = "unknown"

exec open ("configtool/version.py")

setup (
  name = "configtool",
  version = __version__,
  description = "Configtool configuration management suite",
  long_description = "Confgtool configuration mangement suite",
  classifiers = [],
  keywords = "",
  author = "J C Lawrence",
  author_email = "claw@kanga.nu",
  url = "http://kanga.nu/~claw/",
  license = "Creative Commons Attribution-ShareAlike 3.0 Unported",
  packages = find_packages (exclude = ["tests",]),
  package_data = {
  },
  zip_safe = True,
  install_requires = [
    "configobj",
  ],
  entry_points = {
    "console_scripts": [
      "configtool = configtool.configtool:main",
      "configmanage = configtool.configmanage:main",
      "configlocalise = configtool.configlocalise:main",
      ],
    },
  )
