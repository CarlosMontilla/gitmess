#!/usr/bin/env bash

set -e
set -u

INSTALL_DIR=/usr/local/bin
INSTALL_LIB=/usr/local/lib
PROJECTNAME=gitmess

function main {

  if [ "$EUID" -eq 0 ]; then

    echo -e "Installation script for gitmess project"
    echo -e "======================================="
    echo -e

    echo -e -n "1. Installing executable as $INSTALL_DIR/$PROJECTNAME... "

    if [ -d "$INSTALL_DIR" ]; then

      cp ./main.py "$INSTALL_DIR/$PROJECTNAME"
      if [ $? -ne 0 ]; then
        echo -e
        echo -e "Error copying file $INSTALL_DIR/$PROJECTNAME"
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
