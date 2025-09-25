#!/usr/bin/env python
"""
Script to run Django with local settings.
Usage: python scripts/run_local.py [command]
"""
import os
import sys
import subprocess

# Set environment to local
os.environ['DJANGO_ENVIRONMENT'] = 'local'

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

if __name__ == '__main__':
    # Default to runserver if no command provided
    command = sys.argv[1:] if len(sys.argv) > 1 else ['runserver']
    
    # Run Django management command
    subprocess.run([sys.executable, 'manage.py'] + command, cwd=project_root)