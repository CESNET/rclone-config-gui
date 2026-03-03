# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CESNET
#
# rclone_pygui is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

""" memmodel """

from types import SimpleNamespace as nspace

class MModel():
    def __init__(self, debug=False):
        # all profiles loaded from conf:
        self.profiles = {}
        # selected profile dict:
        self.profile = None
        # selected profile name:
        self.profile_name = None
        # S3 configs:
        self.endpoint = ""
        self.access_key_id = ""
        self.secret_access_key = ""
        # enc profile configs:
        self.enc_profile = ""
        self.enc_bucket = ""
        self.password = ""
        self.password2 = ""
        # aux:
        self.debug = debug
        self.edited = set()
        self.rclone_config = None
        self.rclone_config_pw = None
        self.rclone_config_encrypted = False
        self.s3manager_mode = None
        self.selected_bucket = None
        self.bucket_ok = False
        self.template = {
            'profile_name': 's3_profile',
            'endpoint': 's3.be.du.cesnet.cz',
            'access_key_id': '',
            'secret_access_key': '',
            'enc_profile': 'encrypt_profile',
            'enc_bucket': "encbucket",
            'enc_password': '',
            'enc_password2': '',
        }
        self.vars = self.template.keys()
        self.s3_vars = ('profile_name','endpoint','access_key_id','secret_access_key')
        self.enc_vars = ('enc_profile','enc_bucket','enc_password','enc_password2')
        self._new_config()

    def set_config_file(self, rclconf, pw=None):
        self.rclone_config = rclconf
        self.rclone_config_pw = pw

    def _new_config(self):
        self.load_from_dict(self.template)

    def load_from_dict(self, d):
#        for key in self.vars: setattr(self, key, d[key] if key in d else '')
        if self.debug: print(f"load_from_dict: {d=}")
        for key in self.vars:
            if key in d: setattr(self, key, d[key])

    def load_from_widget(self, widget, vars="all"):
        if self.debug: print(f"load_from_widget: {vars=} {widget.input_endpoint.text()=}")
        vars = {"all":self.vars, "s3_vars":self.s3_vars, "enc_vars":self.enc_vars}[vars]
        for key in  vars: setattr(self, key, getattr(widget, f"input_{key}").text())
        if self.debug: print(f"load_from_widget2: {self.endpoint=}")

    def save_to_widget(self, widget, vars="all"):
        if self.debug: print(f"save_to_widget: {self.endpoint=}")
        vars = {"all":self.vars, "s3_vars":self.s3_vars, "enc_vars":self.enc_vars}[vars]
        for key in  vars: getattr(widget, f"input_{key}").setText(getattr(self, key))
        if self.debug: print(f"save_to_widget2: {widget.input_endpoint.text()=}")

    def get_dict(self):
        r = {}
        for key in self.vars: r[key] = getattr(self, key)
        return r

    def get_nspace(self):
        return nspace(**self.get_dict())
