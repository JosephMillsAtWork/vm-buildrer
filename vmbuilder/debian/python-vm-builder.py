#!/usr/bin/python

'''VMBuilder Apport interface

Copyright (C) 2010 Canonical Ltd.
Author: Chuck Short <chuck.short@canonical.com>

This program is free software, you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the Licenes, or (at your option) any later version. See http://www.gnu.org/copyleft/gpl.html for the full text of the license.
'''

import os
import subprocess
from apport.hookutils import *

def add_info(report, ui):
	attach_related_packages(report, ['qemu-kvm', 'debootstrap', 'parted', 'kpartx', 'ubuntu-keyring', 'rsync'])
	
	ui.information("Please attach the command line that you used to generate your virtual machine")

