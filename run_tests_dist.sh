#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CESNET.
#
# free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

set -e

cd dist

echo "runner: $RUNNER"
if [[ "$RUNNER" == "Windows" ]]; then SCRIPT_NAME="${SCRIPT_NAME}.exe"; fi

echo -ne "   test: ${SCRIPT_NAME} --help\r"
set +e
read -r -d '' GOLDEN <<- EOT
usage: ${SCRIPT_NAME} [-h] [-d] [-c RCLONE_CONFIG] [-r RCLONE_COMMAND] [-p]

CESNET S3 rclone GUI config for users

options:
  -h, --help            show this help message and exit
  -d, --debug           enable debug outputs (default False)
  -c RCLONE_CONFIG, --rclone_config RCLONE_CONFIG
                        rclone config file (default: None)
  -r RCLONE_COMMAND, --rclone_command RCLONE_COMMAND
                        rclone command, could be full path to command (default: rclone)
  -p, --password_command
                        run as rclone password command, for internal use
  -v, --version         print version and exit
EOT
set -e
#echo ">$GOLDEN<"
OUT="$(./${SCRIPT_NAME} --help)"
#echo ">$OUT<"
diff <(echo "$GOLDEN"| sed 's/optional arguments/options/' | tr '\n\t' '  ' | tr -s ' ') <(echo "$OUT" | sed 's/optional arguments/options/' | tr '\n\t' '  ' | tr -s ' ')
echo "OK"

echo -ne "   test: ${SCRIPT_NAME} --password_command 0\r"
GOLDEN="abc"
OUT="$(PYGUI_RCLONE_OLDPW=abc PYGUI_RCLONE_NEWPW=def RCLONE_PASSWORD_CHANGE=0 ./${SCRIPT_NAME} --password_command)"
diff <(echo "$GOLDEN") <(echo "$OUT")
echo "OK"

echo -ne "   test: ${SCRIPT_NAME} --password_command 1\r"
GOLDEN="def"
OUT="$(PYGUI_RCLONE_OLDPW=abc PYGUI_RCLONE_NEWPW=def RCLONE_PASSWORD_CHANGE=1 ./${SCRIPT_NAME} --password_command)"
diff <(echo "$GOLDEN") <(echo "$OUT")
echo "OK"
