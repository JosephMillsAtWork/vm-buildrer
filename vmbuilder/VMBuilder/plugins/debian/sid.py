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
from   VMBuilder.plugins.debian.stretch import Stretch
class Sid(Stretch):
    updategrub = "/usr/sbin/update-grub"
    grubroot = "/usr/lib/grub"
    kernel_version = '3.16.0-4'
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
    disk_prefix = 'sd'