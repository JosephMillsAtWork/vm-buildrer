#!/usr/bin/python
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
#    The publically exposed bits of VMBuilder
#
import logging
from   VMBuilder.plugins    import load_plugins, Plugin
from   VMBuilder.distro     import Distro
from   VMBuilder.hypervisor import Hypervisor
from   VMBuilder.frontend   import Frontend
from   VMBuilder.vm         import VM
from   VMBuilder.exception  import VMBuilderException, VMBuilderUserError

# Internal bookkeeping
distros = {}
hypervisors = {}
_plugins = []
frontends = {}
frontend = None

# This is meant to be populated by plugins. It should contain a list of the files that we give back to the user.

def register_hypervisor(cls):
    """Register a hypervisor plugin with VMBuilder"""
    hypervisors[cls.arg] = cls

def register_distro(cls):
    """Register a distro plugin with VMBuilder"""
    distros[cls.arg] = cls

def register_frontend(cls):
    """Register a frontend plugin with VMBuilder"""
    frontends[cls.arg] = cls

def register_plugin(cls):
    """Register a plugin with VMBuilder"""
    _plugins.append(cls)

def set_frontend(arg):
    global frontend
    if arg in frontends.keys():
        frontend = frontends[arg]()
    else:
        raise VMBuilderException("Unknown frontend")

def run():
    """This is sort of weird, but a handy shortcut, if you want to use one of the frontends"""
    frontend.run()

logging.debug('Loading plugins')
load_plugins()
