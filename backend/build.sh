#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run migrations (even though we don't use a database, this keeps Django happy)
python manage.py migrate --run-syncdb

echo "Build completed successfully!"
