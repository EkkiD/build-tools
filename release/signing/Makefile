# This Makefile is meant to be run on keymaster after all locales are built
# and before partial MARs are generated.
# Common usage is as follows:
#  1. Open up signcodepwd.exe and enter passphrase
#  2. mkdir ~/signing-work/$product-$version
#  3. cd ~/signing-work/$product-$version
#  4. cp ~/Makefile .
#  5. make MAIL=yourname@domain.com BUILD=1 VERSION=3.1b1 \
#          TAG=FIREFOX_3_1b1_RELEASE REPO=releases/mozilla-1.9.1
#
# You can pass the other variables listed below, too, if you want to use a
# different stage server, ssh key or username, or sign a different product, etc.
#
# You should receive mail a few times during this process:
#  * Right before sign-release.pl starts
#  * After sign-release.pl completes successfully
#  * Right before sign-files is called, to remind you to enter the passphrase
#  * After the entire process is done, and files are ready to inspected
#    and uploaded.
#
# Note that if something errors you will not receive e-mails past that point
# or mail about the error.
#
# When you're satisfied with the builds and ready to upload them you can run:
#     make upload
# with all of the same variable definitions which will rsync the signed builds
# back from whence they came.

# Make sure necessary variables are defined / set defaults
VERSION         = $(error VERSION must be defined)
BUILD           = $(error BUILD must be defined)
REPO            = $(error REPO must be defined)
TAG             = $(error TAG must be defined)
EMAIL          ?= release@mozilla.com
STAGE_USERNAME ?= ffxbld
SSH_KEY        ?= $(HOME)/.ssh/ffxbld_dsa
PRODUCT        ?= firefox
WORKDIR         = $(HOME)/signing-work/$(PRODUCT)-$(VERSION)
MAR             = $(WORKDIR)/mar.exe
SEVENZIP        = $(WORKDIR)/7-Zip/7z.exe
UPX_BIN         = $(WORKDIR)/upx/upx.exe


all: setup download sign verify fake-upload

echo:
	@echo EMAIL: $(EMAIL)
	@echo STAGE_USERNAME: $(STAGE_USERNAME)
	@echo SSH_KEY: $(SSH_KEY)
	@echo WORKDIR: $(WORKDIR)
	@echo PRODUCT: $(PRODUCT)
	@echo VERSION: $(VERSION)
	@echo BUILD: $(BUILD)
	@echo TAG: $(TAG)
	@echo REPO: $(REPO)

setup:
	# Pull/copy the required tools.
	cvs -d:ext:cltbld@cvs.mozilla.org:/mofo co -d signing release/signing/tools
	cvs -d:ext:cltbld@cvs.mozilla.org:/cvsroot co -d MozBuild mozilla/tools/release/MozBuild
	rsync -av $(HOME)/signing-utils/7-Zip . 
	rsync -av $(HOME)/signing-utils/mar.exe . 
	rsync -av $(HOME)/signing-utils/upx . 

download:
	# Download the builds.
	rsync -av --exclude '*.zip' -e "ssh -i $(SSH_KEY)" \
	  $(STAGE_USERNAME)@stage.mozilla.org:/home/ftp/pub/$(PRODUCT)/nightly/$(VERSION)-candidates/build$(BUILD)/ \
	  unsigned-build$(BUILD)
	# Copy linux/mac builds over to the signed dir, because they don't need internal signing.
	rsync -av --exclude '*unsigned*' unsigned-build$(BUILD)/ signed-build$(BUILD)/

sign: sign-internal sign-installers

sign-internal:
	blat -to $(EMAIL) \
	     -subject "sign-release.pl for $(PRODUCT) $(VERSION) starting" \
		 -body "EOM"
	# Sign the internals of the win32 builds.
	MAR=$(MAR) SEVENZIP=$(SEVENZIP) UPX_BIN=$(UPX_BIN) \
	  perl ./signing/sign-release.pl -M dir -a $(PRODUCT) --release $(TAG) \
	  -d unsigned-build$(BUILD)/unsigned -o signed-build$(BUILD) \
	  -R $(REPO) >> win32_signing_build$(BUILD).log 2>&1
	# And copy over the info file and XPIs.
	cp -pv ./unsigned-build$(BUILD)/unsigned/win32_info.txt ./signed-build$(BUILD)/ 
	rsync -av ./unsigned-build$(BUILD)/unsigned/win32/xpi ./signed-build$(BUILD)/win32
	blat -to $(EMAIL) \
	     -subject "sign-release.pl for $(PRODUCT) $(VERSION) completed" \
		 -body "EOM"

sign-installers:
	# Sign win32 installers.
	cd $(WORKDIR)/signed-build$(BUILD)/win32 && sign-release
	# Generate detached sigs.
	blat -to $(EMAIL) \
	     -subject "Running sign-files for $(PRODUCT) $(VERSION), waiting on passphrase" \
		 -body "EOM"
	cd $(WORKDIR)/signed-build$(BUILD) && sign-files .

verify: verify-signatures verify-win32 verify-asc
	echo "Verification completed"

# This test verifies that installer signing is valid and can be traced back to
# a valid root certificate. Basically, it runs 'chktrust /q *.exe' for every
# win32 locale directory.
verify-signatures:
	cd $(WORKDIR)/signed-build$(BUILD)/win32 && verify-signatures

# This test ensures that every exe and mar in the signed-build$(BUILD) directory
# differs from its unsigned counterpart.
verify-win32: DIFF_FILES=$(strip $(shell diff -rq $(WORKDIR)/unsigned-build$(BUILD)/unsigned/ \
                           signed-build$(BUILD)/ | grep -E '(\.exe|\.mar)\ ' | wc -l))
verify-win32: TOTAL_FILES=$(strip $(shell find $(WORKDIR)/unsigned-build$(BUILD)/unsigned/ \
                            -name '*.exe' -or -name '*.mar' | wc -l))
verify-win32:
	test $(TOTAL_FILES) -gt 0 || \
	  (echo "No files in $(WORKDIR)/unsigned-build$(BUILD)/unsigned, bailing..." && exit 1)
	test $(DIFF_FILES) -eq $(TOTAL_FILES) || \
	  (echo "Some files are unsigned, bailing..." && exit 1)
	echo "Win32 installers appear to be signed properly"

# Finally, this test makes sure we have asc files for every build in
# signed-build$(BUILD). Note that we do not generate detached sigs for MARs,
# XPIs, logs, text files, etc. Basically, we only generate them for installers,
# packages (tar.bz2, dmg, exe), and source files (tar.bz2, .bundle).
verify-asc: ASC_FILES=$(strip $(shell find $(WORKDIR)/signed-build$(BUILD)/ \
                        -name "*.asc" -type f | wc -l))
verify-asc: TOTAL_FILES=$(strip $(shell find $(WORKDIR)/signed-build$(BUILD)/ \
                          -not -wholename '*update*' -not -name "*.xpi" -not -name "*.asc" \
                          -not -name "*.txt" -not -name "*.log" -type f | wc -l))
verify-asc:
	test $(TOTAL_FILES) -gt 0 || \
	  (echo "No files in $(WORKDIR)/signed-build$(BUILD), bailing..." && exit 1)
	test $(ASC_FILES) -eq $(TOTAL_FILES) || \
	  (echo "Incorrect number of .asc files" && exit 1)
	echo "Correct number of .asc files are present"

fake-upload:
	rsync -n -e "ssh -i $(SSH_KEY)" -av signed-build$(BUILD)/ \
	  $(STAGE_USERNAME)@stage.mozilla.org:/home/ftp/pub/$(PRODUCT)/nightly/$(VERSION)-candidates/build$(BUILD)/ \
	  | grep -v asc | grep -v exe | grep -v 'update/win32/.*/.*\.mar'
	blat -to $(EMAIL) \
	     -subject "Signing of $(PRODUCT) $(VERSION) done, ready for inspection"\
	     -body "EOM"

upload:
	rsync -e "ssh -i $(SSH_KEY)" -av signed-build$(BUILD)/ \
	  $(STAGE_USERNAME)@stage.mozilla.org:/home/ftp/pub/$(PRODUCT)/nightly/$(VERSION)-candidates/build$(BUILD)/