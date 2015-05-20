# -*- coding: utf-8 -*-
#
#    Uncomplicated VM Builder
#    Copyright (C) 2007-2008 Canonical Ltd.
#    Copyright (C) 2009      Bernd Zeimetz <bzed@debian.org>
#    
#    See AUTHORS for list of contributors
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import glob
import logging
import os
import shutil
import socket
import tempfile
import VMBuilder
import VMBuilder.disk as disk
import VMBuilder.suite as suite
from   VMBuilder.util import run_cmd
from   VMBuilder.plugins.debian.etch import Etch

class Lenny(Etch):
    valid_flavours = { 'i386' :  ['486', '686', '686-bigmem'],
                       'amd64' : ['amd64']}
    default_flavour = { 'i386' : '686', 'amd64' : 'amd64' }
    xen_kernel_flavour = 'xen'

    def install(self, destdir):
        Etch.install(self, destdir)
        logging.debug("HERE, DOES IT CRASH BEFORE OR AFTER THIS???")

    def install_menu_lst(self):
        # This is now done in debootstrap 
        #run_cmd('mount', '--bind', '/dev', '%s/dev' % self.destdir)
        #self.vm.add_clean_cmd('umount', '%s/dev' % self.destdir, ignore_fail=True)

        #run_cmd('mount', '-t', 'proc', 'proc', '%s/proc' % self.destdir)
        #self.vm.add_clean_cmd('umount', '%s/proc' % self.destdir, ignore_fail=True)

        self.run_in_target(self.updategrub, '-y')
        self.mangle_grub_menu_lst()
        self.run_in_target(self.updategrub)
        self.run_in_target('grub-set-default', '0')
        self.fix_grub_menu_lst_root()

        # These mounts are still required later
        #run_cmd('umount', '%s/dev' % self.destdir)
        #run_cmd('umount', '%s/proc' % self.destdir)

    def install_locales(self):
        self.run_in_target('apt-get', '--force-yes', '-y', 'install', 'locales')

    def debootstrap(self):
        Etch.debootstrap(self)
        self.bind_system_devices()

    def bind_system_devices(self):
        #Mounts the system's /dev, /dev/pts, and /proc on top of ours.
        #Also adds the appropriate umount commands to the cleanup phase.
        if not hasattr(self, "system_devices_mounted") or not self.system_devices_mounted:
            run_cmd('mount', '--bind', '/dev', '%s/dev' % self.destdir)
            self.vm.add_clean_cmd('umount', '%s/dev' % self.destdir, ignore_fail=True)

            run_cmd('mount', '--bind', '/dev/pts', '%s/dev/pts' % self.destdir)
            self.vm.add_clean_cmd('umount', '%s/dev/pts' % self.destdir, ignore_fail=True)

            run_cmd('mount', '-t', 'proc', 'proc', '%s/proc' % self.destdir)
            self.vm.add_clean_cmd('umount', '%s/proc' % self.destdir, ignore_fail=True)

            self.system_devices_mounted = True

    def unbind_system_devices(self):
        #Opposite of bind_system_devices.
        #Also removes the cleanup commands.
        if hasattr(self, "system_devices_mounted") and self.system_devices_mounted:
            run_cmd('umount', '%s/dev/pts' % self.destdir)
            #self.vm.remove_clean_cmd('umount', '%s/dev/pts' % self.destdir, ignore_fail=True)

            run_cmd('umount', '%s/dev' % self.destdir)
            #self.vm.remove_clean_cmd('umount', '%s/dev' % self.destdir, ignore_fail=True)

            run_cmd('umount', '%s/proc' % self.destdir)
            #self.vm.remove_clean_cmd('umount', '%s/proc' % self.destdir, ignore_fail=True)

            self.system_devices_mounted = False

    def copy_settings(self):
        self.copy_to_target('/etc/default/locale', '/etc/default/locale')
        csdir = '%s/etc/console-setup' % self.destdir
        have_cs = os.path.isdir(csdir)
        if have_cs:
            shutil.rmtree(csdir)
            self.copy_to_target('/etc/console-setup', '/etc/console-setup')
            self.copy_to_target('/etc/default/console-setup', '/etc/default/console-setup')
        self.copy_to_target('/etc/timezone', '/etc/timezone')
        self.run_in_target('dpkg-reconfigure', '-fnoninteractive', '-pcritical', 'tzdata')
        self.run_in_target('locale-gen', 'en_US.UTF-8')
        if self.vm.lang:
            encoding = self.vm.lang[self.vm.lang.rfind(".")+1:]
            open('%s/etc/locale.gen' % self.destdir,'a').write("\n%s %s" %(self.vm.lang, encoding))
            self.run_in_target('locale-gen', self.vm.lang)
            self.install_from_template('/etc/default/locale', 'locale', { 'lang' : self.vm.lang })
        self.run_in_target('dpkg-reconfigure', '-fnoninteractive', '-pcritical', 'locales')
        if have_cs:
            self.run_in_target('dpkg-reconfigure', '-fnoninteractive', '-pcritical', 'console-setup')

    def unmount_volatile(self):
        for mntpnt in glob.glob('%s/lib/modules/*/volatile' % self.destdir):
            logging.debug("Unmounting %s" % mntpnt)
            run_cmd('umount', mntpnt)

        # Finally unmounting /dev and /proc. Maybe not very clean to do that here.
        run_cmd('umount', '%s/dev/pts' % self.destdir)
        run_cmd('umount', '%s/dev' % self.destdir)
        run_cmd('umount', '%s/proc' % self.destdir)
        
    def install_kernel(self):
        Etch.install_kernel(self)
        self.fix_grub_menu_lst_root()

    def fix_grub_menu_lst_root(self):
        # Extremely dirty hack to fix the root parameters in menu.lst to (hd0,0)
        bootdev = disk.bootpart(self.vm.disks)
        run_cmd('sed', '-ie', 's/([^)]*)/(hd0,0)/', '%s/boot/grub/menu.lst' % self.destdir)

    def create_devices(self):
        #Having system devices bound makes device creation fail.
        self.unbind_system_devices()
        Etch.create_devices(self)
        self.bind_system_devices()
        
