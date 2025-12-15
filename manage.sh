#!/bin/bash
# Convenience script to run Django management commands
# Usage: ./manage.sh <command> [args]

export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
poetry run python src/manage.py "$@"
