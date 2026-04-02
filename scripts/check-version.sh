#!/bin/sh
# Check version consistency across pyproject.toml and __init__.py
set -e

PYPROJECT_VER=$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
INIT_VER=$(grep '__version__' src/parsemux/__init__.py | cut -d'"' -f2)

if [ "$PYPROJECT_VER" != "$INIT_VER" ]; then
    echo "VERSION MISMATCH: pyproject.toml=$PYPROJECT_VER __init__.py=$INIT_VER"
    exit 1
fi

echo "Version OK: $PYPROJECT_VER"
