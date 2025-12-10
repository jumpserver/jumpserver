# -*- coding: utf-8 -*-
#
from django.core.management.base import BaseCommand
from django.db.utils import OperationalError, ProgrammingError
from django.conf import settings


class Command(BaseCommand):
    help = 'Initialize OAuth2 Provider - Create default JumpServer Client application'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreate the application even if it exists',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        try:
            from authentication.backends.oauth2_provider.utils import (
                get_or_create_jumpserver_client_application
            )
            from oauth2_provider.models import get_application_model
            
            Application = get_application_model()
            
            # 检查表是否存在
            try:
                Application.objects.exists()
            except (OperationalError, ProgrammingError) as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'OAuth2 Provider tables not found. Please run migrations first:\n'
                        f'  python manage.py migrate oauth2_provider\n'
                        f'Error: {e}'
                    )
                )
                return
            
            # 如果强制重建，先删除已存在的应用
            if force:
                deleted_count, _ = Application.objects.filter(
                    name=settings.OAUTH2_PROVIDER_JUMPSERVER_CLIENT_NAME
                ).delete()
                if deleted_count > 0:
                    self.stdout.write(
                        self.style.WARNING(f'Deleted {deleted_count} existing application(s)')
                    )
            
            # 创建或获取应用
            application = get_or_create_jumpserver_client_application()
            
            if application:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ OAuth2 JumpServer Client application initialized successfully\n'
                        f'  - Client ID: {application.client_id}\n'
                        f'  - Client Type: {application.get_client_type_display()}\n'
                        f'  - Grant Type: {application.get_authorization_grant_type_display()}\n'
                        f'  - Redirect URIs: {application.redirect_uris}\n'
                        f'  - Skip Authorization: {application.skip_authorization}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR('Failed to create OAuth2 application')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error initializing OAuth2 Provider: {e}')
            )
            raise
