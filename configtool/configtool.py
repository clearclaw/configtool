#!/usr/bin/env python

import itertools, logging, logtool, os, re, socket, subprocess, sys
from StringIO import StringIO
from socket import gethostname
from optparse import OptionParser
from configobj import ConfigObj

DEFAULT_CONFIGTOOL = r"configlocalise"
DEFAULT_CTDIR = r"/etc/configtool"
DEFAULT_WORKDIR = r"/"
DEFAULT_LOCALTOOL = r"configmanage"
DEFAULT_MODULESDIR = "modules.d"
DEFAULT_TOPODIR = "topo.d"
DEFAULT_TEMPLEXTENSION = r".templ"
DEFAULT_TOPOEXTENSION = r".topo"
TEMPLATE_CHECK = r".check"
TEMPLATE_SAMPLE = r".sample"
PROCESS_UTTIME, PROCESS_STRTIME = logtool.now (slug = True)
VARIABLE_REGEX = r"\$\{([A-Za-z0-9._]+)\}"
ESCAPED_REGEX = r"\$\{\{([A-Za-z0-9._]+)\}\}"

@logtool.log_func
def print_verbose (options, s):
  """Console output in verbose mode."""
  if options.verbose:
    print s

@logtool.log_func
def print_error (options, s):
  """Console output for errors -- suppressed by quiet mode."""
  if not options.quiet:
    print >> sys.stderr, s

@logtool.log_func
def check_options (options):
  # pylint: disable-msg = R0912,R0915
  if not os.path.isdir (options.ct_dir):
    print_error (
      options,
      "ERROR: Configtool root is not a directory: %s" % options.ct_dir)
    options.rc += 1
  if not os.path.isdir (options.work_dir):
    print_error (options,
                 "ERROR: Work root is not a directory: %s" % options.work_dir)
    options.rc += 1
  if not options.action or options.action not in [
    "check", "clean", "sample", "status", "write"]:
    if options.action:
      print_error (options, "ERROR: Illegal action: %s" % options.action)
    else:
      print_error (options, "ERROR: Missing action.")
    options.rc += 1
  if options.action == "write" and not options.force:
    print_error (options, "ERROR: Write action requested without --force.")
    options.rc += 1
  if options.force and options.action != "write":
    print_error (options, "ERROR: Force is only legal with write action.")
    options.rc += 1
  if options.action != "status":
    if not options.module:
      print_error (options, "ERROR: Missing module.")
      options.rc += 1
    if not options.release:
      try:
        options.release = get_release (options, options.module)
        if not options.release:
          print_error (options, "ERROR: Unable to find module release.")
          options.rc += 1
      except: # pylint: disable-msg = W0702
        print_error (options, "ERROR: Unable to find module release.")
        options.rc += 1
    if not options.release: # Version lookup failed or bad version passed
      print_error (
        options,
        "ERROR: Ambiguous or no version found for module: %s"
        % str (options.module))
      options.rc += 1
    options.file_list = (os.path.join (
      options.ct_dir, DEFAULT_MODULESDIR, r"%s.cfgs") % options.module)
    if not os.path.isfile (options.file_list):
      print_error (options,
                   "ERROR: List file doesn't exist: %s" % options.file_list)
      options.rc += 1
  if not os.path.isdir (options.ct_dir):
    print_error (
      options,
      "ERROR: Configtool directory doesn't exist: %s" % options.ct_dir)
    options.rc += 1
  if options.action == "status":
    if options.module:
      print_error (options, "ERROR: Can't define module for status command.")
      options.rc += 1
  return options.rc

@logtool.log_func
def parse_options ():
  parser = OptionParser ()
  parser.add_option ("-c", "--confitooldir", action = "store", dest = "ct_dir",
                     help = "(Alternate) Configtool directory root to use.",
                     default = DEFAULT_CTDIR, metavar = "DIR")
  parser.add_option ("-w", "--workdir", action = "store", dest = "work_dir",
                     help = "(Alternate) Working root directory to use.",
                     default = DEFAULT_WORKDIR, metavar = "DIR")
  parser.add_option ("-a", "--action", action = "store", dest = "action",
                     help = "One of 'check', 'clean', 'sample', 'status'"
                            + " or 'write'.",
                     default = None, metavar = "ACTION")
  parser.add_option ("-f", "--force", action = "store_true", default = False,
                     dest = "force",
                     help = "Write new configuration files"
                            + " (required for 'write').")
  parser.add_option ("-m", "--module", action = "store", dest = "module",
                     help = "Module to localise for (required).",
                     metavar = "MODULE")
  parser.add_option ("-r", "--release", action = "store", dest = "release",
                     help = "(Alternate) Release of module.",
                     metavar = "RELEASE")
  parser.add_option ("-t", "--target", action = "store", dest = "target",
                     help = "(Alternate) Target host(name) to localise for.",
                     default = gethostname (), metavar = "HOST")
  parser.add_option ("-b", "--nobackup", action = "store_true",
                     default = False, dest = "backup",
                     help = "Disable backups of touched files.")
  parser.add_option ("-v", "--verbose", action = "store_true", default = False,
                     dest = "verbose", help = "Enable verbose output.")
  parser.add_option ("-q", "--quiet", action = "store_true", default = False,
                     dest = "quiet", help = "Suppress all output.")
  parser.add_option ("-d", "--debug", action = "store_true", default = False,
                     dest = "debug", help = "Output debug information.")
  (options, args) = parser.parse_args ()
  options.rc = 0
  logging.basicConfig (level = logging.DEBUG if options.debug
                       else logging.INFO)
  if check_options (options):
    raise ValueError
  return (options, args)

@logtool.log_func
def get_localhostname ():
  """Get the local hostname without a domain."""
  h = socket.gethostname ()
  return h.split (".")[0]

@logtool.log_func
def get_value (base, kl, key):
  while kl:
    k = kl[0]
    kl = kl[1:]
    if k is None or k == "":
      continue
    base = base[k]
  return base[key]

@logtool.log_func
def gen_indexes (s):
  for i in xrange (len (s), -1, -1):
    yield s[:i]
  raise StopIteration

@logtool.log_func
def specific_value (config, options, key):
  for k in [options.module, "DEFAULT"]:
    g_host = gen_indexes (options.target)
    g_release = gen_indexes (options.release)
    base = config.get (k)
    if base: # Got a module
      for i in itertools.product (g_release, g_host):
        try:
          return get_value (base, i, key)
        except: # pylint: disable-msg=W0702
          continue
  # Failed
  # print ("No definition for key: ${%s}\n" % key)
  print_error (options, "\t\t\tNo definition for variable: ${%s}" % key)
  return None

@logtool.log_func
def config_value (cfg_list, options, key):
  if not cfg_list or cfg_list == []:
    return None
  for c in cfg_list:
    v = specific_value (c[1], options, key)
    if v:
      return v
    # Failed
    # print ("No definition for key: %s/${%s}\n" % (c[0], key))
  print_error (options, "\t\t\tNo definition for variable: ${%s}" % key)
  return None

@logtool.log_func
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
      print_verbose (options, "\t\tReplacing ${%s} with: %s" % (k, v))
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

@logtool.log_func
def get_release (options, app):
  try:
    import rpm
    ts = rpm.TransactionSet ()
    entry = ts.dbMatch ()
    entry.pattern ('name', rpm.RPMMIRE_GLOB, app)
    for i in entry:
      if i['name'] == app:
        return i['version']
    print_error (options,
                 "WARNING: Failed to find installed RPM version of %s" % app)
    return None
  except ImportError:
    import apt
    cache = apt.cache.Cache ()
    cache.open ()
    try:
      p = cache[app]
    except: # pylint: disable-msg = W0702
      print_error (options,
                   "ERROR: Failed to find DEB version of %s" % app)
      return None
    if not p or not p.installed:
      print_error (options,
                   "ERROR: Failed to find installed DEB version of %s" % app)
      return None
    try:
      return p.versions.keys ()[0]
    except: # pylint: disable-msg = W0702
      return None

@logtool.log_func
def load_topos (options, topo_dir):
  cfg_list = []
  files = os.listdir (topo_dir)
  files.sort ()
  for f in files:
    if f.endswith (DEFAULT_TOPOEXTENSION):
      fname = os.path.join (topo_dir, f)
      try:
        c = ConfigObj (fname, interpolation = False)
      except: # pylint: disable-msg = W0702
        print_error (options, "Unable to parse topo file: %s" % fname)
        raise ValueError
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

@logtool.log_func
def do_file (options, in_file, out_file):
  print_verbose (options, "\tFile: %s" % in_file)
  cfg_list = load_topos (options, os.path.join (options.ct_dir,
                                                DEFAULT_TOPODIR))
  if not cfg_list:
    print_error (options, "ERROR: Failed to find/load any topology files.")
    raise ValueError
  if not options.backup and os.path.isfile (out_file):
    os.rename (out_file, "%s-backup.%s" % (out_file, PROCESS_STRTIME))
  else:
    try:
      os.remove (out_file)
    except: # pylint: disable-msg=W0702
      pass
  if not os.path.isfile (in_file):
    print_error (options, "ERROR: Template %s is not a file." % in_file)
    return 1
  rc = 0
  with open (in_file, "r") as file_in:
    with open (out_file, "w") as file_out:
      rc = localise_file (cfg_list, options, file_in, file_out)
      if rc:
        print_error (options,
                     "ERROR: Failed.  Some variables were not defined.")
  return rc

@logtool.log_func
def status_process (options):
  total = 0
  for f in os.listdir (os.path.join (options.ct_dir, DEFAULT_MODULESDIR)):
    if not f.endswith (".cfgs"):
      continue
    module = f[:-5]
    args = [sys.argv[0], "-a", "check", "-m", module]
    if options.ct_dir != DEFAULT_CTDIR:
      args.extend (["-c", options.ct_dir])
    if options.work_dir != DEFAULT_WORKDIR:
      args.extend (["-w", options.work_dir])
    if options.verbose:
      args.extend (["-v",])
    if options.debug:
      args.extend (["-d",])
    print_verbose (options, " ".join (args) + "\t(output suppressed)")
    p = subprocess.Popen (args = args, cwd = "/tmp")
    rc = p.wait ()
    if rc:
      total += 1
      print_error (options,
                   "\tFAILED!  Configuration is inconsistent (%d).\n" % rc)
    else:
      print_error (options, "\t\tCorrect.")
  return total

@logtool.log_func
def clean_file (options, file1, file2): # pylint: disable-msg = W0613
  if not options.backup and os.path.isfile (file1):
    os.rename (file1, "%s-backup.%s" % (file1, PROCESS_STRTIME))
  else:
    try:
      os.remove (file1)
    except: # pylint: disable-msg = W0702
      return 1
  return 0

@logtool.log_func
def compare_files (options, file1, file2):
  cmd = "diff -q %s %s > /dev/null" % (file1, file2)
  #if not options.quiet:
  #  print_error (options, "\tProcessing: %s vs %s" % (file1, file2))
  print_verbose (options, "\t%s" % cmd)
  rc = 0
  try:
    rc = subprocess.call (cmd, shell = True)
    if rc < 0:
      print_error (options, "ERROR: Compare terminated by signal: %s" % (-rc))
    # elif rc > 0:
    #  print_verbose (options, "ERROR: Failed comparison check: %s" % file2)
  except OSError, e:
    print_error (options, "ERROR: Compare catastrophically failed: %s" % e)
    raise Exception
  return rc

@logtool.log_func
def process_cfgs (options, cfg_ext, out_ext, func):
  err = 0
  print_verbose (options, "Module: %s" % options.module)
  for line in open (options.file_list, 'r'):
    line = line.strip ()
    if not line or line[0] == "#":
      continue
    if line[0] == os.path.sep: # Knock of root for work_dir
      line = line[1:]
    in_file = os.path.join (options.work_dir, line + cfg_ext)
    out_file = os.path.join (options.work_dir, line + out_ext)
    rc = func (options, in_file, out_file)
    if rc:
      err += 1
      print_error (options, "ERROR: Error in processing: %s" % in_file)
  if err:
    print_error (options, "ERROR: %d files failed to process." % err)
  return err

@logtool.log_func
def do_check (options):
  rc = process_cfgs (options, DEFAULT_TEMPLEXTENSION, TEMPLATE_CHECK, do_file)
  if not rc:
    rc = process_cfgs (options, TEMPLATE_CHECK, "", compare_files)
  return rc

@logtool.log_func
def do_clean (options):
  rc = process_cfgs (options, "", "", clean_file)
  if rc:
    print_verbose (
      options,
      "ERROR: Failed cleaning configuration files.  Nothing to remove?")
  return 0

@logtool.log_func
def do_sample (options):
  return process_cfgs (options,
                       DEFAULT_TEMPLEXTENSION, TEMPLATE_SAMPLE, do_file)

@logtool.log_func
def do_status (options):
  rc = status_process (options)
  if rc:
    print_error (options,
                 "ERROR: %d modules have inconsistent configurations." % rc)
  return rc

@logtool.log_func
def do_write (options):
  return process_cfgs (options, DEFAULT_TEMPLEXTENSION, "", do_file)

@logtool.log_func
def do_unknown (options):
  print_error (options, "ERROR: Couldn't figure what to do.")
  return 2

@logtool.log_func
def main ():
  try:
    (options, args) = parse_options () # pylint: disable-msg = W0612
    if options.rc:
      sys.exit (options.rc)
    actions = {
      "check": do_check,
      "clean": do_clean,
      "sample": do_sample,
      "status": do_status,
      "write": do_write,
      }
    rc = actions.get (options.action, do_unknown) (options)
    if rc:
      print_error (options,
                   "ERROR: Failure during %s process." % options.action)
    sys.exit (rc)
  except Exception as e: # pylint: disable-msg = W0702
    logtool.log_fault (e, message = "FAULT: Irrecoverable error.",
                       level = logging.DEBUG)
    sys.exit (99)

if __name__ == "__main__":
  main()
