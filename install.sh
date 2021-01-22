#!/usr/bin/env bash

set -e
set -u

INSTALL_DIR=/usr/local/bin
INSTALL_LIB=/usr/local/lib
PROJECTNAME=gitmess
MAINFILE=main.py
GITCOMMAND=mess

function main {

  if [ "$EUID" -eq 0 ]; then

    echo -e "Installation script for gitmess project"
    echo -e "======================================="
    echo -e

    echo -e -n "1. Installing executables in $INSTALL_DIR... "

    if [ -d "$INSTALL_DIR" ]; then

      cp "$MAINFILE" "$INSTALL_DIR/$PROJECTNAME"
      ln -sf "$INSTALL_DIR/$PROJECTNAME" "$INSTALL_DIR/git-$GITCOMMAND"
      if [ $? -ne 0 ]; then
        echo -e
        echo -e "Error copying files $INSTALL_DIR"
        echo -e
        echo -e "Installation failed"
        exit 4
      fi

      chmod a+x "$INSTALL_DIR/$PROJECTNAME"
      echo -e "Done!"

    else
      echo -e
      echo -e "Directory $INSTALL_DIR does not exists. Please create it and add it to your PATH environment variable"
      echo -e
      echo -e "Installation failed"
      exit 2
    fi

    echo -e "2. Checking if $PROJECTNAME command is available... "
    if (command -v "$PROJECTNAME" > /dev/null 2>&1); then
      echo -e "\tCommand $PROJECTNAME is available"
      echo -e
      echo -e "Installation finished successfully"
      exit 0
    else
      echo -e "\tCommand $PROJECTNAME is not available. Make sure that $INSTALL_DIR is in your PATH environment variable"
      echo -e
      echo -e "Installation failed"
      exit 3
    fi

  else
    echo -e "Please run this script as root (or with sudo privileges)"
    echo -e "Installation failed"
    exit 1
  fi


}

main
