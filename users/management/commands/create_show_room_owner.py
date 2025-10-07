from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a show room owner user'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email address for the show room owner')
        parser.add_argument('--password', type=str, help='Password for the show room owner')
        parser.add_argument('--first-name', type=str, help='First name')
        parser.add_argument('--last-name', type=str, help='Last name')

    def handle(self, *args, **options):
        email = options['email']
        password = options.get('password', 'defaultpassword123')
        first_name = options.get('first_name', '')
        last_name = options.get('last_name', '')

        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.ERROR(f'User with email {email} already exists')
            )
            return

        user = User.objects.create_user(
            email=email,
            password=password,
            role='show_room_owner',
            first_name=first_name,
            last_name=last_name
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created show room owner: {email}\n'
                f'Role: {user.role}\n'
                f'Password: {password}'
            )
        )