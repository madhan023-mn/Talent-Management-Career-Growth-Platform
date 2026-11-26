#!/bin/bash
echo "==> Building Talent Growth Django project for Vercel..."
python3 -m pip install -r requirements.txt
python3 manage.py collectstatic --noinput --clear
echo "==> Build complete."
