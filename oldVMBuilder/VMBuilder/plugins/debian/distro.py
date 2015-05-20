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
import logging
import os, os.path
import socket
import types
import VMBuilder
from   VMBuilder           import register_distro, Distro
from   VMBuilder.util      import run_cmd
from   VMBuilder.exception import VMBuilderUserError, VMBuilderException

class Debian(Distro):
    name = 'Debian'
    arg = 'debian'
    suites = ['etch', 'lenny']
    
    # Maps host arch to valid guest archs
    # FIXME: Running a amd64 kernel with an i386 userspace allows us to run
    #        amd64 guests
     
    valid_archs = { 'amd64' : ['amd64', 'i386' ],
                    'i386' : [ 'i386' ] }

    xen_kernel = ''
    kernel = ''

    def register_options(self):
        group = self.vm.setting_group('Package options')
        group.add_option('--addpkg', action='append', metavar='PKG', help='Install PKG into the guest (can be specfied multiple times).')
        group.add_option('--removepkg', action='append', metavar='PKG', help='Remove PKG from the guest (can be specfied multiple times)')
        self.vm.register_setting_group(group)

        group = self.vm.setting_group('General OS options')
        self.host_arch = run_cmd('dpkg', '--print-architecture').rstrip()
        group.add_option('-a', '--arch', default=self.host_arch, help='Specify the target architecture.  Valid options: amd64 i386 (defaults to host arch)')
        group.add_option('--hostname', default='debian', help='Set NAME as the hostname of the guest. Default: debian. Also uses this name as the VM name.')
        self.vm.register_setting_group(group)

        # FIXME: Add Debian ports 
        # FIXME: Add volatile
        group = self.vm.setting_group('Installation options')
        group.add_option('--suite', default='etch', help='Suite to install. Valid options: %s [default: %%default]' % ' '.join(self.suites))
        group.add_option('--flavour', '--kernel-flavour', help='Kernel flavour to use. Default and valid options depend on architecture and suite')
        group.add_option('--variant', metavar='VARIANT', help='Passed to debootstrap --variant flag; use minbase, buildd, or fakechroot.')
        group.add_option('--iso', metavar='PATH', help='Use an iso image as the source for installation of file. Full path to the iso must be provided. If --mirror is also provided, it will be used in the final sources.list of the vm.  This requires suite and kernel parameter to match what is available on the iso, obviously.')
        group.add_option('--mirror', metavar='URL', help='Use Debian mirror at URL instead of the default, which is http://ftp.debian.org for official arches.')
        group.add_option('--proxy', metavar='URL', help='Use proxy at URL for cached packages')
        group.add_option('--install-mirror', metavar='URL', help='Use Debian mirror at URL for the installation only. Apt\'s sources.list will still use default or URL set by --mirror')
        group.add_option('--security-mirror', metavar='URL', help='Use Debian security mirror at URL instead of the default, which is http://security.debian.org/debian-security/ for official arches.')
        group.add_option('--install-security-mirror', metavar='URL', help='Use the security mirror at URL for installation only. Apt\'s sources.list will still use default or URL set by --security-mirror')
        group.add_option('--components', metavar='COMPS', help='A comma seperated list of distro components to include (e.g. main,contrib,non-free).')
        group.add_option('--lang', metavar='LANG', default=self.get_locale(), help='Set the locale to LANG [default: %default]')
        self.vm.register_setting_group(group)

        group = self.vm.setting_group('Settings for the initial user')
        group.add_option('--user', default='debian', help='Username of initial user [default: %default]')
        group.add_option('--name', default='Debian', help='Full name of initial user [default: %default]')
        group.add_option('--pass', default='debian', help='Password of initial user [default: %default]')
        group.add_option('--rootpass', help='Initial root password (WARNING: this has strong security implications).')
        self.vm.register_setting_group(group)

        group = self.vm.setting_group('Other options')
        group.add_option('--ssh-key', metavar='PATH', help='Add PATH to root\'s ~/.ssh/authorized_keys (WARNING: this has strong security implications).')
        group.add_option('--ssh-user-key', help='Add PATH to the user\'s ~/.ssh/authorized_keys.')
        self.vm.register_setting_group(group)

    def set_defaults(self):
        if not self.vm.mirror:
            #if self.vm.arch == 'lpia':
            #    self.vm.mirror = 'http://ports.ubuntu.com/ubuntu-ports'
            #else:
            self.vm.mirror = 'http://ftp.debian.org/debian'

        if not self.vm.security_mirror:
            #if self.vm.arch == 'lpia':
            #    self.vm.security_mirror = 'http://ports.ubuntu.com/ubuntu-ports'
            #else:
            self.vm.security_mirror = 'http://security.debian.org/debian-security'

        if not self.vm.components:
            self.vm.components = ['main']
        else:
            self.vm.components = self.vm.components.split(',')

    def get_locale(self):
        return os.getenv('LANG')

    def preflight_check(self):
        """While not all of these are strictly checks, their failure would inevitably
        lead to failure, and since we can check them before we start setting up disk
        and whatnot, we might as well go ahead an do this now."""

        if not self.vm.suite in self.suites:
            raise VMBuilderUserError('Invalid suite. Valid suites are: %s' % ' '.join(self.suites))
        
        modname = 'VMBuilder.plugins.debian.%s' % (self.vm.suite, )
        mod = __import__(modname, fromlist=[self.vm.suite])
        self.suite = getattr(mod, self.vm.suite.capitalize())(self.vm)

        if self.vm.arch not in self.valid_archs[self.host_arch] or  \
            not self.suite.check_arch_validity(self.vm.arch):
            raise VMBuilderUserError('%s is not a valid architecture. Valid architectures are: %s' % (self.vm.arch, 
                                                                                                      ' '.join(self.valid_archs[self.host_arch])))

        if not self.vm.components:
            self.vm.components = ['main', 'contrib']
        else:
            if type(self.vm.components) is str:
                self.vm.components = self.vm.components.split(',')

        if self.vm.hypervisor.name == 'Xen':
            logging.info('Xen kernel default: linux-image-2.6-%s-%s', self.suite.xen_kernel_flavour, self.suite.default_flavour[self.vm.arch])

        self.vm.virtio_net = self.use_virtio_net()

        if self.vm.lang:
            try:
                run_cmd('locale-gen', '%s' % self.vm.lang)
            except VMBuilderException, e:
                msg = "locale-gen does not recognize your locale '%s'" % self.vm.lang
                raise VMBuilderUserError(msg)

        if hasattr(self.vm, "ec2") and self.vm.ec2:
            self.get_ec2_kernel()
            self.get_ec2_ramdisk()

    def install(self, destdir):
        self.destdir = destdir
        self.suite.install(destdir)

    def install_vmbuilder_log(self, logfile, rootdir):
        self.suite.install_vmbuilder_log(logfile, rootdir)

    def post_mount(self, fs):
        self.suite.post_mount(fs)

    def use_virtio_net(self):
        return self.suite.virtio_net

    def install_bootloader(self):
        devmapfile = '%s/device.map' % self.vm.workdir
        devmap = open(devmapfile, 'w')
        for (disk, id) in zip(self.vm.disks, range(len(self.vm.disks))):
            devmap.write("(hd%d) %s\n" % (id, disk.filename))
        devmap.close()
        run_cmd('grub', '--device-map=%s' % devmapfile, '--batch',  stdin='''root (hd0,0)
setup (hd0)
EOT''')

    def find_linux_kernel(self, suite, flavour, arch):
        if flavour == None:
            rmad = run_cmd('rmadison', 'linux-image-2.6-%s' % (arch))
        else:
            rmad = run_cmd('rmadison', 'linux-image-2.6-%s-%s' % (flavour, arch))
        version = ['0', '0','0', '0']

        for line in rmad.splitlines():
            sline = line.split('|')
                    
            #Linux XEN kernel is referred to in Debian by rmadison as:
            #linux-image-2.6-xen-amd64 | 2.6.18+6etch3 |     oldstable | amd64
            #Specifically, etch is called 'oldstable' in the 3rd field, to get the suite you need
            #excavate it from the 2nd field.

            if sline[1].strip().count(suite) > 0:
                #Fix for Debian handling of kernel version names
                #It's x.y.z+w, not x.y.z.w
                vt = sline[1].strip().split('.')
                deb_vt = vt[2].split('+')
                vt = [vt[0], vt[1], deb_vt[0], deb_vt[1]]

                for i in range(4):
                    if int(vt[i]) > int(version[i]):
                        version = vt
                        break

        if version[0] != '0':
            return '%s.%s.%s-%s' % (version[0],version[1],version[2],version[3])
        else:
            return None

    def xen_kernel_version(self):
        if self.suite.xen_kernel_flavour:
            if not self.xen_kernel:
                logging.debug("Searching for %s-%s flavour Xen kernel..." % (self.suite.xen_kernel_flavour, self.suite.default_flavour[self.vm.arch]))
                xen_kernel = self.find_linux_kernel(self.vm.suite, self.suite.xen_kernel_flavour, self.suite.default_flavour[self.vm.arch])

                if xen_kernel == None:
                    logging.debug('Default Xen kernel flavour %s-%s is not available for this suite.' % (self.suite.xen_kernel_flavour, self.suite.default_flavour[self.vm.arch]))
                    if self.suite.valid_flavours[self.vm.arch] > 0:
                        for flavour in self.suite.valid_flavours[self.vm.arch]:
                            if flavour != self.suite.default_flavour[self.vm.arch]:
                                logging.debug("Trying alternate flavour %s-%s..." % (self.suite.xen_kernel_flavour, flavour))
                                xen_kernel = self.find_linux_kernel(self.vm.suite, self.suite.xen_kernel_flavour, self.suite.default_flavour[self.vm.arch])
                                if xen_kernel != None:
                                    logging.info("Using Xen kernel linux-image-2.6-%s-%s, package version %s" % (self.suite.xen_kernel_flavour, flavour, xen_kernel))
                                    break
                else:
                    logging.info("Using Xen kernel linux-image-2.6-%s-%s, package version %s" % (self.suite.xen_kernel_flavour, self.suite.default_flavour[self.vm.arch], xen_kernel))

                if xen_kernel == None:
                    raise VMBuilderException('There is no valid Xen kernel for the suite selected.')
                
                self.xen_kernel = xen_kernel
            return self.xen_kernel
        else:
            raise VMBuilderUserError('There is no valid xen kernel for the suite selected.')

    #Ugly kludge to avoid breaking old code that relies on xen_kernel_path

    def kernel_path(self):
        if not isinstance(self.vm.hypervisor, VMBuilder.plugins.xen.Xen):
            return self.__kernel_path()
        else:
            return self.xen_kernel_path()

    def ramdisk_path(self):
        if not isinstance(self.vm.hypervisor, VMBuilder.plugins.xen.Xen):
            return self.__ramdisk_path()
        else:
            return self.xen_ramdisk_path()

    def __kernel_path(self):
        kernels = run_cmd("ls", "%s/boot/" % self.vm.installdir)

        for kernel in kernels.split("\n"):
            k_filename_parts = kernel.split("-")

            if k_filename_parts[0] == "vmlinuz":
                if k_filename_parts[3] in self.suite.valid_flavours[self.vm.arch]:
                    return "/boot/%s" % kernel

        return None

    def __ramdisk_path(self):
        kernels = run_cmd("ls", "%s/boot/" % self.vm.installdir)

        for kernel in kernels.split("\n"):
            k_filename_parts = kernel.split("-")

            if k_filename_parts[0] == "initrd.img":
                if k_filename_parts[3] in self.suite.valid_flavours[self.vm.arch]:
                    return "/boot/%s" % kernel

        return None

    def xen_kernel_path(self):
        kernels = run_cmd("ls", "%s/boot/" % self.vm.installdir)

        for kernel in kernels.split("\n"):
            k_filename_parts = kernel.split("-")

            if k_filename_parts[0] == "vmlinuz":
                if k_filename_parts[3] == self.suite.xen_kernel_flavour:
                    if k_filename_parts[4] in self.suite.valid_flavours[self.vm.arch]:
                        return "/boot/%s" % kernel

        return None

    def xen_ramdisk_path(self):
        kernels = run_cmd("ls", "%s/boot/" % self.vm.installdir)

        for kernel in kernels.split("\n"):
            k_filename_parts = kernel.split("-")

            if k_filename_parts[0] == "initrd.img":
                if k_filename_parts[3] == self.suite.xen_kernel_flavour:
                    if k_filename_parts[4] in self.suite.valid_flavours[self.vm.arch]:
                        return "/boot/%s" % kernel

        return None

    def get_ec2_kernel(self):
        if self.suite.ec2_kernel_info:
            return self.suite.ec2_kernel_info[self.vm.arch]
        else:
            raise VMBuilderUserError('EC2 is not supported for the suite selected')

    def get_ec2_ramdisk(self):
        if self.suite.ec2_ramdisk_info:
            return self.suite.ec2_ramdisk_info[self.vm.arch]
        else:
            raise VMBuilderUserError('EC2 is not supported for the suite selected')

    def disable_hwclock_access(self):
        return self.suite.disable_hwclock_access()

register_distro(Debian)
