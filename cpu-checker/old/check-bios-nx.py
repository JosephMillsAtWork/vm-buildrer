#!/usr/bin/python
# Copyright (C) 2009 Canonical, Ltd.
# License: GPLv3
# Author: Kees Cook <kees@ubuntu.com>
#
# Attempts to determine if the running x86-based CPU has NX capapbilities
# (regardless of it being disabled by the BIOS).  If the CPU is NX-capable
# but the nx bit is missing from flags, exit 1 (i.e. "BIOS settings need
# changing"), otherwise exit 0 (i.e. "nothing wrong with BIOS")
#
# lacks NX:
#     not pae:
#         cpu family <= 5
#         cpu family > 6 && cpu family < 15
#         cpu family == 6, model <= 12
#     pae, cpu family == 6, model == 13  (excepting some sSpec?)
#             http://processorfinder.intel.com/List.aspx?ParentRadio=All&ProcFam=942&SearchKey=
# has NX:
#     http://processorfinder.intel.com/Default.aspx
#     pae, cpu family == 6, model >= 14
#     pae, cpu family == 15, model >= 3
#     pae, cpu family > 15

import os, sys, re
import optparse

parser = optparse.OptionParser()
parser.add_option("--verbose", action='store_true',
                  help="Explain in detail what has been detected")
(opt, args) = parser.parse_args()

arch = os.environ.get('CHECK_BIOS_NX_MACHINE',os.uname()[4])
if not re.match('(i.86|x86_64)$', arch):
    if opt.verbose:
        print >>sys.stderr, "This script is currently only useful on x86-based CPUs"
    sys.exit(0)

family = None
model = None
flags = []
for line in file(os.environ.get('CHECK_BIOS_NX_CPUINFO','/proc/cpuinfo')):
    line = line.strip()
    if line.startswith('cpu family\t'):
        family = int(line.split().pop())
    elif line.startswith('model\t'):
        model = int(line.split().pop())
    elif line.startswith('flags\t'):
        flags = line.split(':',1)[1].strip().split()
    if model != None and family != None and len(flags) > 0:
        break

if len(flags) == 0:
    # No flags found (?!), fail open
    if opt.verbose:
        print >>sys.stderr, "No 'flags' were found for this CPU.  Check /proc/cpuinfo"
    sys.exit(1)

# If it's in the flags, it's not being disabled by the BIOS; rejoice.
if 'nx' in flags:
    if opt.verbose:
        print >>sys.stderr, "This CPU has 'nx' in the flags, so the BIOS is not disabling it."
    sys.exit(0)

if 'pae' in flags:
    if model == None or family == None:
        # Cannot identify CPU, fail open
        if opt.verbose:
            print >>sys.stderr, "No 'model' or 'family' were found for this CPU.  Check /proc/cpuinfo"
        sys.exit(1)
    if (family == 6 and model >= 14) or \
       (family == 15 and model >= 3) or \
       (family > 15):
        # NX should be available in CPU, but missing from flags
        if opt.verbose:
            print >>sys.stderr, '''This CPU is family %d, model %d, and has NX capabilities but is unable to
use these protective features because the BIOS is configured to disable
the capability.  Please enable this in your BIOS.  For more details, see:
''' % (family, model) + \
                'https://wiki.ubuntu.com/Security/CPUFeatures'
        sys.exit(1)
    else:
        # NX not available in CPU
        if opt.verbose:
            print >>sys.stderr, '''This CPU is family %d, model %d, and does not have NX capabilities.''' % (family, model)
        sys.exit(0)

if opt.verbose:
    print >>sys.stderr, "This CPU is not PAE capable, so it does not have NX."
sys.exit(0)
