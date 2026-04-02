#!/usr/bin/env python
"""Migration script for Vercel deployment."""
import os
import sys
import django

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_prod')

# Setup Django
django.setup()

# Run migrations
from django.core.management import execute_from_command_line

if __name__ == '__main__':
    print("Running Django migrations...")
    execute_from_command_line(['manage.py', 'migrate', '--verbosity', '2'])
    print("Migrations completed successfully!")
    
    # Create superuser if needed
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    if not User.objects.filter(is_superuser=True).exists():
        print("Creating superuser...")
        User.objects.create_superuser(
            email='admin@facturacion.com',
            password='admin123',
            first_name='Admin',
            last_name='User'
        )
        print("Superuser created: admin@facturacion.com / admin123")
    else:
        print("Superuser already exists.")
