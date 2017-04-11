#!/bin/bash

FILES="./fpemud-wrt"
LIBFILES="$(find ./lib -name '*.py' | tr '\n' ' ')"

autopep8 -ia --ignore=E501,E402 ${FILES}
autopep8 -ia --ignore=E501 ${LIBFILES}