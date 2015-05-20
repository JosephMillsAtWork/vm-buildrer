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

class Etch(suite.Suite):
    updategrub = "/usr/sbin/update-grub"
    grubroot = "/usr/lib/grub"

    valid_flavours = { 'i386' :  ['486', '686', '686-bigmem',
                                  '686-bigmem-etchnhalf', '686-etchnhalf',
                                  '686-smp', 'vserver-686'],
                       'amd64' : ['amd64', 'amd64-etchnhalf', 'amd64-generic',
                                  'amd64-k8', 'amd64-k8-smp', 'vserver-amd64',
                                  'vserver-amd64-k8-smp']}
    
    default_flavour = { 'i386' : '686-etchnhalf', 'amd64' : 'amd64-etchnhalf' }
    disk_prefix = 'sd'
    xen_kernel_flavour = 'xen'
    virtio_net = False

    ec2_kernel_info = { 'i386' : 'aki-9b00e5f2', 'amd64' : 'aki-9800e5f1' }
    ec2_ramdisk_info = { 'i386' : 'ari-cant-be-arsed', 'amd64' : 'ari-to-look-that-up' }

    def check_kernel_flavour(self, arch, flavour):
        return flavour in self.valid_flavours[arch]

    def check_arch_validity(self, arch):
        return arch in self.valid_flavours.keys()
        
    def install(self, destdir):
        self.destdir = destdir

        logging.debug("debootstrapping")
        self.debootstrap()

        logging.debug("Setting up sources.list")
        self.install_sources_list()

        logging.debug("Setting up apt proxy")
        self.install_apt_proxy()

        logging.debug("Installing fstab")
        self.install_fstab()

        logging.debug("Creating devices")
        self.create_devices()
    
        if self.vm.hypervisor.needs_bootloader:
            logging.debug("Installing grub")
            self.install_grub()
        
        logging.debug("Configuring guest networking")
        self.config_network()

        logging.debug("Preventing daemons from starting")
        self.prevent_daemons_starting()

        if self.vm.hypervisor.needs_bootloader:
            logging.debug("Installing menu.list")
            self.install_menu_lst()

            logging.debug("Installing kernel")
            self.install_kernel()

            logging.debug("Creating device.map")
            self.install_device_map()
        else:
            logging.debug("Installing kernel")
            self.install_kernel_without_bootloader()

        logging.debug("Installing extra packages")
        self.install_extras()

        logging.debug("Creating initial user")
        self.create_initial_user()

        logging.debug("Installing ssh keys")
        self.install_authorized_keys()

        logging.debug("Installing locales")
        self.install_locales()

        logging.debug("Copy host settings")
        self.copy_settings()

        logging.debug("Making sure system is up-to-date")
        self.update()

        logging.debug("Setting up final sources.list")
        self.install_sources_list(final=True)

        logging.debug("Unmounting volatile lrm filesystems")
        self.unmount_volatile()

        if hasattr(self.vm, 'ec2') and self.vm.ec2:
            logging.debug("Configuring for ec2")
            self.install_ec2()

        logging.debug("Unpreventing daemons from starting")
        self.unprevent_daemons_starting()

    def update(self):
        self.run_in_target('apt-get', '-y', '--force-yes', 'dist-upgrade',
                           env={ 'DEBIAN_FRONTEND' : 'noninteractive' })
        
    def install_authorized_keys(self):
        if self.vm.ssh_key:
            os.mkdir('%s/root/.ssh' % self.destdir, 0700)
            shutil.copy(self.vm.ssh_key, '%s/root/.ssh/authorized_keys' % self.destdir)
            os.chmod('%s/root/.ssh/authorized_keys' % self.destdir, 0644)
        if self.vm.ssh_user_key:
            os.mkdir('%s/home/%s/.ssh' % (self.destdir, self.vm.user), 0700)
            shutil.copy(self.vm.ssh_user_key, '%s/home/%s/.ssh/authorized_keys' % (self.destdir, self.vm.user))
            os.chmod('%s/home/%s/.ssh/authorized_keys' % (self.destdir, self.vm.user), 0644)
            self.run_in_target('chown', '-R', '%s:%s' % (self.vm.user,)*2, '/home/%s/.ssh/' % (self.vm.user)) 

        if self.vm.ssh_user_key or self.vm.ssh_key:
            if not self.vm.addpkg:
                self.vm.addpkg = []
            self.vm.addpkg += ['openssh-server']

    def update_passwords(self):
        # Set the user password, using md5
        self.run_in_target('chpasswd', '-m', stdin=('%s:%s\n' % (self.vm.user, getattr(self.vm, 'pass'))))

        # Lock root account only if we didn't set the root password
        if self.vm.rootpass:
            self.run_in_target('chpasswd', '-m', stdin=('%s:%s\n' % ('root', self.vm.rootpass)))
        else:
            self.run_in_target('chpasswd', '-e', stdin='root:!\n')

    def create_initial_user(self):
        self.run_in_target('adduser', '--disabled-password', '--gecos', self.vm.name, self.vm.user)
        self.run_in_target('addgroup', '--system', 'admin')
        self.run_in_target('adduser', self.vm.user, 'admin')

        self.install_from_template('/etc/sudoers', 'sudoers')
        for group in ['adm', 'audio', 'cdrom', 'dialout', 'floppy', 'video', 'plugdev', 'dip', 'netdev', 'powerdev', 'lpadmin', 'scanner']:
            self.run_in_target('adduser', self.vm.user, group, ignore_fail=True)

        self.update_passwords()

    def kernel_name(self):
        if not isinstance(self.vm.hypervisor, VMBuilder.plugins.xen.Xen):
            return 'linux-image-2.6-%s' % (self.vm.flavour or self.default_flavour[self.vm.arch],)
        else:
            return 'linux-image-2.6-%s-%s' % (self.xen_kernel_flavour, self.vm.flavour or self.default_flavour[self.vm.arch])

    def config_network(self):
        self.vm.install_file('/etc/hostname', self.vm.hostname)
        self.install_from_template('/etc/hosts', 'etc_hosts', { 'hostname' : self.vm.hostname, 'domain' : self.vm.domain }) 
        self.install_from_template('/etc/network/interfaces', 'interfaces')

    def unprevent_daemons_starting(self):
        os.unlink('%s/usr/sbin/policy-rc.d' % self.destdir)

    def prevent_daemons_starting(self):
        os.chmod(self.install_from_template('/usr/sbin/policy-rc.d', 'nostart-policy-rc.d'), 0755)

    def install_extras(self):
        if not self.vm.addpkg and not self.vm.removepkg:
            return
        cmd = ['apt-get', 'install', '-y', '--force-yes']
        cmd += self.vm.addpkg or []
        cmd += ['%s-' % pkg for pkg in self.vm.removepkg or []]
        self.run_in_target(env={ 'DEBIAN_FRONTEND' : 'noninteractive' }, *cmd)
        
    def unmount_volatile(self):
        for mntpnt in glob.glob('%s/lib/modules/*/volatile' % self.destdir):
            logging.debug("Unmounting %s" % mntpnt)
            run_cmd('umount', mntpnt)

    def install_menu_lst(self):
        run_cmd('mount', '--bind', '/dev', '%s/dev' % self.destdir)
        self.vm.add_clean_cmd('umount', '%s/dev' % self.destdir, ignore_fail=True)

        self.run_in_target('mount', '-t', 'proc', 'proc', '/proc')
        self.vm.add_clean_cmd('umount', '%s/proc' % self.destdir, ignore_fail=True)

        self.run_in_target(self.updategrub, '-y')
        self.mangle_grub_menu_lst()
        self.run_in_target(self.updategrub)
        self.run_in_target('grub-set-default', '0')

        run_cmd('umount', '%s/dev' % self.destdir)
        run_cmd('umount', '%s/proc' % self.destdir)

    def mangle_grub_menu_lst(self):
        bootdev = disk.bootpart(self.vm.disks)
        run_cmd('sed', '-ie', 's/^# kopt=root=\([^ ]*\)\(.*\)/# kopt=root=UUID=%s\\2/g' % bootdev.fs.uuid, '%s/boot/grub/menu.lst' % self.destdir)
        run_cmd('sed', '-ie', 's/^# groot.*/# groot %s/g' % bootdev.get_grub_id(), '%s/boot/grub/menu.lst' % self.destdir)
        run_cmd('sed', '-ie', '/^# kopt_2_6/ d', '%s/boot/grub/menu.lst' % self.destdir)

    def install_sources_list(self, final=False):
        if final:
            mirror, updates_mirror, security_mirror = self.vm.mirror, self.vm.mirror, self.vm.security_mirror
        else:
            mirror, updates_mirror, security_mirror = self.install_mirrors()

        self.install_from_template('/etc/apt/sources.list', 'sources.list', { 'mirror' : mirror, 'security_mirror' : security_mirror, 'updates_mirror' : updates_mirror })

        # If setting up the final mirror, allow apt-get update to fail
        # (since we might be on a complete different network than the
        # final vm is going to be on).
        self.run_in_target('apt-get', 'update', ignore_fail=final)

    def install_apt_proxy(self):
        if self.vm.proxy is not None:
            self.vm.install_file('/etc/apt/apt.conf', '// Proxy added by vmbuilder\nAcquire::http { Proxy "%s"; };' % self.vm.proxy)

    def install_fstab(self):
        if self.vm.hypervisor.preferred_storage == VMBuilder.hypervisor.STORAGE_FS_IMAGE:
            self.install_from_template('/etc/fstab', 'etch_fstab_fsimage', { 'fss' : disk.get_ordered_filesystems(self.vm), 'prefix' : self.disk_prefix })
        else:
            self.install_from_template('/etc/fstab', 'etch_fstab', { 'parts' : disk.get_ordered_partitions(self.vm.disks), 'prefix' : self.disk_prefix })

    def install_device_map(self):
        self.install_from_template('/boot/grub/device.map', 'devicemap', { 'prefix' : self.disk_prefix })

    def debootstrap(self):
        cmd = ['/usr/sbin/debootstrap', '--arch=%s' % self.vm.arch]
        if self.vm.variant:
            cmd += ['--variant=%s' % self.vm.variant]
        cmd += [self.vm.suite, self.destdir, self.debootstrap_mirror()]
        kwargs = { 'env' : { 'DEBIAN_FRONTEND' : 'noninteractive' } }
        if self.vm.proxy:
            kwargs['env']['http_proxy'] = self.vm.proxy
        run_cmd(*cmd, **kwargs)
    
    def debootstrap_mirror(self):
        if self.vm.iso:
            isodir = tempfile.mkdtemp()
            self.vm.add_clean_cb(lambda:os.rmdir(isodir))
            run_cmd('mount', '-o', 'loop', '-t', 'iso9660', self.vm.iso, isodir)
            self.vm.add_clean_cmd('umount', isodir)
            self.iso_mounted = True

            return 'file://%s' % isodir
        else:
            return self.install_mirrors()[0]


    def install_mirrors(self):
        if self.vm.iso:
            mirror = "file:///isomnt"
        elif self.vm.install_mirror:
            mirror = self.vm.install_mirror
        else:
            mirror = self.vm.mirror

        if self.vm.install_mirror:
            updates_mirror = self.vm.install_mirror
        else:
            updates_mirror = self.vm.mirror

        if self.vm.install_security_mirror:
            security_mirror = self.vm.install_security_mirror
        else:
            security_mirror = self.vm.security_mirror

        return (mirror, updates_mirror, security_mirror)

    def install_kernel(self):
        self.install_from_template('/etc/kernel-img.conf', 'kernelimg', { 'updategrub' : self.updategrub }) 
        run_cmd('chroot', self.destdir, 'apt-get', '--force-yes', '-y', 'install', self.kernel_name(), 'grub')

    def install_kernel_without_bootloader(self):
        self.install_from_template('/etc/kernel-img.conf', 'kernelimg', { 'updategrub' : '/bin/true' }) 
        run_cmd('chroot', self.destdir, 'apt-get', '--force-yes', '-y', 'install', self.kernel_name())

    def install_grub(self):
        self.run_in_target('apt-get', '--force-yes', '-y', 'install', 'grub')
        run_cmd('cp', '-a', '%s%s/%s/' % (self.destdir, self.grubroot, self.vm.arch == 'amd64' and 'x86_64-pc' or 'i386-pc'), '%s/boot/grub' % self.destdir) 


    def install_locales(self):
        self.run_in_target('apt-get', '--force-yes', '-y', 'install', 'locales')

    def create_devices(self):
        import VMBuilder.plugins.xen

        if isinstance(self.vm.hypervisor, VMBuilder.plugins.xen.Xen):
            self.run_in_target('mknod', '/dev/xvda', 'b', '202', '0')
            self.run_in_target('mknod', '/dev/xvda1', 'b', '202', '1')
            self.run_in_target('mknod', '/dev/xvda2', 'b', '202', '2')
            self.run_in_target('mknod', '/dev/xvda3', 'b', '202', '3')
            self.run_in_target('mknod', '/dev/xvc0', 'c', '204', '191')

    def install_from_template(self, *args, **kwargs):
        return self.vm.distro.install_from_template(*args, **kwargs)

    def run_in_target(self, *args, **kwargs):
        self.vm.distro.run_in_target(*args, **kwargs)

    def copy_to_target(self, infile, destpath):
        logging.debug("Copying %s on host to %s in guest" % (infile, destpath))
        dir = '%s/%s' % (self.destdir, os.path.dirname(destpath))
        if not os.path.isdir(dir):
            os.makedirs(dir)
        if os.path.isdir(infile):
            shutil.copytree(infile, '%s/%s' % (self.destdir, destpath))
        else:
            shutil.copy(infile, '%s/%s' % (self.destdir, destpath))

    def post_mount(self, fs):
        if fs.mntpnt == '/':
            logging.debug("Creating /var/run in root filesystem")
            os.makedirs('%s/var/run' % fs.mntpath)
            logging.debug("Creating /var/lock in root filesystem")
            os.makedirs('%s/var/lock' % fs.mntpath)


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
            self.run_in_target('locale-gen', self.vm.lang)
            self.install_from_template('/etc/default/locale', 'locale', { 'lang' : self.vm.lang })
        self.run_in_target('dpkg-reconfigure', '-fnoninteractive', '-pcritical', 'locales')
        if have_cs:
            self.run_in_target('dpkg-reconfigure', '-fnoninteractive', '-pcritical', 'console-setup')

    def install_vmbuilder_log(self, logfile, rootdir):
        shutil.copy(logfile, '%s/var/log/vmbuilder-install.log' % (rootdir,))

    def install_ec2(self):
	#Mostly ported over from the Ubuntu install_ec2 commands
        #TODO: etch doesn't use Upstart, port over to init scripts
        #Basically, it makes it setup a getty console on xvc0
        #self.install_from_template('/etc/event.d/xvc0', 'upstart', { 'console' : 'xvc0' })
        #TODO: Debian bug 420726 may effect this next line since Etch has libc < 2.5-5
        self.install_from_template('/etc/ld.so.conf.d/libc6-xen.conf', 'xen-ld-so-conf')
        self.run_in_target('update-rc.d', '-f', 'hwclockfirst.sh', 'remove')
        #TODO: Change to Debian appropriate MOTD
        #self.install_from_template('/etc/update-motd.d/51_update-motd', '51_update-motd-hardy')
        #self.run_in_target('chmod', '755', '/etc/update-motd.d/51_update-motd')

    def disable_hwclock_access(self):
        #Selflessly stolen from dapper.py.
        #Needed for EC2 usage.
        fp = open('%s/etc/default/rcS' % self.destdir, 'a')
        fp.write('HWCLOCKACCESS=no')
        fp.close()
