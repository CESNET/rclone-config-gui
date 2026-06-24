#!/bin/bash

YKCHR="$(command -v ykchalresp)"
if [[ ! -x "$YKCHR" ]]; then
  echo "fatal error: ykchalresp not found"
  exit 1
fi

YKINF="$(command -v ykinfo)"
if [[ ! -x "$YKINF" ]]; then
  echo "fatal error: ykinfo not found"
  exit 2
fi

if ! $YKINF -v > /dev/null; then
  exit 3
fi

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
rclone --password-command "$YKCHR -2 $CHALL" $@
