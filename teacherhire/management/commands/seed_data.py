import requests
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Makes a GET request to the exam center URL to insert data'

    def handle(self, *args, **kwargs):
        url = 'http://127.0.0.1:8000/api/admin/insert/data/'
        response = requests.get(url)

        if response.status_code == 200:
            self.stdout.write(self.style.SUCCESS('Data inserted successfully'))
        else:
            self.stdout.write(self.style.ERROR('Failed to insert data'))
