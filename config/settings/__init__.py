"""
Django settings module selector.
This module automatically selects the appropriate settings based on the DJANGO_ENVIRONMENT variable.
"""

import os
import environ

# Initialize environment variables
env = environ.Env()

# Get the environment from environment variable, default to 'local'
environment = env('DJANGO_ENVIRONMENT', default='local')

# Import the appropriate settings module
if environment == 'production':
    from .production import *
elif environment == 'development':
    from .development import *
else:
    from .local import *

# Set a variable to track which environment is active
ENVIRONMENT = environment