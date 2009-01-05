#!/usr/bin/python

# This script expects a directory as its first non-option argument,
# followed by a list of filenames.

import sys, os, os.path, shutil
from optparse import OptionParser
from time import mktime, strptime

NIGHTLY_PATH = "/home/ftp/pub/%(product)s/nightly"
TINDERBOX_BUILDS_PATH = "/home/ftp/pub/%(product)s/tinderbox-builds/%(tinderbox_builds_dir)s"
LATEST_DIR = "latest-%(branch)s"
LONG_DATED_DIR = "%(year)s/%(month)s/%(year)s-%(month)s-%(day)s-%(hour)s-%(branch)s"
SHORT_DATED_DIR = "%(year)s-%(month)s-%(day)s-%(hour)s-%(branch)s"
CANDIDATES_DIR = "%(version)s-candidates/build%(buildnumber)s"

def CopyFileToDir(original_file, source_dir, dest_dir, preserve_dirs=False):
    if not original_file.startswith(source_dir):
        print "%s is not in %s!" % (original_file, source_dir)
        return
    relative_path = os.path.basename(original_file)
    if preserve_dirs:
        # Add any dirs below source_dir to the final destination
        filePath = original_file.replace(source_dir, "").lstrip("/")
        filePath = os.path.dirname(filePath)
        dest_dir = os.path.join(dest_dir, filePath)
    new_file = os.path.join(dest_dir, relative_path)
    full_dest_dir = os.path.dirname(new_file)
    if not os.path.isdir(full_dest_dir):
        os.makedirs(full_dest_dir)
    if os.path.exists(new_file):
        os.unlink(new_file)
    shutil.copyfile(original_file, new_file)

def BuildIDToDict(buildid):
    """Returns an dict with the year, month, day, hour, minute, and second
       as keys, as parsed from the buildid"""
    buildidDict = {}
    try:
        # strptime is no good here because it strips leading zeros
        buildidDict['year']   = buildid[0:4]
        buildidDict['month']  = buildid[4:6]
        buildidDict['day']    = buildid[6:8]
        buildidDict['hour']   = buildid[8:10]
        buildidDict['minute'] = buildid[10:12]
        buildidDict['second'] = buildid[12:14]
    except:
        raise "Could not parse buildid!"
    return buildidDict

def BuildIDToUnixTime(buildid):
    """Returns the timestamp the buildid represents in unix time."""
    try:
        return int(mktime(strptime(buildid, "%Y%m%d%H%M%S")))
    except:
        raise "Could not parse buildid!"

def ReleaseToDated(options, upload_dir, files):
    values = BuildIDToDict(options.buildid)
    values['branch']  = options.branch
    longDir = LONG_DATED_DIR % values
    shortDir = SHORT_DATED_DIR % values

    longDatedPath = os.path.join(NIGHTLY_PATH, longDir)
    shortDatedPath = os.path.join(NIGHTLY_PATH, shortDir)

    for f in files:
        CopyFileToDir(f, upload_dir, longDatedPath)
        os.chdir(NIGHTLY_PATH)
        os.symlink(longDir, shortDir)

def ReleaseToLatest(options, upload_dir, files):
    latestDir = LATEST_DIR % {'branch': options.branch}
    latestPath = os.path.join(NIGHTLY_PATH, latestDir)

    for f in files:
        if f.endswith('.xpi'):
            CopyFileToDir(f, upload_dir, latestPath)

def ReleaseToTinderboxBuilds(options, upload_dir, files, dated=True):
    tinderboxBuildsPath = TINDERBOX_BUILDS_PATH % \
      {'product': options.product,
       'tinderbox_builds_dir': options.tinderbox_builds_dir}
    if dated:
        buildid = str(BuildIDToUnixTime(options.buildid))
        tinderboxBuildsPath = os.path.join(tinderboxBuildsPath, buildid)

    for f in files:
        CopyFileToDir(f, upload_dir, tinderboxBuildsPath)
        
def ReleaseToTinderboxBuildsOverwrite(options, upload_dir, files):
    ReleaseToTinderboxBuilds(options, upload_dir, files, dated=False)

def ReleaseToCandidatesDir(options, upload_dir, files):
    candidatesDir = CANDIDATES_DIR % {'version': options.version,
                                      'buildnumber': options.build_number}
    candidatesPath = os.path.join(NIGHTLY_PATH, candidatesDir)

    for f in files:
        realCandidatesPath = candidatesPath
        if 'win32' in f:
            realCandidatesPath = os.path.join(realCandidatesPath, 'unsigned')
        CopyFileToDir(f, upload_dir, realCandidatesPath, preserve_dirs=True)


if __name__ == '__main__':
    releaseTo = []
    error = False
    
    parser = OptionParser(usage="usage: %prog [options] <directory> <files>")
    parser.add_option("-p", "--product",
                      action="store", dest="product",
                      help="Set product name to build paths properly.")
    parser.add_option("-v", "--version",
                      action="store", dest="version",
                      help="Set version number to build paths properly.")
    parser.add_option("-b", "--branch",
                      action="store", dest="branch",
                      help="Set branch name to build paths properly.")
    parser.add_option("-i", "--buildid",
                      action="store", dest="buildid",
                      help="Set buildid to build paths properly.")
    parser.add_option("-n", "--build-number",
                      action="store", dest="build_number",
                      help="Set buildid to build paths properly.")
    parser.add_option("--tinderbox-builds-dir",
                      action="store", dest="tinderbox_builds_dir",
                      help="Set tinderbox builds dir to build paths properly.")
    parser.add_option("-l", "--release-to-latest",
                      action="store_true", dest="release_to_latest",
                      help="Copy files to $product/nightly/latest-$branch")
    parser.add_option("-d", "--release-to-dated",
                      action="store_true", dest="release_to_dated",
                      help="Copy files to $product/nightly/$datedir-$branch")
    parser.add_option("-c", "--release-to-candidates-dir",
                      action="store_true", dest="release_to_candidates_dir",
                      help="Copy files to $product/nightly/$version-candidates/build$build_number")
    parser.add_option("-t", "--release-to-tinderbox-builds",
                      action="store_true", dest="release_to_tinderbox_builds",
                      help="Copy files to $product/tinderbox-builds/$tinderbox_builds_dir")
    parser.add_option("--release-to-tinderbox-dated-builds",
                      action="store_true", dest="release_to_dated_tinderbox_builds",
                      help="Copy files to $product/tinderbox-builds/$tinderbox_builds_dir/$timestamp")
    (options, args) = parser.parse_args()
    
    if len(args) < 2:
        print "Error, you must specify a directory and at least one file."
        error = True

    if not options.product:
        print "Error, you must supply the product name."
        error = True

    if options.release_to_latest:
        releaseTo.append(ReleaseToLatest)
        if not options.branch:
            print "Error, you must supply the branch name."
            error = True
    if options.release_to_dated:
        releaseTo.append(ReleaseToDated)
        if not options.branch:
            print "Error, you must supply the branch name."
            error = True
        if not options.buildid:
            print "Error, you must supply the build id."
            error = True
    if options.release_to_candidates_dir:
        releaseTo.append(ReleaseToCandidatesDir)
        if not options.version:
            print "Error, you must supply the version number."
            error = True
        if not options.build_number:
            print "Error, you must supply the build number."
            error = True
    if options.release_to_tinderbox_builds:
        releaseTo.append(ReleaseToTinderboxBuildsOverwrite)
        if not options.tinderbox_builds_dir:
            print "Error, you must supply the tinderbox builds dir."
            error = True
    if options.release_to_dated_tinderbox_builds:
        releaseTo.append(ReleaseToTinderboxBuilds)
        if not options.tinderbox_builds_dir:
            print "Error, you must supply the tinderbox builds dir."
            error = True
        if not options.buildid:
            print "Error, you must supply the build id."
            error = True
    if len(releaseTo) == 0:
        print "Error, you must pass a --release-to option!"
        error = True
    
    if error:
        sys.exit(1)
    
    NIGHTLY_PATH = NIGHTLY_PATH % {'product': options.product}
    upload_dir = os.path.abspath(args[0])
    files = args[1:]
    if not os.path.isdir(upload_dir):
        print "Error, %s is not a directory!" % upload_dir
        sys.exit(1)
    for f in files:
        f = os.path.abspath(f)
        if not os.path.isfile(f):
            print "Error, %s is not a file!" % f
            sys.exit(1)
    
    for func in releaseTo:
        func(options, upload_dir, files)