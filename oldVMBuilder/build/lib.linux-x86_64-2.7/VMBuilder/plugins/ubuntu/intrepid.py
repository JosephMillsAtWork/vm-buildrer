#
#    Uncomplicated VM Builder
#    Copyright (C) 2007-2009 Canonical Ltd.
#    
#    See AUTHORS for list of contributors
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License version 3, as
#    published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import logging
import VMBuilder.disk as disk
import VMBuilder.suite as suite
from   VMBuilder.util import run_cmd
from   VMBuilder.plugins.ubuntu.hardy import Hardy

class Intrepid(Hardy):
    valid_flavours = { 'i386' :  ['386', 'generic', 'server', 'virtual'],
                       'amd64' : ['generic', 'server', 'virtual'],
                       'lpia'  : ['lpia', 'lpiacompat'] }
    default_flavour = { 'i386' : 'virtual', 'amd64' : 'virtual', 'lpia' : 'lpia' }
    xen_kernel_flavour = 'virtual'
    ec2_kernel_info = { 'i386' : 'aki-714daa18', 'amd64' : 'aki-4f4daa26' }
    ec2_ramdisk_info = { 'i386': 'ari-7e4daa17', 'amd64' : 'ari-4c4daa25' }

    def install_ec2(self):
# workaround for policy bug on ubuntu-server. (see bug #275432)
        self.run_in_target('apt-get', '--force-yes', '-y', 'install', 'policykit')
        self.run_in_target('apt-get', '--force-yes', '-y', 'install', 'server^')
        self.install_from_template('/etc/update-motd.d/51_update-motd', '51_update-motd')
        self.run_in_target('chmod', '755', '/etc/update-motd.d/51_update-motd')

    def mangle_grub_menu_lst(self):
        bootdev = disk.bootpart(self.vm.disks)
        run_cmd('sed', '-ie', 's/^# kopt=root=\([^ ]*\)\(.*\)/# kopt=root=UUID=%s\\2/g' % bootdev.fs.uuid, '%s/boot/grub/menu.lst' % self.destdir)
        run_cmd('sed', '-ie', 's/^# groot.*/# groot=%s/g' % bootdev.fs.uuid, '%s/boot/grub/menu.lst' % self.destdir)
        run_cmd('sed', '-ie', '/^# kopt_2_6/ d', '%s/boot/grub/menu.lst' % self.destdir)

    def install_xen_kernel(self):
	import VMBuilder.plugins.xen

	if isinstance(self.vm.hypervisor, VMBuilder.plugins.xen.Xen):
	   logging.info('Skipping Xen kernel installation.')
