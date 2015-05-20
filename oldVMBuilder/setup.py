#!/usr/bin/python

from distutils.core import setup
import VMBuilder.plugins
import os
import subprocess

def notglob(name):
    out = []
    
    for root, dirs, files in os.walk(name):
        for filename in files:
            out.append(os.path.join(root, filename))
            
    return out

if os.path.exists('.bzr'):
    try:
        o = subprocess.Popen(('bzr','version-info', '--python'), stdout=subprocess.PIPE).stdout
        f = open('VMBuilder/vcsversion.py', 'w')
        f.write(o.read())
        f.close()
        o.close()
    except Exception, e:
        print repr(e)

setup(name='VMBuilder',
      version='0.11',
      description='Uncomplicated VM Builder',
      author='Soren Hansen',
      author_email='soren@canonical.com',
      url='http://launchpad.net/vmbuilder/',
      packages=['VMBuilder', 'VMBuilder.plugins'] + VMBuilder.plugins.find_plugins(),
      data_files=[('/etc/vmbuilder/%s' % (pkg,), notglob('VMBuilder/plugins/%s/templates/*' % (pkg,))) for pkg in [p.split('.')[-1] for p in VMBuilder.plugins.find_plugins()]],
      scripts=['vmbuilder'], 
      )
