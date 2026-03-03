# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CESNET.
#

""" """

import pytest, tempfile, os, shutil
from collections import namedtuple
from rclone_config_gui.rclone_control import Rclone_control
from rclone_config_gui.mmodel import MModel

def literal(**kw):
    return namedtuple('literal', kw)(**kw)

@pytest.fixture(scope="session")
def tmpf():
    nf, fn = tempfile.mkstemp()
    yield fn
    os.unlink(fn)

@pytest.fixture(scope="module")
def rcl_users(tmpf):
    shutil.copy('rclone_pytest.conf', tmpf)
    #args = literal(rclone_command='rclone', rclone_config=tmpf, debug=False)
    rcl = Rclone_control(False, 'rclone', rclone_config_command='../rclone_config.py')
    rcl.set_rclone_config(tmpf)
    return rcl

@pytest.fixture(scope="module")
def rcl_dpo(tmpf):
    shutil.copy('rclone_pytest.conf', tmpf)
    #args = literal(rclone_command='rclone', rclone_config=tmpf, debug=False)
    rcl = Rclone_control(False, 'rclone', rclone_config_command='../rclone_config_dpo.py')
    rcl.set_rclone_config(tmpf)
    return rcl

@pytest.fixture(scope="session")
def mm(tmpf):
    mm = MModel()
    return mm
