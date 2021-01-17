#!/usr/bin/env bash

set -e
set -u

INSTALL_DIR=/usr/local/bin
INSTALL_LIB=/usr/local/lib
PROJECTNAME=gitmess

function main {

  cp ./main.py "$INSTALL_DIR/$PROJECTNAME"
  chmod a+x "$INSTALL_DIR/$PROJECTNAME"

}

main
