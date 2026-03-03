# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CESNET.
#

"""Module tests."""

import pytest, shutil, re, os
from types import SimpleNamespace as nspace

from rclone_pygui.utils import *

def test_rclone_obscure():
    st = 'abcd2'
    ost = rclone_obscure(st)
    dost = rclone_deobscure(ost)
    assert st == dost
    dost = rclone_deobscure('0M2woNOk0cIylEMztPkVNLq6oJKB')
    assert st == dost

def test_get_rclone_version(rcl_dpo):
    """ """
    rclone = shutil.which(rcl_dpo.rclone_command)
    assert os.path.isfile(rclone)
    assert os.access(rclone, os.X_OK)
    rclone_version = rcl_dpo.get_rclone_version(rclone)
    assert re.match(r"^v[0-9]+\.[0-9]+\.[0-9]+$", rclone_version)


#def test_password_command_mode_rcl_users(rcl_users):
#    """ rcl """
#    old_pw, new_pw = 'abc', 'def'
#    (st, err, out) = rcl_users.rclone_change_config_pw(old_pw, new_pw)
#    assert (st, err, out) == (0, '', 'Read password using --password-command\n')
#    (st, err, out) = rcl_users.rclone_change_config_pw(new_pw, old_pw)
#    assert (st, err, out) == (0, '', 'Read password using --password-command\n')

def test_password_command_mode_rcl_dpo(rcl_dpo):
    """ rcl_dpo """
    old_pw, new_pw = 'abc', 'def'
    (st, err, out) = rcl_dpo.rclone_change_config_pw(old_pw, new_pw)
    assert (st, err, out) == (0, '', 'Read password using --password-command\n')
    (st, err, out) = rcl_dpo.rclone_change_config_pw(new_pw, '')
#    assert (st, err, out) == (0, '', 'Read password using --password-command\n')
    assert (st, err, out) == (0, '', '')

def test_rclone_create_profile(rcl_dpo):
    new_pw = 'def'
    conf = open(rcl_dpo.rclone_config, 'r').read()
#    assert re.match('^# Encrypted rclone configuration File', conf)
    assert len(re.findall('^\\[profile_name\\]\n', conf)) == 1
    assert len(re.findall('\n\\[profile_name_enc\\]\n', conf)) == 1
    assert len(re.findall('\n\\[profile_test\\]\n', conf)) == 0
    assert rcl_dpo.rclone_create_profile(new_pw, 'profile_test','s3') == True
    conf = open(rcl_dpo.rclone_config, 'r').read()
    assert len(re.findall('\n\\[profile_test\\]\n', conf)) == 1

def test_mm(mm):
    assert mm.get_dict() == {
        'profile_name': 's3_profile',
        'endpoint': 's3.be.du.cesnet.cz',
        'access_key_id': '',
        'secret_access_key': '',
        'enc_profile': 'encrypt_profile',
        'enc_bucket': "encbucket",
        'enc_password': '',
        'enc_password2': '',
    }
    d = {
        'profile_name': 'a',
        'endpoint': 'b',
        'access_key_id': 'c',
        'secret_access_key': 'D',
        'enc_profile': 'e',
        'enc_bucket': 'f',
        'enc_password': 'G',
        'enc_password2': 'h',
    }
    mm.load_from_dict(d)
    assert mm.get_dict() == d
    assert mm.get_nspace() == nspace(**d)
    d['endpoint'] = 'X'
    assert mm.get_nspace() != nspace(**d)
