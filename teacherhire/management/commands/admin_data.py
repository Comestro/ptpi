# teacherhire/management/commands/seed_admin.py

from django.core.management.base import BaseCommand
from teacherhire.models import CustomUser


class Command(BaseCommand):
    help = 'Seed the database with an admin user'

    def handle(self, *args, **kwargs):
        if not CustomUser.objects.filter(email='ptpi854301@gmail.com').exists():
            CustomUser.objects.create_superuser(
                email='ptpi854301@gmail.com',
<<<<<<< HEAD
                username='Manish',
=======
                username='Manish458',
>>>>>>> 7cbae0344548750ed4730bf4c2e5bc6330b2f260
                password='adminpassword',
                Fname='Manish',
                Lname='Kumar Gandhi',
                is_verified=True,
                is_staff=True
            )
            self.stdout.write(self.style.SUCCESS('Successfully created admin user'))
        else:
            self.stdout.write(self.style.WARNING('Admin user already exists'))


