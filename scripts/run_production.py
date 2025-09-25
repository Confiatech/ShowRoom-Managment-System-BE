#!/usr/bin/env python
"""
Script to run Django with production settings.
Usage: python scripts/run_production.py [command]
"""
import os
import sys
import subprocess

# Set environment to production
os.environ['DJANGO_ENVIRONMENT'] = 'production'

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

if __name__ == '__main__':
    # Default to collectstatic and migrate for production
    command = sys.argv[1:] if len(sys.argv) > 1 else ['collectstatic', '--noinput']
    
    # Run Django management command
    subprocess.run([sys.executable, 'manage.py'] + command, cwd=project_root)