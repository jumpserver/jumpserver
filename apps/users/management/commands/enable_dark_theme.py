"""
Django management command to enable dark theme for JumpServer users
Usage: python manage.py enable_dark_theme [--all-users] [--default-new-users]
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.conf import settings


class Command(BaseCommand):
    help = 'Enable dark theme for JumpServer users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all-users',
            action='store_true',
            help='Enable dark theme for all existing users',
        )
        parser.add_argument(
            '--default-new-users',
            action='store_true',
            help='Set dark theme as default for new users',
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Enable dark theme for specific username',
        )
        parser.add_argument(
            '--theme',
            type=str,
            choices=['auto', 'light', 'dark', 'classic_green'],
            default='dark',
            help='Theme to set (default: dark)',
        )

    def handle(self, *args, **options):
        User = get_user_model()
        theme = options['theme']
        
        if options['all_users']:
            self.enable_for_all_users(User, theme)
        elif options['username']:
            self.enable_for_user(User, options['username'], theme)
        elif options['default_new_users']:
            self.set_default_theme(theme)
        else:
            self.stdout.write(
                self.style.WARNING(
                    'Please specify --all-users, --username <username>, or --default-new-users'
                )
            )
            return

    def enable_for_all_users(self, User, theme):
        """Enable theme for all existing users"""
        try:
            # Check if theme_preference field exists
            if hasattr(User._meta.get_field('theme_preference'), 'name'):
                updated_count = User.objects.update(theme_preference=theme)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully updated theme to "{theme}" for {updated_count} users'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        'theme_preference field not found. Please run migrations first.'
                    )
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error updating users: {str(e)}')
            )

    def enable_for_user(self, User, username, theme):
        """Enable theme for specific user"""
        try:
            user = User.objects.get(username=username)
            if hasattr(user, 'theme_preference'):
                user.theme_preference = theme
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully updated theme to "{theme}" for user "{username}"'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        'theme_preference field not found. Please run migrations first.'
                    )
                )
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User "{username}" not found')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error updating user: {str(e)}')
            )

    def set_default_theme(self, theme):
        """Set default theme for new users"""
        self.stdout.write(
            self.style.SUCCESS(
                f'To set "{theme}" as default for new users, update your settings.py:'
            )
        )
        self.stdout.write(
            f'DEFAULT_USER_THEME = "{theme}"'
        )
        self.stdout.write(
            'Or modify the User model default value and create a migration.'
        )
