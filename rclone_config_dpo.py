#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CESNET
#
# rclone_pygui is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

""" rclone config manager for DPO """

import sys
from rclone_pygui.rclone_config_dpo import main

if __name__ == '__main__':
    sys.exit(main())
