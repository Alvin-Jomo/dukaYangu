# management/commands/createsuperuser_safe.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a superuser safely bypassing signals'

    def handle(self, *args, **options):
        User.objects.create_superuser(
            username='admin',
            email='alvotheboss@gmail.com',
            password='admin123',
            phone='0712345678',
            is_approved=True
        )
        self.stdout.write(self.style.SUCCESS('Superuser created successfully'))