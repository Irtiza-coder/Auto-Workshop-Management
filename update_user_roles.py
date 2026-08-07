import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workshop_system.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

# 1. Configure the single Super Admin
admin_user, created = User.objects.get_or_create(username='admin', defaults={'email': 'admin@example.com'})
admin_user.is_staff = True
admin_user.is_superuser = True
admin_user.set_password('admin')
admin_user.save()
print("Super Admin 'admin' updated.")

# 2. Demote 'Irtiza' (and any other users) to standard Workshop User (NO access to /admin/)
for user in User.objects.exclude(username='admin'):
    user.is_staff = False
    user.is_superuser = False
    if user.username == 'Irtiza':
        user.set_password('user123')
    user.save()
    print(f"User '{user.username}' updated: Demoted from Django Admin. Workshop App login active.")

print("\n--- Summary of User Roles ---")
for u in User.objects.all():
    admin_access = "YES (/admin/ + Workshop)" if u.is_superuser or u.is_staff else "NO (Workshop App Only)"
    print(f"Username: {u.username:<10} | Django Admin Access: {admin_access}")
