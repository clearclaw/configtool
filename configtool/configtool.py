#!/usr/bin/env python

import os, subprocess, sys
from time import strftime
from socket import gethostname
from optparse import OptionParser

#
# Configuration localiser
#

DEFAULT_LOCALTOOL = r"configmanage"
DEFAULT_CONFIGTOOL = r"configlocalise"
DEFAULT_TOPODIR = r"/etc/configtool/topo.d"
DEFAULT_TOPOEXTENSION = r".topo"
DEFAULT_MODULESDIR = r"/etc/configtool/modules.d"
DEFAULT_LISTFILE = os.path.join (DEFAULT_MODULESDIR, r"%s.cfgs")
TEMPLATE_EXTENSION = r".templ"
TEMPLATE_CHECK = r".check"
TEMPLATE_CHECK = r".sample"
PROCESS_STRTIME = strftime ("%Y-%m-%d-%H%M.%S")

def parse_options ():
  parser = OptionParser ()
  parser.add_option ("-w", "--localtool", action = "store", dest = "file_local",
                     help = "(Alternate) Localisation tool to use",
                     default = DEFAULT_LOCALTOOL, metavar = "FILE")
  parser.add_option ("-x", "--execute", action = "store", dest = "file_tool",
                     help = "(Alternate) Configuration tool to use",
                     default = DEFAULT_CONFIGTOOL, metavar = "FILE")
  parser.add_option ("-c", "--topodir", action = "store", dest = "topo_dir",
                     help = "(Alternate) Topology directory to use",
                     default = DEFAULT_TOPODIR, metavar = "DIR")
  parser.add_option ("-d", "--topoext", action = "store", dest = "topo_ext",
                     help = "(Alternate) Topology file extension",
                     default = DEFAULT_TOPOEXTENSION, metavar = "EXTENSION")
  parser.add_option ("-l", "--listfile", action = "store", dest = "file_list",
                     help = "(Alternate) Catalog of configuration files to localise",
                     default = None, metavar = "FILE")
  parser.add_option ("-a", "--action", action = "store", dest = "action",
                     help = "One of 'check', 'clean', 'sample', 'status' or 'write'",
                     default = None, metavar = "ACTION")
  parser.add_option ("-f", "--force", action = "store_true", default = False,
                     dest = "force",
                     help = "Write new configuration files (required for 'write')")
  parser.add_option ("-e", "--extension", action = "store", dest = "extension",
                     help = "(Alternate) Extension to use for templates",
                     default = TEMPLATE_EXTENSION, metavar = "EXTENSION")
  parser.add_option ("-m", "--module", action = "store", dest = "module",
                     help = "Module to localise for (required)",
                     metavar = "MODULE")
  parser.add_option ("-r", "--release", action = "store", dest = "release",
                     help = "(Alternate) Release of module (required)",
                     metavar = "RELEASE")
  parser.add_option ("-t", "--target", action = "store", dest = "target",
                     help = "(Alternate) Target to localise for",
                     default = gethostname (), metavar = "HOST")
  parser.add_option ("-b", "--nobackup", action = "store_true", default = False,
                     dest = "backup", help = "Disable backups of touched files")
  parser.add_option ("-v", "--verbose", action = "store_true", default = False,
                     dest = "verbose", help = "Enable verbose output")
  parser.add_option ("-q", "--quiet", action = "store_true", default = False,
                     dest = "quiet", help = "Suppress output")
  (options, args) = parser.parse_args ()
  if not options.action or options.action not in [
    "check", "clean", "sample", "status", "write"]:
    print >> sys.stderr, "ERROR: Illegal or missing action: " + options.action
    sys.exit (-1)
  if not options.action:
    print >> sys.stderr, "ERROR: Missing action."
    sys.exit (-1)
  if options.action == "write" and not options.force:
    print >> sys.stderr, "ERROR: Write action requested without --force."
    sys.exit (-1)
  if options.force and options.action != "write":
    print >> sys.stderr, "ERROR: Force is only legal with write action."
    sys.exit (-1)
  if options.action != "status":
    if not options.file_list:
      options.file_list = DEFAULT_LISTFILE % options.module
    if not os.path.isfile (options.file_list):
      print >> sys.stderr, "ERROR: List file doesn't exist: " + options.file_list
      sys.exit (-1)
    if not options.module:
      print >> sys.stderr, "ERROR: Missing module."
      sys.exit (-1)
    if not options.release:
      try:
        options.release = get_release (options.module)
        if not options.release:
          print >> sys.stderr, "ERROR: Unable to find module release."
          sys.exit (-1)
      except: # pylint: disable-msg = W0702
        print >> sys.stderr, "ERROR: Unable to find module release."
        sys.exit (-1)
    if not options.release: # RPM version lookup failed or bad version passed
      print >> sys.stderr, ("ERROR: Ambiguous version found for module: ",
                            str (options.module))
      sys.exit (-1)
  if options.file_local and not os.path.isfile (options.file_local):
    print >> sys.stderr, ("ERROR: Localisation tool doesn't exist: ",
                          options.file_tool)
    sys.exit (-1)
  if not os.path.isdir (options.topo_dir):
    print >> sys.stderr, ("ERROR: Topology directory doesn't exist: ",
                          options.topo_dir)
    sys.exit (-1)
  if options.topo_ext[0] != "." : # Safety check
    options.topo_ext = "." + options.topo_ext
  if options.extension[0] != "." : # Safety check
    options.extension = "." + options.extension
  if options.action == "status":
    if options.module:
      print >> sys.stderr, "ERROR: Can't define module for status command."
      sys.exit (-1)
  return (options, args)

def get_release (app):
  try:
    import rpm
    ts = rpm.TransactionSet ()
    entry = ts.dbMatch ()
    entry.pattern ('name', rpm.RPMMIRE_GLOB, app)
    for i in entry:
      if i['name'] == app:
        return i['version']
    print >> sys.stderr, "ERROR: Failed to find installed version of %s" % app
    return None
  except ImportError:
    import apt
    cache = apt.cache.Cache ()
    p = cache.get (app)
    if not p or not p.installed:
      print >> sys.stderr, "ERROR: Failed to find installed version of %s" % app
      return None
    try:
      return p.versions.keys ()[0]
    except: # pylint: disable-msg = W0702
      return None

def status_process (options):
  total = 0
  for f in os.listdir (DEFAULT_MODULESDIR):
    if not f.endswith (".cfgs"):
      continue
    fn = f[:-5]
    if options.verbose:
      cmd = "configtool -a check -m %s -v" % fn
    else:
      cmd = "configtool -a check -m %s" % fn
    print fn
    if options.verbose:
      print "\t", cmd, "\t(output suppressed)"
    p = subprocess.Popen (args = cmd, cwd = "/tmp")
    rc = p.wait ()
    if rc:
      total += 1
      print "\t\t", "FAILED!  Configuration is inconsistent (%d)." % rc
    else:
      print "\t\t", "Correct."
  return total

def clean_process (options):
  rc = False
  for line in open (options.file_list, "r"):
    line = line.strip ()
    if not line or line[0] == "#":
      continue
    if not options.backup and os.path.isfile (line):
      os.rename (line, "%s-backup.%s" % (line, PROCESS_STRTIME))
    else:
      try:
        os.remove (line)
      except: # pylint: disable-msg = W0702
        rc = True
  return rc

def build_command (options):
  cmd = options.file_local
  if options.file_tool != DEFAULT_CONFIGTOOL:
    cmd += " -x " + options.file_tool
  if options.topo_dir != DEFAULT_TOPODIR:
    cmd += " -c " + options.topo_dir
  if options.topo_ext != DEFAULT_TOPOEXTENSION:
    cmd += " -d " + options.topo_ext
  if options.file_list:
    cmd += " -l " + options.file_list
  if options.extension != TEMPLATE_EXTENSION:
    cmd += " -e " + options.extension
  cmd += " -m %s -r %s" % (options.module, options.release)
  if options.target != gethostname ():
    cmd += " -t " + options.target
  cmd += " -a " + options.action
  if options.force:
    cmd += " -f"
  if options.backup:
    cmd += " -b"
  if options.quiet:
    cmd += " -q"
  if options.verbose:
    cmd += " -v"
  return cmd

def main ():
  (options, args) = parse_options ()
  if options.action == "status":
    rc = status_process (options)
    if rc and not options.quiet:
      print "ERROR: %d modules have inconsistent configurations." % rc
    sys.exit (rc)
  if options.action == "clean":
    rc = clean_process (options)
    if rc and options.verbose:
      print "ERROR: Failed cleaning configuration files.  Nothing to remove?"
    sys.exit (0) # Not an error
  cmd = build_command (options)
  #if not options.quiet:
  #  print "Processing: " + options.module
  if options.verbose:
    print "\t", cmd
  try:
    rc = subprocess.call (cmd, shell = True)
    if rc < 0 and not options.quiet:
      print >> sys.stderr, "ERROR: Localisation terminated by signal: ", -rc
    #elif rc > 0 and not options.quiet:
    #  print >> sys.stderr, "ERROR: Localisation tool returned: ", rc
  except OSError, e:
    if not options.quiet:
      print >> sys.stderr, "ERROR: Execution catastrophically failed: ", e
    sys.exit (900)
  sys.exit (rc)

if __name__ == "__main__":
  main()
