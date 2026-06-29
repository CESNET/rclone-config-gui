#!/bin/bash

MSG="Enter challenge string for YubiKey challenge-response operation: "
STARS=''
CHALL=''
while true; do
  printf "\r%*s\r$MSG" $((${#MSG}+82)) ''
  IFS='' read -N 1 -srp "$STARS" CHR
  case "$CHR" in
    ($'\n')
      break;
      ;;
    ($'\177')
      if [[ "${#CHALL}" != "0" ]]; then
        CHALL="${CHALL:0:$(( ${#CHALL}-1 ))}"
        STARS="${STARS:0:$(( ${#STARS}-1 ))}"
      fi
      ;;
    (*)
      if [[ "${#CHALL}" != "80" ]]; then
        CHALL="$CHALL$CHR"
        STARS="${STARS}*"
      fi
      ;;
  esac
done
echo

echo "Tap The YubiKey"
PYGUI_YUBIKEY_CHALLENGE="$CHALL" rclone --password-command "./rclone_config.py -py" $@
