#!/usr/bin/python
# vim:sts=2 sw=2
import sys, shutil, urllib2, urllib, os, traceback, time

clobber_suffix='.deleteme'

def ts_to_str(ts):
  if ts is None:
    return None
  return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))

def write_file(ts, fn):
  assert isinstance(ts, int)
  f = open(fn, "w")
  f.write(str(ts))
  f.close()

def read_file(fn):
  if not os.path.exists(fn):
    return None

  data = open(fn).read().strip()
  try:
    return int(data)
  except ValueError:
    return None

def rmdirRecursive(dir):
    """This is a replacement for shutil.rmtree that works better under
    windows. Thanks to Bear at the OSAF for the code.
    (Borrowed from buildbot.slave.commands)"""
    if not os.path.exists(dir):
        # This handles broken links
        if os.path.islink(dir):
            os.remove(dir)
        return

    if os.path.islink(dir):
        os.remove(dir)
        return

    # Verify the directory is read/write/execute for the current user
    os.chmod(dir, 0700)

    for name in os.listdir(dir):
        full_name = os.path.join(dir, name)
        # on Windows, if we don't have write permission we can't remove
        # the file/directory either, so turn that on
        if os.name == 'nt':
            if not os.access(full_name, os.W_OK):
                # I think this is now redundant, but I don't have an NT
                # machine to test on, so I'm going to leave it in place
                # -warner
                os.chmod(full_name, 0600)

        if os.path.isdir(full_name):
            rmdirRecursive(full_name)
        else:
            # Don't try to chmod links
            if not os.path.islink(full_name):
                os.chmod(full_name, 0700)
            os.remove(full_name)
    os.rmdir(dir)

def do_clobber(dir, dryrun=False, skip=None):
  try:
    for f in os.listdir(dir):
      if skip is not None and f in skip:
        print "Skipping", f
        continue
      clobber_path=f+clobber_suffix
      if os.path.isfile(f):
        print "Removing", f
        if not dryrun:
          if os.path.exists(clobber_path):
            os.unlink(clobber_path)
          # Prevent repeated moving.
          if f.endswith(clobber_suffix):
            os.unlink(f)
          else:
            shutil.move(f, clobber_path)
            os.unlink(clobber_path)
      elif os.path.isdir(f):
        print "Removing %s/" % f
        if not dryrun:
          if os.path.exists(clobber_path):
            rmdirRecursive(clobber_path)
          # Prevent repeated moving.
          if f.endswith(clobber_suffix):
            rmdirRecursive(f)
          else:
            shutil.move(f, clobber_path)
            rmdirRecursive(clobber_path)
  except:
    print "Couldn't clobber properly, bailing out."
    sys.exit(1)

def getClobberDates(clobberURL, branch, buildername, builddir, slave, master):
  params = dict(branch=branch, buildername=buildername, builddir=builddir, slave=slave, master=master)
  url = "%s?%s" % (clobberURL, urllib.urlencode(params))
  print "Checking clobber URL: %s" % url
  data = urllib2.urlopen(url).read().strip()

  retval = {}
  try:
    for line in data.split("\n"):
      line = line.strip()
      if not line:
        continue
      builddir, builder_time, who = line.split(":")
      builder_time = int(builder_time)
      retval[builddir] = (builder_time, who)
    return retval
  except ValueError:
    print "Error parsing response from server"
    print data
    raise

if __name__ == "__main__":
  from optparse import OptionParser
  parser = OptionParser("%prog [options] clobberURL branch buildername builddir slave master")
  parser.add_option("-n", "--dry-run", dest="dryrun", action="store_true",
      default=False, help="don't actually delete anything")
  parser.add_option("-t", "--periodic", dest="period", type="float",
      default=None, help="hours between periodic clobbers")
  parser.add_option('-s', '--skip', help='do not delete this file/directory',
      action='append', dest='skip', default=['last-clobber'])
  parser.add_option('-d', '--dir', help='clobber this directory',
      dest='dir', default='.', type='string')
  parser.add_option('-v', '--verbose', help='be more verbose',
      dest='verbose', action='store_true', default=False)

  options, args = parser.parse_args()
  if len(args) != 6:
    parser.error("Incorrect number of arguments")

  if options.period:
    periodicClobberTime = options.period * 3600
  else:
    periodicClobberTime = None

  clobberURL, branch, builder, my_builddir, slave, master = args

  try:
    server_clobber_dates = getClobberDates(clobberURL, branch, builder, my_builddir, slave, master)
  except:
    if options.verbose:
      traceback.print_exc()
    print "Error contacting server"
    sys.exit(1)

  if options.verbose:
    print "Server gave us", server_clobber_dates

  now = int(time.time())

  # Add ourself to the server_clobber_dates if it's not set
  # This happens when this slave has never been clobbered
  if my_builddir not in server_clobber_dates:
    server_clobber_dates[my_builddir] = None, ""

  root_dir = os.path.abspath(options.dir)

  for builddir, (server_clobber_date, who) in server_clobber_dates.items():
    builder_dir = os.path.join(root_dir, builddir)
    if not os.path.isdir(builder_dir):
      print "%s doesn't exist, skipping" % builder_dir
      continue
    os.chdir(builder_dir)

    our_clobber_date = read_file("last-clobber")

    clobber = False

    print "%s:Our last clobber date: " % builddir, ts_to_str(our_clobber_date)
    print "%s:Server clobber date:   " % builddir, ts_to_str(server_clobber_date)

    # If we don't have a last clobber date, then this is probably a fresh build.
    # We should only do a forced server clobber if we know when our last clobber
    # was, and if the server date is more recent than that.
    if server_clobber_date is not None and our_clobber_date is not None:
      # If the server is giving us a clobber date, compare the server's idea of
      # the clobber date to our last clobber date
      if server_clobber_date > our_clobber_date:
        # If the server's clobber date is greater than our last clobber date,
        # then we should clobber.
        clobber = True
        # We should also update our clobber date to match the server's
        our_clobber_date = server_clobber_date
        if who:
          print "%s:Server is forcing a clobber, initiated by %s" % (builddir, who)
        else:
          print "%s:Server is forcing a clobber" % builddir

    if not clobber:
      # Disable periodic clobbers for builders that aren't my_builddir
      if builddir != my_builddir:
        continue

      # Next, check if more than the periodicClobberTime period has passed since
      # our last clobber
      if our_clobber_date is None:
        # We've never been clobbered
        # Set our last clobber time to now, so that we'll clobber
        # properly after periodicClobberTime
        our_clobber_date = now
        write_file(our_clobber_date, "last-clobber")
      elif periodicClobberTime and now > our_clobber_date + periodicClobberTime:
        # periodicClobberTime has passed since our last clobber
        clobber = True
        # Update our clobber date to now
        our_clobber_date = now
        print "%s:More than %s seconds have passed since our last clobber" % (builddir, periodicClobberTime)

    if clobber:
      # Finally, perform a clobber if we're supposed to
      print "%s:Clobbering..." % builddir
      do_clobber(builder_dir, options.dryrun, options.skip)
      write_file(our_clobber_date, "last-clobber")
