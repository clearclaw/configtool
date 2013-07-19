#!/usr/bin/env python

#
# Configuration localisation
#
# See ConfigObj documentation for format specifications for
# configuration file:
#
#   http://www.voidspace.org.uk/python/configobj.html
#
DEFAULT_TOPODIR = r"/etc/configtool/topo.d"
DEFAULT_TOPOEXTENSION = r".topo"
VARIABLE_REGEX = r"\$\{([A-Za-z0-9._]+)\}"
ESCAPED_REGEX = r"\$\{\{([A-Za-z0-9._]+)\}\}"

import itertools, re, os, socket, sys, time
from types import DictType
from optparse import OptionParser
from configobj import ConfigObj
from StringIO import StringIO
from time import strftime, time

PROCESS_STRTIME = strftime ("%Y-%m-%d-%H%M.%S")
PROCESS_UTTIME = time ()

def get_localhostname ():
  """Get the local hostname without a domain."""
  h = socket.gethostname ()
  return h.split (".")[0]

def parse_options ():
  parser = OptionParser ()
  parser.add_option ("-c", "--topodir", action="store", dest="topo_dir",
                     help="(Alternate) Topology directory to use",
                     default = DEFAULT_TOPODIR, metavar="DIR")
  parser.add_option ("-d", "--topoext", action="store", dest="topo_ext",
                     help="(Alternate) Topology file extension",
                     default = DEFAULT_TOPOEXTENSION, metavar="EXTENSION")
  parser.add_option ("-i", "--inputfile", action="store", dest="file_in",
                     help="Input file to localise (required)", metavar="FILE")
  parser.add_option ("-o", "--outputfile", action="store", dest="file_out",
                     help="Localised file to write (required)", metavar="FILE")
  parser.add_option ("-m", "--module", action="store", dest="module",
                     help="Module to localise for (required)",
                     metavar="MODULE")
  parser.add_option ("-r", "--release", action="store", dest="release",
                     help="Release of module (required)", metavar="RELEASE")
  parser.add_option ("-t", "--target", action="store", dest="target",
                     help="(Alternate) Target to localise for",
                     default = get_localhostname (), metavar="HOST")
  parser.add_option ("-b", "--nobackup", action="store_true", default=False,
                     dest="backup", help="Disable backups of touched files")
  parser.add_option ("-v", "--verbose", action="store_true", default=False,
                     dest="verbose", help="Enable verbose output")
  parser.add_option ("-q", "--quiet", action="store_true", default=False,
                     dest="quiet", help="Suppress output")
  (options, args) = parser.parse_args ()
  err = False
  if not (options.file_in and options.file_out and
          options.module and options.release):
    print >> sys.stderr, "ERROR: Missing argument(s)"
    err = True
  if not os.path.isdir (options.topo_dir):
    print >> sys.stderr, (
      "ERROR: Topology directory doesn't exist: " + options.topo_dir)
    err = True
  if not options.file_in or not os.path.isfile (options.file_in):
    print >> sys.stderr, (
      "ERROR: Input file doesn't exist: " + str (options.file_in))
    err = True
  if options.topo_ext[0] != "." : # Safety check
    options.topo_ext = "." + options.topo_ext
  if err:
    # parser.print_help ()
    sys.exit (-1)
  return (options, args)

def get_value (base, kl):
  while kl:
    k = kl.pop (0)
    if k is None:
      continue
    a = base.get (k)
    if a:
      if isinstance (a, DictType):
        base = a
        continue
      return a
  else:
    raise ValueError

def gen_indexes (s):
  for i in xrange (len (s), -1, -1):
    yield s[:i]
  raise StopIteration

def specific_value (config, options, key):
  g_host = gen_indexes (options.target)
  g_release = gen_indexes (options.release)
  for k in [options.module, "default"]:
    base = config.get (k)
    if base: # Got a module
      for i in itertools.product (g_release, g_host):
        try:
          return get_value (base, i)
        except: # pylint: disable-msg=W0702
          continue
  # Failed
  # print ("No definition for key: ${%s}\n" % key)
  if not options.quiet:
    print >> sys.stderr, "\t\t\tNo definition for variable: ${%s}" % key
  return None

def config_value (cfg_list, options, key):
  if not cfg_list or cfg_list == []:
    return None
  for c in cfg_list:
    v = specific_value (c[1], options, key)
    if v:
      return v
    # Failed
    # print ("No definition for key: %s/${%s}\n" % (c[0], key))
  if not options.quiet:
    print >> sys.stderr, "\t\t\tNo definition for variable: ${%s}" % key
  return None

def localise_file (cfg_list, options, in_file, out_file):
  reg = re.compile (VARIABLE_REGEX)
  esc = re.compile (ESCAPED_REGEX)
  rc = False
  for line in in_file:
    while True:
      m = reg.search (line)
      if not m:
        break
      # t = m.group (0) # Entire match
      k = m.group (1) # Variable name
      v = config_value (cfg_list, options, k) # Replacement token
      pattern = "%s%s%s"
      if not v: # Variable definition found
        pattern = "%s$(%s)%s"
        v = k
        rc = True
      if options.verbose:
        print "\t\t\t\tReplacing ${%s} with: %s" % (k, v)
      line = pattern % (line[:m.start(0)], v, line[m.end(0):])
    # Check for and handled escaped variables.
    m = esc.search (line)
    if m:
      # t = m.group (0) # Entire match
      k = m.group (1) # Variable name
      pattern = "%s${%s}%s"
      line = pattern % (line[:m.start(0)], k, line[m.end(0):])
    out_file.write (line)
  return rc

def load_topos (topo_dir, topo_ext = DEFAULT_TOPOEXTENSION):
  cfg_list = []
  files = os.listdir (topo_dir)
  files.sort ()
  for f in files:
    if f.endswith (topo_ext):
      c = ConfigObj (os.path.join (topo_dir, f), interpolation = False)
      cfg_list.append ((f, c))
  if cfg_list == []:
    return None
  s = StringIO (
    """[default]
         LOCAL_HOSTNAME = %s
         LOCAL_STRTIME = %s
         LOCAL_UTTIME = %d""" % (get_localhostname (),
                                 PROCESS_STRTIME,
                                 PROCESS_UTTIME))
  cfg_list.append (("<default>", ConfigObj (s, interpolation = False)))
  return cfg_list

def main ():
  (options, args) = parse_options ()
  cfg_list = load_topos (options.topo_dir, options.topo_ext)
  if not cfg_list:
    print >> sys.stderr, "ERROR: Failed to find/load any topology files."
    sys.exit (99)
  if not options.backup and os.path.isfile (options.file_out):
    os.rename (options.file_out,
               "%s-backup.%s" % (options.file_out, PROCESS_STRTIME))
  else:
    try:
      os.remove (options.file_out)
    except: # pylint: disable-msg=W0702
      pass
  rc = 0
  with open (options.file_in, "r") as in_file:
    with open (options.file_out, "w") as out_file
      rc = localise_file (cfg_list, options, in_file, out_file)
      if rc and not options.quiet:
        print >> sys.stderr, "ERROR: Failed.  Some variables were not defined."
  sys.exit (rc)

if __name__ == "__main__":
  main()
