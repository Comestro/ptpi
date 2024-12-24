# teacherhire/management/commands/build.py

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Custom build command'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Build command executed successfully'))