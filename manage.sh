#!/bin/bash
# Convenience script to run Django management commands
# Usage: ./manage.sh <command> [args]

export PYTHONPATH="${PWD}/src:${PYTHONPATH}"

# Ensure proto pb2 files are generated under apps folder (src)
if [ "$1" = "generateproto" ]; then
	(cd src && poetry run python manage.py "$@")
else
	poetry run python src/manage.py "$@"
fi
