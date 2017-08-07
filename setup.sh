#!/usr/bin/env bash

echo "EXECUTABLE_SCRIPTS=\$HOME/sancarlabutils
PATH=\$PATH:\$EXECUTABLE_SCRIPTS
export PATH
CUSTOM_PYTHON_SCRIPTS=\$EXECUTABLE_SCRIPTS/utils
PYTHONPATH=\$PYTHONPATH:\$CUSTOM_PYTHON_SCRIPTS
export PYTHONPATH" >>~/.bash_profile

source ~/.bash_profile