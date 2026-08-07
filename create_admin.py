import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workshop_system.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

user, created = User.objects.get_or_create(username='admin', defaults={'email': 'admin@example.com', 'is_staff': True, 'is_superuser': True})
user.set_password('admin')
user.is_staff = True
user.is_superuser = True
user.save()

if created:
    print('Admin user created successfully!')
else:
    print('Admin user password reset successfully!')

print('Login Credentials:')
print('Username: admin')
print('Password: admin')
