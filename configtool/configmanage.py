#!/usr/bin/env python

#
# Configuration localiser
#

DEFAULT_CONFIGTOOL = r"configlocalise"
DEFAULT_TOPODIR = r"/etc/configtool/topo.d"
DEFAULT_TOPOEXTENSION = r".topo"
DEFAULT_LISTFILE = r"/etc/configtool/modules.d/%s.cfgs"
TEMPLATE_EXTENSION = r".templ"
TEMPLATE_CHECK = r".check"
TEMPLATE_SAMPLE = r".sample"

import os, socket, subprocess, sys
from optparse import OptionParser

def parse_options ():
  parser = OptionParser ()
  parser.add_option ("-x", "--execute", action="store", dest="file_tool",
                     help="(Alternate) Configuration tool to use",
                     default = DEFAULT_CONFIGTOOL, metavar="FILE")
  parser.add_option ("-c", "--topodir", action="store", dest="topo_dir",
                     help="(Alternate) Topology directory to use",
                     default = DEFAULT_TOPODIR, metavar="DIR")
  parser.add_option ("-d", "--topoext", action="store", dest="topo_ext",
                     help="(Alternate) Topology file extension",
                     default = DEFAULT_TOPOEXTENSION, metavar="EXTENSION")
  parser.add_option ("-l", "--listfile", action="store", dest="file_list",
                     help="(Alternate) Catalog of configuration files to localise",
                     default = None, metavar="FILE")
  parser.add_option ("-a", "--action", action="store", dest="action",
                     help="One of 'check', 'sample' or 'write'",
                     default = "sample", metavar="ACTION")
  parser.add_option ("-f", "--force", action="store_true", default=False,
                     dest="force", help="Write new configuration files (required for 'write')")
  parser.add_option ("-e", "--extension", action="store", dest="extension",
                     help="(Alternate) Extension to use for templates",
                     default = TEMPLATE_EXTENSION, metavar="EXTENSION")
  parser.add_option ("-m", "--module", action="store", dest="module",
                     help="Module to localise for (required)", metavar="MODULE")
  parser.add_option ("-r", "--release", action="store", dest="release",
                     help="Release of module (required)", metavar="RELEASE")
  parser.add_option ("-t", "--target", action="store", dest="target",
                     help="(Alternate) Target to localise for",
                     default = socket.gethostname (), metavar="HOST")
  parser.add_option ("-b", "--nobackup", action="store_true", default=False,
                     dest="backup", help="Disable backups of touched files")
  parser.add_option ("-v", "--verbose", action="store_true", default=False,
                     dest="verbose", help="Enable verbose output")
  parser.add_option ("-q", "--quiet", action="store_true", default=False,
                     dest="quiet", help="Suppress output")
  (options, args) = parser.parse_args ()
  err = False
  if not (options.file_list and options.module and options.release):
    print >> sys.stderr, "ERROR: Missing argument(s)"
    err = True
  if options.file_tool and not os.path.isfile (options.file_tool):
    print >> sys.stderr, "ERROR: Configuration tool doesn't exist: " + options.file_tool
    err = True
  if not os.path.isdir (options.topo_dir):
    print >> sys.stderr, "ERROR: Topology directory doesn't exist: " + options.topo_dir
    err = True
  if not options.file_list:
    options.file_list = DEFAULT_LISTFILE % options.module
  if not os.path.isfile (options.file_list):
    print >> sys.stderr, "ERROR: List file doesn't exist: " + options.file_list
    err = True
  if options.action not in ["check", "sample", "write"]:
    print >> sys.stderr, "ERROR: Illegal/unsupported action: " + options.action
    err = True
  if options.action == "write" and not options.force:
    print >> sys.stderr, "ERROR: Write action requested without --force."
    err = True
  if options.force and options.action != "write":
    print >> sys.stderr, "ERROR: Force is only legal with write action."
    err = True
  if options.topo_ext[0] != "." : # Safety check
    options.topo_ext = "." + options.topo_ext
  if options.extension[0] != "." : # Safety check
    options.extension = "." + options.extension
  if err:
    # parser.print_help ()
    sys.exit (-1)
  return (options, args)

def localise_file (options, in_file, out_file, force_quiet = False):
  cmd = options.file_tool
  if options.backup:
    cmd += " -b"
  if options.topo_dir != DEFAULT_TOPODIR:
    cmd += " -c " + options.topo_dir
  if options.topo_ext != DEFAULT_TOPOEXTENSION:
    cmd += " -d " + options.topo_ext
  cmd += " -i %s -o %s -m %s -r %s" % (in_file, out_file, options.module,
                                       options.release)
  if options.target != socket.gethostname ():
    cmd += " -t " + options.target
  if options.quiet:
    cmd += " -q"
  if options.verbose:
    cmd += " -v"
  #if not (force_quiet and options.quiet):
  #  print "\tProcessing: %s -> %s" % (in_file, out_file)
  if options.verbose:
    print "\t\t", cmd
  try:
    rc = subprocess.call (cmd, shell = True)
    if rc < 0 and not options.quiet:
      print >> sys.stderr, "ERROR: Configtool terminated by signal: %d" % -rc
    elif rc > 0 and not options.quiet:
      print >> sys.stderr, "ERROR: Configtool returned: %d" % rc
  except OSError, e:
    if not options.quiet:
      print >> sys.stderr, "ERROR: Execution catastrophically failed: ", str (e)
      sys.exit (900)
  return rc

def process_files (options, file_ext, force_quiet = False):
  err = 0
  for line in open (options.file_list, 'r'):
    line = line.strip ()
    if not line or line[0] == "#":
      continue
    in_file = line + options.extension
    out_file = line + file_ext
    rc = localise_file (options, in_file, out_file, force_quiet)
    if rc:
      err += 1
      if not options.quiet:
        print >> sys.stderr, "ERROR: Error in processing: ", in_file
  if err and not options.quiet:
    print >> sys.stderr, "ERROR: %d files failed to process." % err
  return err

def compare_files (options, file1, file2):
  cmd = "diff -q %s %s > /dev/null" % (file1, file2)
  #if not options.quiet:
  #  print "\tProcessing: %s vs %s" % (file1, file2)
  if options.verbose:
    print "\t\t", cmd
  rc = 0
  try:
    rc = subprocess.call (cmd, shell = True)
    if rc < 0 and not options.quiet:
      print >> sys.stderr, "ERROR: Compare terminated by signal: ", -rc
    # elif rc > 0 and options.verbose:
    #  print >> sys.stderr, "ERROR: Failed comparison check: ", file2
  except OSError, e:
    if not options.quiet:
      print >> sys.stderr, "ERROR: Compare catastrophically failed: ", e
      sys.exit (900)
  return rc

def check_files (options, file_ext):
  err = 0
  for line in open (options.file_list, 'r'):
    line = line.strip ()
    if not line or line[0] == "#":
      continue
    in_file = line + file_ext
    out_file = line
    rc = compare_files (options, in_file, out_file)
    if rc:
      err += 1
      if not options.quiet:
        print >> sys.stderr, "ERROR: Failed comparison: ", out_file
  if err and not options.quiet:
    print >> sys.stderr, "ERROR: %d file(s) failed to compare." % err
  return err

def main ():
  (options, args) = parse_options ()
  rc = 0
  if options.action == "check":
    rc = process_files (options, TEMPLATE_CHECK, True)
    if not rc:
      rc = check_files (options, TEMPLATE_CHECK)
  elif options.action == "sample":
    rc = process_files (options, TEMPLATE_SAMPLE)
  elif options.action == "write" and options.force:
    rc = process_files (options, "")
  else:
    print >> sys.stderr, "ERROR: Couldn't figure what to do."
    sys.exit (2)
  if rc and not options.quiet:
    print >> sys.stderr, "ERROR: Failure during %s process." % options.action
  sys.exit (rc)

if __name__ == "__main__":
  main()
