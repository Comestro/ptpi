# teacherhire/management/commands/seed_admin.py

from django.core.management.base import BaseCommand
from teacherhire.models import CustomUser

class Command(BaseCommand):
    help = 'Seed the database with an admin user'

    def handle(self, *args, **kwargs):
        if not CustomUser.objects.filter(email='admin@example.com').exists():
            CustomUser.objects.create_superuser(
                email='admin@example.com',
                username='admin',
                password='adminpassword',
                Fname='Admin',
                Lname='User',
                is_verified=True
            )
            self.stdout.write(self.style.SUCCESS('Successfully created admin user'))
        else:
            self.stdout.write(self.style.WARNING('Admin user already exists'))