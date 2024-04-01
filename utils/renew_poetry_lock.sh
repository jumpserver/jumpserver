#!/bin/bash

command -v poetry >/dev/null 2>&1 || { 
    echo "poetry not found. Aborting."
    exit 1
}

if [ ! -f "pyproject.toml" ]; then
    echo "pyproject.toml not found. Aborting."
    exit 1
fi

poetry config virtualenvs.create false
poetry lock --no-update