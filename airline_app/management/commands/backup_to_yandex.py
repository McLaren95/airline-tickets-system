import os
import subprocess
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
import yadisk


class Command(BaseCommand):
    help = 'Создание бэкапа БД и отправка в Яндекс.Диск'

    def handle(self, *args, **options):
        self.stdout.write("Начало создания резервной копии...")

        backup_path = self.create_local_backup()

        if backup_path:
            self.upload_to_yandex(backup_path)

            self.clean_old_backups()

            self.stdout.write(self.style.SUCCESS("Бэкап успешно создан и отправлен!"))
        else:
            self.stdout.write(self.style.ERROR("Ошибка при создании бэкапа"))

    def create_local_backup(self):
        try:
            db = settings.DATABASES['default']

            backup_dir = os.path.join(settings.BASE_DIR, 'backups')
            os.makedirs(backup_dir, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'airline_db_{timestamp}.backup'
            filepath = os.path.join(backup_dir, filename)

            cmd = [
                'pg_dump',
                '-h', db['HOST'],
                '-U', db['USER'],
                '-d', db['NAME'],
                '-F', 'c',
                '-f', filepath
            ]

            self.stdout.write(f"Создаем бэкап: {filename}")

            env = os.environ.copy()
            env['PGPASSWORD'] = db['PASSWORD']

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                file_size = os.path.getsize(filepath) / 1024 / 1024  # в MB
                self.stdout.write(f"Размер бэкапа: {file_size:.2f} MB")
                return filepath
            else:
                self.stdout.write(self.style.ERROR(f"Ошибка pg_dump: {result.stderr}"))
                return None

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Исключение: {str(e)}"))
            return None

    def upload_to_yandex(self, filepath):
        try:
            token = getattr(settings, 'YANDEX_DISK_TOKEN', None)

            if not token:
                self.stdout.write(self.style.WARNING(
                    "Токен Яндекс.Диска не настроен. Бэкап сохранен только локально."
                ))
                return

            y = yadisk.YaDisk(token=token)

            if not y.check_token():
                self.stdout.write(self.style.ERROR("Неверный токен Яндекс.Диска"))
                return

            remote_folder = "/airline_backups/"
            if not y.exists(remote_folder):
                y.mkdir(remote_folder)

            filename = os.path.basename(filepath)
            remote_path = f"{remote_folder}{filename}"

            self.stdout.write(f"Отправляем в Яндекс.Диск: {filename}")
            y.upload(filepath, remote_path)

            self.stdout.write(self.style.SUCCESS(
                f"Файл загружен в Яндекс.Диск: {remote_path}"
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка Яндекс.Диска: {str(e)}"))

    def clean_old_backups(self, keep_days=3):
        try:
            backup_dir = os.path.join(settings.BASE_DIR, 'backups')
            cutoff_date = datetime.now() - timedelta(days=keep_days)

            for filename in os.listdir(backup_dir):
                if filename.endswith('.backup'):
                    filepath = os.path.join(backup_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getctime(filepath))

                    if file_time < cutoff_date:
                        os.remove(filepath)
                        self.stdout.write(f"Удален старый бэкап: {filename}")

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Ошибка очистки: {str(e)}"))