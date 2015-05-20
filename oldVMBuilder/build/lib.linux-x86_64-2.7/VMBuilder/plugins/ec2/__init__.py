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
import VMBuilder
from   VMBuilder import register_plugin, Plugin, VMBuilderUserError, VMBuilderException
from   VMBuilder.util import run_cmd
import logging
import os

class EC2(Plugin):
    name = 'EC2 integration'

    def register_options(self):
        group = self.vm.setting_group('EC2 and Eucalyptus support')
        group.add_option('--ec2', action='store_true', help='Build for EC2')
        group.add_option('--ec2-name','--ec2-prefix', metavar='EC2_NAME', help='Name for the EC2 image.')
        group.add_option('--ec2-cert', metavar='CERTFILE', help='PEM encoded public certificate for EC2.')
        group.add_option('--ec2-key', metavar='KEYFILE', help='PEM encoded private key for EC2.')
        group.add_option('--ec2-user', metavar='AWS_ACCOUNT', help='EC2 user ID (a.k.a. AWS account number, not AWS access key ID).')
        group.add_option('--ec2-bucket', metavar='BUCKET', help='S3 bucket to hold the AMI.')
        group.add_option('--ec2-access-key', metavar='ACCESS_ID', help='AWS access key ID.')
        group.add_option('--ec2-secret-key', metavar='SECRET_ID', help='AWS secret access key.')
        group.add_option('--ec2-kernel','--ec2-aki', metavar='AKI', help='EC2 AKI (kernel) to use.')
        group.add_option('--ec2-ramdisk','--ec2-ari', metavar='ARI', help='EC2 ARI (ramdisk) to use.')
        group.add_option('--ec2-version', metavar='EC2_VER', help='Specify the EC2 image version.')
        group.add_option('--ec2-landscape', action='store_true', help='Install landscape client support')
        group.add_option('--ec2-bundle', action='store_true', help='Bundle the instance')
        group.add_option('--ec2-upload', action='store_true', help='Upload the instance')
        group.add_option('--ec2-register', action='store_true', help='Register the instance')
        group.add_option('--ec2-no-amazon-tools', action='store_true', help='Do not use Amazon\'s EC2 AMI tools.')
        group.add_option('--ec2-no-euca-tools', action='store_true', help='Do not use Eucalyptus\' EC2 AMI tools.')
        group.add_option('--ec2-url', metavar='EC2_URL', help='URL of EC2 or compatible cluster.')
        group.add_option('--ec2-s3-url', metavar='S3_URL', help='URL of EC2 or compatible cluster\'s S3 server.')
        group.add_option('--ec2-cloud-cert', metavar='EUCALYPTUS_CERT', help='Certificate of EC2-compatible cluster.')
        group.add_option('--ec2-is-eucalyptus', action='store_true', help='Allow the use of Eucalyptus-specific features like KVM.')
        group.add_option('--ec2-bundle-kernel', action='store_true', help='Bundle the kernel and ramdisk.')
        group.add_option('--ec2-upload-kernel', action='store_true', help='Upload the kernel and ramdisk.')
        group.add_option('--ec2-register-kernel', action='store_true', help='Register the kernel and ramdisk')
        self.vm.register_setting_group(group)

    def preflight_check(self):
        if not getattr(self.vm, 'ec2', False):
            return True

        #NOW, actually check if we can do EC2. Also check if we can take advantage of Euca's KVM support
        if not isinstance(self.vm.hypervisor, VMBuilder.plugins.xen.Xen):
            if not self.vm.ec2_is_eucalyptus:
                raise VMBuilderUserError("You must use Xen on EC2")
            elif not isinstance(self.vm.hypervisor, VMBuilder.plugins.kvm.vm.KVM):
                raise VMBuilderUserError("You must use either Xen or KVM on Eucalyptus")

        if self.vm.ec2_no_amazon_tools:
            logging.info("Not using Amazon ec2-tools.")
            awsec2_installed = False
        else:
            try:
                run_cmd('ec2-ami-tools-version')
            except OSError, VMBuilderException:
                awsec2_installed = False
            else:
                awsec2_installed = True

        if self.vm.ec2_no_euca_tools:
            logging.info("Not using Eucalyptus euca2ools.")
            euca_installed = False
        else:
            try: #TODO: Fix this so that it doesn't use running d-a-z as a we-have-euca2ools check
                run_cmd('euca-describe-availability-zones')
            except OSError, VMBuilderException:
                euca_installed = False
            else:
                euca_installed = True

        if euca_installed:
            self.ec2_tools_prefix = "euca-"
        elif awsec2_installed:
            self.ec2_tools_prefix = "ec2-"
        else:
            if self.vm.ec2_bundle or self.vm.ec2_upload:
                raise VMBuilderUserError('When bundling or uploading for EC2 you must have ec2-tools or euca2ools installed.')
            else:
                logging.warn('You do not have a suitable AMI tools suite installed, however, the current operation does not require it.')
                self.ec2_tools_prefix = None

        if self.ec2_tools_prefix:
            logging.info("Using EC2 tools prefix: %s" % self.ec2_tools_prefix)

        if self.vm.ec2_bundle:
            if not self.vm.ec2_name:
                raise VMBuilderUserError('When building for EC2 you must supply the name for the image.')

            if not self.vm.ec2_url and "EC2_URL" in os.environ:
                self.vm.ec2_url = os.environ["EC2_URL"]

            if not self.vm.ec2_s3_url and "S3_URL" in os.environ:
                self.vm.ec2_s3_url = os.environ["S3_URL"]

            if not self.vm.ec2_cloud_cert and "EUCALYPTUS_CERT" in os.environ:
                self.vm.ec2_cloud_cert = os.environ["EUCALYPTUS_CERT"]

            if not self.vm.ec2_cert:
                if "EC2_CERT" in os.environ:
                    self.vm.ec2_cert = os.environ["EC2_CERT"]
                else:
                    raise VMBuilderUserError('When building for EC2 you must provide your PEM encoded public key certificate')

            if not self.vm.ec2_key:
                if "EC2_PRIVATE_KEY" in os.environ:
                    self.vm.ec2_key = os.environ["EC2_PRIVATE_KEY"]
                else:
                    raise VMBuilderUserError('When building for EC2 you must provide your PEM encoded private key file')

            if not self.vm.ec2_user:
                if "EC2_USER_ID" in os.environ:
                    self.vm.ec2_user = os.environ["EC2_USER_ID"]
                else:
                    raise VMBuilderUserError('When building for EC2 you must provide your EC2 user ID (your AWS account number, not your AWS access key ID)')

            if self.vm.ec2_upload:
                if not self.vm.ec2_bucket:
                    raise VMBuilderUserError('When building for EC2 you must provide an S3 bucket to hold the AMI')

                if not self.vm.ec2_access_key:
                    if "EC2_ACCESS_KEY" in os.environ:
                        self.vm.ec2_access_key = os.environ["EC2_ACCESS_KEY"]
                    else:
                        raise VMBuilderUserError('When building for EC2 you must provide your AWS access key ID.')

                if not self.vm.ec2_secret_key:
                    if "EC2_SECRET_KEY" in os.environ:
                        self.vm.ec2_secret_key = os.environ["EC2_SECRET_KEY"]
                    else:
                        raise VMBuilderUserError('When building for EC2 you must provide your AWS secret access key.')

        if not self.vm.ec2_version:
            raise VMBuilderUserError('When building for EC2 you must provide version info.')

    def post_install(self):
        if not getattr(self.vm, 'ec2', False):
            return

        logging.info("Running ec2 postinstall")

        self.install_from_template('/etc/ec2_version', 'ec2_version', { 'version' : self.vm.ec2_version } )

        self.vm.distro.disable_hwclock_access()

    def deploy(self):
        if not getattr(self.vm, 'ec2', False):
            return False

        #We take the time now to upload the kernel and ramdisk, if the user wants it.
        if self.vm.ec2_bundle_kernel:
            logging.info("Building EC2 kernel bundle")

            if self.vm.in_place:
                installdir = self.vm.rootmnt
            else:
                installdir = self.vm.tmproot

            kernel_loc = self.vm.distro.kernel_path()
            ramdisk_loc = self.vm.distro.ramdisk_path()

            kernel_name = os.path.split(kernel_loc)[1]

            if self.vm.ec2_cloud_cert:
                bundle_cmdline = ['%sbundle-image' % self.ec2_tools_prefix, '--image', "%s%s" % (installdir, kernel_loc), '--cert', self.vm.ec2_cert, '--privatekey', self.vm.ec2_key, '--user', self.vm.ec2_user, '--prefix', kernel_name, '-r', ['i386', 'x86_64'][self.vm.arch == 'amd64'], '-d', self.vm.destdir, '--kernel', 'true', '--ec2cert', self.vm.ec2_cloud_cert]
            else:
                bundle_cmdline = ['%sbundle-image' % self.ec2_tools_prefix, '--image', "%s%s" % (installdir, kernel_loc), '--cert', self.vm.ec2_cert, '--privatekey', self.vm.ec2_key, '--user', self.vm.ec2_user, '--prefix', kernel_name, '-r', ['i386', 'x86_64'][self.vm.arch == 'amd64'], '-d', self.vm.destdir, '--kernel', 'true']

            run_cmd(*bundle_cmdline)

            kernel_manifest = '%s/%s.manifest.xml' % (self.vm.destdir, kernel_name)

            if ramdisk_loc != None:
                ramdisk_name = os.path.split(ramdisk_loc)[1]

                if self.vm.ec2_cloud_cert:
                    bundle_cmdline = ['%sbundle-image' % self.ec2_tools_prefix, '--image', "%s%s" % (installdir, ramdisk_loc), '--cert', self.vm.ec2_cert, '--privatekey', self.vm.ec2_key, '--user', self.vm.ec2_user, '--prefix', ramdisk_name, '-r', ['i386', 'x86_64'][self.vm.arch == 'amd64'], '-d', self.vm.destdir, '--ramdisk', 'true', '--ec2cert', self.vm.ec2_cloud_cert]
                else:
                    bundle_cmdline = ['%sbundle-image' % self.ec2_tools_prefix, '--image', "%s%s" % (installdir, ramdisk_loc), '--cert', self.vm.ec2_cert, '--privatekey', self.vm.ec2_key, '--user', self.vm.ec2_user, '--prefix', ramdisk_name, '-r', ['i386', 'x86_64'][self.vm.arch == 'amd64'], '-d', self.vm.destdir, '--ramdisk', 'true']

                run_cmd(*bundle_cmdline)
                ramdisk_manifest = '%s/%s.manifest.xml' % (self.vm.destdir, ramdisk_name)

            if self.vm.ec2_upload_kernel:
                logging.info("Uploading EC2 kernel bundle")

                upload_cmdline = ['%supload-bundle' % self.ec2_tools_prefix, '--manifest', kernel_manifest, '--bucket', self.vm.ec2_bucket, '--access-key', self.vm.ec2_access_key, '--secret-key', self.vm.ec2_secret_key]

                if self.vm.ec2_s3_url:
                    upload_cmdline += ['--url', self.vm.ec2_s3_url]

                if self.vm.ec2_cloud_cert:
                    upload_cmdline += ['--ec2cert', self.vm.ec2_cloud_cert]

                run_cmd(*upload_cmdline)

                if ramdisk_loc != None:
                    upload_cmdline = ['%supload-bundle' % self.ec2_tools_prefix, '--manifest', ramdisk_manifest, '--bucket', self.vm.ec2_bucket, '--access-key', self.vm.ec2_access_key, '--secret-key', self.vm.ec2_secret_key]

                    if self.vm.ec2_s3_url:
                        upload_cmdline += ['--url', self.vm.ec2_s3_url]

                    if self.vm.ec2_cloud_cert:
                        upload_cmdline += ['--ec2cert', self.vm.ec2_cloud_cert]

                    run_cmd(*upload_cmdline)

                if self.vm.ec2_register_kernel:
                    logging.info("Registering EC2 kernel bundle")
                    uploaded_kernel_manifest = '%s/%s.manifest.xml' % (self.vm.ec2_bucket, kernel_name)
                    register_cmdline = ['%sregister' % self.ec2_tools_prefix, uploaded_kernel_manifest, '--access-key', self.vm.ec2_access_key, '--secret-key', self.vm.ec2_secret_key]

                    if self.vm.ec2_s3_url:
                        register_cmdline += ['--url', self.vm.ec2_url]

                    registered_eki = run_cmd(*register_cmdline)

                    self.vm.ec2_kernel = registered_eki.split("\t")[1].strip()
                    logging.info("EC2 kernel ID: %s" % self.vm.ec2_kernel)

                    if ramdisk_loc != None:
                        uploaded_ramdisk_manifest = '%s/%s.manifest.xml' % (self.vm.ec2_bucket, ramdisk_name)

                        register_cmdline = ['%sregister' % self.ec2_tools_prefix, uploaded_ramdisk_manifest, '--access-key', self.vm.ec2_access_key, '--secret-key', self.vm.ec2_secret_key]

                        if self.vm.ec2_s3_url:
                            register_cmdline += ['--url', self.vm.ec2_url]

                        registered_eri = run_cmd(*register_cmdline)

                        self.vm.ec2_ramdisk = registered_eri.split("\t")[1].strip()
                        logging.info("EC2 ramdisk ID: %s" % self.vm.ec2_ramdisk)

#   This is the way we used to do this. Now we just refer to ec2/euca2ools since Boto won't stop choking on my local hostname!!
#                    from boto.ec2.connection import EC2Connection
#                    from boto.ec2.regioninfo import RegionInfo

#                    rinfo = None
#                    if self.vm.ec2_is_eucalyptus: #default boto regioninfo assumes Amazon EC2
#                        rinfo = RegionInfo(None, "eucalyptus", self.vm.ec2_url)

#                    #Code added to support Eucalyptus and other EC2-compatible clusters
#                    if self.vm.ec2_url:
#                        import urlparse
#                        parsed_url = urlparse.urlparse(self.vm.ec2_url)
#                        is_secure = False

#                        if parsed_url.scheme == 'https':
#                            is_secure = True

#                        conn = EC2Connection(self.vm.ec2_access_key, self.vm.ec2_secret_key,
#                            host = parsed_url.hostname, port = parsed_url.port, path = parsed_url.path,
#                            is_secure = is_secure, region = rinfo)
#                    else:
#                        conn = EC2Connection(self.vm.ec2_access_key, self.vm.ec2_secret_key, region = rinfo)

#                    kernel_id = conn.register_image('%s/%s.manifest.xml' % (self.vm.ec2_bucket, kernel_name))

            else: #No uploading, keep the Mani Manifest
                self.vm.result_files.append(kernel_manifest)

                if ramdisk_loc != None:
                    self.vm.result_files.append(ramdisk_manifest)

        if not self.vm.ec2_kernel:
            self.vm.ec2_kernel = self.vm.distro.get_ec2_kernel()
        
        logging.debug('%s - to be used for AKI.' %(self.vm.ec2_kernel))

        if not self.vm.ec2_ramdisk:
            self.vm.ec2_ramdisk = self.vm.distro.ec2_ramdisk_id()

        logging.debug('%s - to be use for the ARI.' %(self.vm.ec2_ramdisk))

        if self.vm.ec2_bundle:
            logging.info("Building EC2 bundle")
            bundle_cmdline = ['%sbundle-image' % self.ec2_tools_prefix, '--image', self.vm.filesystems[0].filename, '--cert', self.vm.ec2_cert, '--privatekey', self.vm.ec2_key, '--user', self.vm.ec2_user, '--prefix', self.vm.ec2_name, '-r', ['i386', 'x86_64'][self.vm.arch == 'amd64'], '-d', self.vm.workdir, '--kernel', self.vm.ec2_kernel, '--ramdisk', self.vm.ec2_ramdisk]

            if self.vm.ec2_cloud_cert:
                bundle_cmdline += ['--ec2cert', self.vm.ec2_cloud_cert]

            run_cmd(*bundle_cmdline)

            manifest = '%s/%s.manifest.xml' % (self.vm.workdir, self.vm.ec2_name)
            if self.vm.ec2_upload:
                logging.info("Uploading EC2 bundle")
                upload_cmdline = ['%supload-bundle' % self.ec2_tools_prefix, '--manifest', manifest, '--bucket', self.vm.ec2_bucket, '--access-key', self.vm.ec2_access_key, '--secret-key', self.vm.ec2_secret_key]

                if self.vm.ec2_s3_url:
                    upload_cmdline += ['--url', self.vm.ec2_s3_url]

                if self.vm.ec2_cloud_cert:
                    upload_cmdline += ['--ec2cert', self.vm.ec2_cloud_cert]

                run_cmd(*upload_cmdline)

                if self.vm.ec2_register:
                    logging.info("Registering EC2 bundle")
                    uploaded_image_manifest = '%s/%s.manifest.xml' % (self.vm.ec2_bucket, self.vm.ec2_name)
                    register_cmdline = ['%sregister' % self.ec2_tools_prefix, uploaded_image_manifest, '--access-key', self.vm.ec2_access_key, '--secret-key', self.vm.ec2_secret_key]

                    if self.vm.ec2_s3_url:
                        register_cmdline += ['--url', self.vm.ec2_url]

                    registered_ami = run_cmd(*register_cmdline)

                    image_id = registered_ami.split("\t")[1].strip()
                    logging.info("EC2 image ID: %s" % image_id)
                    
#                   Again, changing strategies call for lots of commented out code
#                    from boto.ec2.connection import EC2Connection
#                    from boto.ec2.regioninfo import RegionInfo

#                    rinfo = None
#                    if self.vm.ec2_is_eucalyptus: #default boto regioninfo assumes Amazon EC2
#                        rinfo = RegionInfo(None, "eucalyptus", self.vm.ec2_url)

#                    #Code added to support Eucalyptus and other EC2-compatible clusters
#                    if self.vm.ec2_url:
#                        import urlparse
#                        parsed_url = urlparse.urlparse(self.vm.ec2_url)
#                        is_secure = False

#                        if parsed_url.scheme == 'https':
#                            is_secure = True

#                        conn = EC2Connection(self.vm.ec2_access_key, self.vm.ec2_secret_key,
#                            host = parsed_url.hostname, port = parsed_url.port, path = parsed_url.path, is_secure = is_secure, region = rinfo)
#                    else:
#                        conn = EC2Connection(self.vm.ec2_access_key, self.vm.ec2_secret_key, region = rinfo)

#                    image_id = conn.register_image('%s/%s.manifest.xml' % (self.vm.ec2_bucket, self.vm.ec2_name))
            else:
                self.vm.result_files.append(manifest)
        else:
            self.vm.result_files.append(self.vm.filesystems[0].filename)

        return True

register_plugin(EC2)
