#!/usr/bin/env python
"""
Script to run Django with development settings.
Usage: python scripts/run_development.py [command]
"""
import os
import sys
import subprocess

# Set environment to development
os.environ['DJANGO_ENVIRONMENT'] = 'development'

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

if __name__ == '__main__':
    # Default to runserver if no command provided
    command = sys.argv[1:] if len(sys.argv) > 1 else ['runserver']
    
    # Run Django management command
    subprocess.run([sys.executable, 'manage.py'] + command, cwd=project_root)