#!/usr/bin/env bash

set -e
set -u

INSTALL_DIR=/usr/local/bin
INSTALL_LIB=/usr/local/lib
PROJECTNAME=gitmess

function main {

  if [ "$EUID" -eq 0 ]; then

     cp ./main.py "$INSTALL_DIR/$PROJECTNAME"
     chmod a+x "$INSTALL_DIR/$PROJECTNAME"

  else
    echo "Please run this script as root (or with sudo privileges)"
  fi


}

main
