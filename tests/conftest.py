# -*- coding: utf-8 -*-
# Copyright (C) 2010, 2011 Sebastian Wiesner <lunaryorn@googlemail.com>
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import (print_function, division, unicode_literals,
                        absolute_import)

import sys
import re
from collections import namedtuple
from subprocess import Popen, PIPE

import pytest


DEVICE_PATTERN = re.compile(
    r'(\W|\s)*(?P<name>.+?)\s+id=(?P<id>\d+)\s\[[^]]+\]', re.UNICODE)
PROPERTY_PATTERN = re.compile(
    r'(?P<name>[^(]+) \((?P<id>\d+)\):\s+(?P<values>.*)', re.UNICODE)
ATOM_PATTERN = re.compile(
    r'\((?P<value>\d+)\)', re.UNICODE)

Device = namedtuple('Device', 'id name properties')


def _read_device_properties(device_id):
    proc = Popen(['xinput', 'list-props', str(device_id)], stdout=PIPE)
    output = proc.communicate()[0].decode(sys.getfilesystemencoding())
    properties = {}
    for line in output.splitlines()[1:]:
        line = line.strip()
        match = PROPERTY_PATTERN.match(line)
        value_strings = match.group('values').strip().split(',')
        values = []
        for value_string in value_strings:
            value_string = value_string.strip()
            if '.' in value_string:
                value = float(value_string)
            elif '(' in value_string:
                value = int(ATOM_PATTERN.search(value_string).group('value'))
            else:
                value = int(value_string)
            values.append(value)
        properties[match.group('name')] = values
    return properties


def _read_device_database():
    proc = Popen(['xinput', 'list'], stdout=PIPE)
    output = proc.communicate()[0].decode(sys.getfilesystemencoding())
    devices = {}
    for line in output.splitlines():
        line = line.strip()
        match = DEVICE_PATTERN.match(line)
        device_id = int(match.group('id'))
        device = Device(device_id, match.group('name'),
                        _read_device_properties(device_id))
        devices[device_id] = device
    return devices


def pytest_configure(config):
    # make sure, that an application and consequently an X11 Display
    # connection exists
    config.xinput_device_database = _read_device_database()
    for device in config.xinput_device_database.itervalues():
        if 'Synaptics Off' in device.properties:
            config.xinput_has_touchpad = True
            break
    else:
        config.xinput_has_touchpad = False


def pytest_funcarg__device_database(request):
    """
    The device database as returned by the "xinput" utility.
    """
    return request.config.xinput_device_database


def pytest_funcarg__qtapp(request):
    """
    Return the :class:`~PyQt4.QtGui.QApplication` instance for use in the
    tests.
    """
    QtGui = pytest.importorskip('PyQt4.QtGui')
    app = QtGui.QApplication.instance()
    if not app:
        app = QtGui.QApplication([])
    return app


def pytest_funcarg__qxdisplay(request):
    """
    Qt X11 display wrapper.
    """
    qx11 = pytest.importorskip('synaptiks.qx11')
    return qx11.QX11Display()


def pytest_funcarg__display(request):
    """
    A direct X11 display connection.
    """
    from synaptiks._bindings import xlib
    return request.cached_setup(
        lambda: xlib.open_display(),
        xlib.close_display)
