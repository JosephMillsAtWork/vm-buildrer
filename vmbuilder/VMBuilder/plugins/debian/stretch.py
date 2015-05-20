from   VMBuilder.plugins.debian.jessie import Jessie
class Stretch(Jessie):
    updategrub = "/usr/sbin/update-grub"
    grubroot = "/usr/lib/grub"
    valid_flavours = { 'i386' :  ['386', '686', '686-smp', 'generic', 'k7', 'k7-smp', 'server', 'server-bigiron', 'lowlatency'],
                       'amd64' : ['amd64-generic', 'amd64-k8', 'amd64-k8-smp', 'amd64-server', 'amd64-xeon', 'server']}
    default_flavour = { 'i386' : '686-pae', 'amd64' : 'amd64' }
    kernel_version = '3.16.0-4'
    disk_prefix = 'sd'
    