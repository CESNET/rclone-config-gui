# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CESNET
#
# rclone_pygui is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

""" rclone control class """

import sys, os, re, json, shutil, platform, secrets
import subprocess as sp
from PySide6.QtWidgets import QMessageBox

from .utils import WarningQD, fatal_err, rclone_obscure

class Rclone_control():
    def __init__(self, debug, rclone_command, rclone_pygui_command=None):
        self.debug = debug
        if self.debug: print("Rclone_control init")
        self.rclone_version = None
        self.rclone_config = None
        self.rclone_pygui_command = rclone_pygui_command or sys.argv[0]
        if not (rclone := shutil.which(rclone_command)):
            WarningQD(title="Warning", text="Rclone command not found.", icon=QMessageBox.Warning).exec()
            fatal_err(f"Rclone command \"{rclone_command}\" not found.")
        self.rclone_command = rclone
        if self.debug: print(f"Using rclone command \"{rclone}\"")
        # ***
        self.rclone_version = self.get_rclone_version(rclone, self.debug)
        self.pwbits = 2048
        self.enc_profile = None
        self.enc_bucket = None
        if self.debug: print(f"rclone version: {self.rclone_version}")

    def set_rclone_config(self, rc=None):
        self.rclone_config = rc if rc!='' else None
    def get_rclone_config(self):
        return self.rclone_config if self.rclone_config is not None else 'not selected'

    def rclone_config_check(self, config_pw):
        if self.debug: print("call rclone config dump")
        (st, err, out) = self.subprocess_call(
            self.rclone_command, ['--no-console', '--config', self.rclone_config, '--ask-password=false', 'config', 'dump'],
            self.debug,
            { 'RCLONE_CONFIG_PASS': config_pw }
        )
        if st==0:
            profiles = json.loads(out)
            if self.debug: print(json.dumps(profiles, indent=2))
            return (True, profiles)
        return (False, [])

    def rclone_change_config_pw(self, old_pw, new_pw):
        if self.debug: print("call rclone config encryption set")
        subcomm = 'set' if new_pw!='' else 'remove'
        (st, err, out) = self.subprocess_call(
            self.rclone_command, [
                '--no-console',
                '--config', self.rclone_config, 'config', 'encryption', subcomm, '--ask-password=false',
                '--password-command', f"{self.rclone_pygui_command} --password_command"
            ],
            self.debug,
            { 'PYGUI_RCLONE_OLDPW': old_pw, 'PYGUI_RCLONE_NEWPW': new_pw }
        )
        return (st, err, out)

    def rclone_change_keys(self, config_pw, endpoint, access_key_id, secret_access_key):
        if self.debug: print("rclone_change_keys:")
        options = {
            "endpoint": { "confval":endpoint, 'updated':False },
            "access_key_id": { "confval":access_key_id, 'updated':False },
            "secret_access_key": { "confval":secret_access_key, 'updated':False },
        }
        nextarg, rcstate, rcresult, rcconfname  = "--all", None, "", ""
        while True:
            for opt in [k for k in options.keys() if not options[k]['updated']]:
                if rcconfname == opt:
                    rcresult = options[opt]['confval']
                    options[opt]['updated'] = True
            if self.debug: print(f"call rclone w.nextarg: {nextarg}")
            (st, err, out) = self.subprocess_call(
                self.rclone_command, ['--no-console', '--config', self.rclone_config, 'config', 'update', '--non-interactive', self.profile_name, '--continue'] + [nextarg],
                self.debug,
                { 'RCLONE_CONFIG_PASS': config_pw, 'RCLONE_RESULT': rcresult }
            )
            if st != 0: raise Exception(f"Wrong status ({st}) from subprocess ({err=}).")
            jout = json.loads(out)
            if self.debug: print(json.dumps(jout, indent=2))
            rcstate = jout['State']
            # exit from while:
            if rcstate in ("", "*all-advanced",): break
            if len([k for k in options.keys() if not options[k]['updated']])==0: break
            #
            nextarg = f"--state={rcstate}"
            rcresult = str(jout['Option']['Default'])
            rcconfname = jout['Option']['Name']
        if self.debug: print("rclone_change_keys done.")
        return True

    def rclone_create_enc_profile(self, config_pw, enc_profile=None, enc_bucket=None, password=None, password2=None):
        self.enc_profile = f"{self.profile_name}_enc" if enc_profile is None else enc_profile
        self.enc_bucket = "encbucket" if enc_bucket is None else enc_bucket
        self.enc_remote = f"{self.profile_name}:{self.enc_bucket}"
        self.rclone_create_profile(config_pw, enc_profile, 'crypt', f'remote={self.enc_remote}')
        if password is not None or password2 is not None:
            return self.rclone_configure_enc_profile(config_pw, enc_profile, enc_bucket, password, password2)
        else: return True

    def rclone_create_profile(self, config_pw, profile, type='s3', nextarg='provider=Ceph'):
        (st, err, out) = self.subprocess_call(
            self.rclone_command, ['--config', self.rclone_config, 'config', 'create', profile, type] + [nextarg] + ['--no-console', '--non-interactive'],
            self.debug,
                { 'RCLONE_CONFIG_PASS': config_pw, }
        )
        if st != 0: raise Exception(f"Wrong status ({st}) from subprocess ({err=}).")
        return True

    def rclone_delete_profile(self, config_pw, profile):
        (st, err, out) = self.subprocess_call(
            self.rclone_command, ['--config', self.rclone_config, 'config', 'delete', profile, '--no-console'],
            self.debug,
                { 'RCLONE_CONFIG_PASS': config_pw, }
        )
        if st != 0: raise Exception(f"Wrong status ({st}) from subprocess ({err=}).")
        return True

    def _generate_pwd(self, bits=None):
        if bits is None: bits = self.pwbits
        pw = secrets.token_urlsafe(bits // 8)
        #opw = rclone_obscure(pw)
        return pw

    def rclone_configure_enc_profile(self, config_pw, enc_profile=None, enc_bucket=None, password=None, password2=None):
        self.enc_profile = f"{self.profile_name}_enc" if enc_profile is None else enc_profile
        self.enc_bucket = "encbucket-default" if enc_bucket is None else enc_bucket
        self.enc_remote = f"{self.profile_name}:{self.enc_bucket}"
        if self.debug: print("rclone_configure_enc_profile:")
        options = {
            "remote": { "confval":self.enc_remote, 'updated':False },
            "password": { "confval":rclone_obscure(self._generate_pwd() if password is None else password), 'updated':False },
            "password2": { "confval":rclone_obscure(self._generate_pwd() if password2 is None else password2), 'updated':False },
        }
        nextarg, rcstate, rcresult, rcconfname  = "--all", None, "", ""
        while True:
            for opt in [k for k in options.keys() if not options[k]['updated']]:
                if rcconfname == opt:
                    rcresult = options[opt]['confval']
                    options[opt]['updated'] = True
            if self.debug: print(f"call rclone w.nextarg: {nextarg}")
            (st, err, out) = self.subprocess_call(
                self.rclone_command, ['--no-console', '--config', self.rclone_config, 'config', 'update', '--non-interactive', self.enc_profile, '--continue'] + [nextarg],
                self.debug,
                { 'RCLONE_CONFIG_PASS': config_pw, 'RCLONE_RESULT': rcresult }
            )
            if st != 0: raise Exception(f"Wrong status ({st}) from subprocess ({err=}).")
            jout = json.loads(out)
            if self.debug: print(json.dumps(jout, indent=2))
            rcstate = jout['State']
            # exit from while:
            if rcstate in ("", "*all-advanced",): break
            if len([k for k in options.keys() if not options[k]['updated']])==0: break
            #
            nextarg = f"--state={rcstate}"
            rcresult = str(jout['Option']['Default'])
            rcconfname = jout['Option']['Name']
        if self.debug: print("rclone_change_keys done.")
        return True

    def get_rclone_version(self, cmd, debug=False):
        if debug: print("call rclone version")
        (st, err, out) = self.subprocess_call(cmd, ["version"], debug)
        if st == 0: return out.split("\n")[0].replace('rclone ', '')
        else: raise Exception(f"Rclone not found ({err=})")

    def subprocess_call(self, cmd, cmd_args, debug, env=None):
        wait_timeout_s = 10
        proc = None
        try:
            if debug: print(f"subprocess call: {cmd} {cmd_args=} {env=}")
            env_copy = os.environ.copy()
            if env != None: env_copy.update(env)
            kwargs = {}
            if platform.system() == "Windows":
                si = sp.STARTUPINFO()
                si.dwFlags |= sp.STARTF_USESHOWWINDOW
                si.wShowWindow = 7 # SW_SHOWMINNOACTIVE
                kwargs['creationflags'] = sp.DETACHED_PROCESS
                kwargs['startupinfo'] = si
                #kwargs['capture_output'] = True
            proc = sp.Popen([cmd] + cmd_args,
                stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE, text=True,
                env=env_copy, start_new_session=True,
                **kwargs
            )
            proc.wait(timeout = wait_timeout_s)
            out = proc.stdout.read()
            err = proc.stderr.read()
            if debug: print(out, err)
            status = proc.returncode
            return (status, err, out)
        except sp.TimeoutExpired:
            status, err = 255, 'timeout'
            return (status, err, '')
        finally:
            if proc:
                proc.stdin.close()
                proc.terminate()
                if debug: print(f"-->subprocess call finnished: {cmd} {cmd_args=}: {status=} {err=}")
