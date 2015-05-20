#!/bin/sh
# Copyright (C) 2009-2010 Canonical, Ltd.
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
set -e
export LANG=C

usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help  show this help message and exit"
    echo "  --verbose   Explain in detail what has been detected"
}

VERBOSE=
verbose() {
    if [ -n "$VERBOSE" ]; then
        echo "$@" >&2
    fi
}

TEMP=$(getopt -o h --long verbose,help -n check-bios-nx -- "$@")
eval set -- "$TEMP"

while :; do
    case "$1" in
        -h|--help) usage ; exit 0 ;;
        --verbose) VERBOSE=1; shift ;;
        --) shift ; break ;;
        *) usage >&2 ; exit 2 ;;
    esac
done

ARCH=${CHECK_BIOS_NX_MACHINE:-$(uname -m)}
if ! echo "$ARCH" | egrep -q '^(i.86|x86_64)$' ; then
    verbose "This script is currently only useful on x86-based CPUs"
    exit 0
fi

# Avoid calling grep/head/awk 3 times in a row, thanks to Jamie Strandboge
# and Steve Beattie.
set -- $(awk 'BEGIN { FS=": " ; family = "0" ; model = "0" ; flags = "-" } \
     family == "0" && /^cpu family\t/ { family = $2 } \
     model  == "0" && /^model\t/      { model = $2 } \
     flags  == "-" && /^flags\t/      { flags = $2 } \
     END { print family; print model; print flags }' \
    ${CHECK_BIOS_NX_CPUINFO:-/proc/cpuinfo})
family=$1
model=$2
shift 2
flags=$*

if [ -z "$flags" ]; then
    # No flags found (?!), fail open
    verbose "No 'flags' were found for this CPU.  Check /proc/cpuinfo"
    exit 1
fi

# If it's in the flags, it's not being disabled by the BIOS; rejoice.
if echo " $flags " | grep -q ' nx ' ; then
    verbose "This CPU has 'nx' in the flags, so the BIOS is not disabling it."
    exit 0
fi

if echo " $flags " | grep -q ' pae ' ; then
    if [ -z "$model" ] || [ -z "$family" ]; then
        # Cannot identify CPU, fail open
        verbose "No 'model' or 'family' were found for this CPU.  Check /proc/cpuinfo"
        exit 1
    fi

    if ([ $family -eq 6 ] && [ $model -ge 14 ]) || \
       ([ $family -eq 15 ] && [ $model -ge 3]) || \
       [ $family -gt 15 ]; then
        # NX should be available in CPU, but missing from flags
        echo "This CPU is family $family, model $model, and has NX capabilities but is unable to" >&2
        echo "use these protective features because the BIOS is configured to disable" >&2
        echo "the capability.  Please enable this in your BIOS.  For more details, see:" >&2
        echo "https://wiki.ubuntu.com/Security/CPUFeatures" >&2
        exit 1
    else
        # NX not available in CPU
        verbose "This CPU is family $family, model $model, and does not have NX capabilities."
        exit 0
    fi

fi

verbose "This CPU is not PAE capable, so it does not have NX."
exit 0
