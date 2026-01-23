"""Скрипты бэкапов БД и чекпоинтов

Поддерживает:
- Full backup (pg_dump)
- WAL archiving (continuous)
- Daily scheduled backups
- Checkpoint backup (MCCFR models)
- Retention policy (30 days default)
"""

import os
import subprocess
import shutil
import schedule
import time
import threading
from datetime import datetime, timezone, timezone
from pathlib import Path
from typing import Optional, List
import json
import logging

from data.database import DATABASE_URL
from utils.backup_cloud import get_cloud_storage, CloudBackupStorage

logger = logging.getLogger(__name__)


class BackupManager:
    """Менеджер бэкапов"""
    
    def __init__(self, backup_dir: Optional[Path] = None, cloud_storage: Optional[CloudBackupStorage] = None):
        """
        Args:
            backup_dir: Директория для бэкапов (по умолчанию ./backups)
            cloud_storage: Облачное хранилище для синхронизации (опционально)
        """
        if backup_dir is None:
            backup_dir = Path("backups")
        
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Поддиректории
        self.db_backup_dir = self.backup_dir / "database"
        self.checkpoint_backup_dir = self.backup_dir / "checkpoints"
        self.db_backup_dir.mkdir(exist_ok=True)
        self.checkpoint_backup_dir.mkdir(exist_ok=True)
        
        # Облачное хранилище
        self.cloud_storage = cloud_storage or get_cloud_storage()
    
    def backup_database(self, full: bool = True) -> Path:
        """
        Создает бэкап PostgreSQL БД
        
        Args:
            full: True для полного бэкапа, False для инкрементального
            
        Returns:
            Путь к файлу бэкапа
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = self.db_backup_dir / f"pokerbot_db_{timestamp}.sql"
        
        # Парсим DATABASE_URL
        # Формат: postgresql://user:password@host:port/dbname
        db_url = DATABASE_URL.replace("postgresql://", "")
        
        if "@" in db_url:
            auth, rest = db_url.split("@")
            user, password = auth.split(":")
            host_port, dbname = rest.split("/")
            host, port = host_port.split(":") if ":" in host_port else (host_port, "5432")
        else:
            raise ValueError("Invalid DATABASE_URL format")
        
        # Создаем бэкап через pg_dump
        env = os.environ.copy()
        env["PGPASSWORD"] = password
        
        cmd = [
            "pg_dump",
            "-h", host,
            "-p", port,
            "-U", user,
            "-d", dbname,
            "-F", "c",  # Custom format
            "-f", str(backup_file)
        ]
        
        try:
            subprocess.run(cmd, env=env, check=True, capture_output=True)
            print(f"Бэкап БД создан: {backup_file}")
            
            # Сохраняем метаданные
            metadata = {
                "timestamp": timestamp,
                "type": "full" if full else "incremental",
                "file": str(backup_file),
                "size": backup_file.stat().st_size
            }
            
            metadata_file = backup_file.with_suffix(".json")
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Загружаем в облако если настроено
            if self.cloud_storage and self.cloud_storage.provider != "local":
                remote_path = f"database/{backup_file.name}"
                if self.cloud_storage.upload(backup_file, remote_path):
                    logger.info(f"Backup uploaded to {self.cloud_storage.provider}: {remote_path}")
            
            return backup_file
        
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при создании бэкапа БД: {e}")
            print(f"Stdout: {e.stdout.decode()}")
            print(f"Stderr: {e.stderr.decode()}")
            raise
    
    def backup_checkpoints(self, limit_type: Optional[str] = None) -> list:
        """
        Создает бэкап чекпоинтов обучения
        
        Args:
            limit_type: Лимит для бэкапа (если None, бэкапит все)
            
        Returns:
            Список путей к бэкапам
        """
        checkpoint_source = Path("checkpoints")
        if not checkpoint_source.exists():
            print("Директория checkpoints не найдена")
            return []
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_paths = []
        
        if limit_type:
            # Бэкап конкретного лимита
            source_dir = checkpoint_source / limit_type
            if source_dir.exists():
                dest_dir = self.checkpoint_backup_dir / f"{limit_type}_{timestamp}"
                shutil.copytree(source_dir, dest_dir)
                backup_paths.append(dest_dir)
                print(f"Бэкап чекпоинтов {limit_type} создан: {dest_dir}")
        else:
            # Бэкап всех чекпоинтов
            dest_dir = self.checkpoint_backup_dir / f"all_{timestamp}"
            shutil.copytree(checkpoint_source, dest_dir)
            backup_paths.append(dest_dir)
            print(f"Бэкап всех чекпоинтов создан: {dest_dir}")
        
        return backup_paths
    
    def restore_database(self, backup_file: Path) -> bool:
        """
        Восстанавливает БД из бэкапа
        
        Args:
            backup_file: Путь к файлу бэкапа
            
        Returns:
            True если успешно
        """
        if not backup_file.exists():
            print(f"Файл бэкапа не найден: {backup_file}")
            return False
        
        # Парсим DATABASE_URL
        db_url = DATABASE_URL.replace("postgresql://", "")
        auth, rest = db_url.split("@")
        user, password = auth.split(":")
        host_port, dbname = rest.split("/")
        host, port = host_port.split(":") if ":" in host_port else (host_port, "5432")
        
        env = os.environ.copy()
        env["PGPASSWORD"] = password
        
        cmd = [
            "pg_restore",
            "-h", host,
            "-p", port,
            "-U", user,
            "-d", dbname,
            "-c",  # Clean (drop objects)
            "-v",  # Verbose
            str(backup_file)
        ]
        
        try:
            subprocess.run(cmd, env=env, check=True, capture_output=True)
            print(f"БД восстановлена из: {backup_file}")
            return True
        
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при восстановлении БД: {e}")
            print(f"Stdout: {e.stdout.decode()}")
            print(f"Stderr: {e.stderr.decode()}")
            return False
    
    def cleanup_old_backups(self, days: int = 30):
        """
        Удаляет старые бэкапы

        Args:
            days: Количество дней для хранения
        """
        cutoff_date = datetime.now(timezone.utc).timestamp() - (days * 24 * 3600)

        for backup_file in self.db_backup_dir.glob("*.sql"):
            if backup_file.stat().st_mtime < cutoff_date:
                backup_file.unlink()
                metadata_file = backup_file.with_suffix(".json")
                if metadata_file.exists():
                    metadata_file.unlink()
                logger.info(f"Удален старый бэкап: {backup_file}")

        for backup_dir in self.checkpoint_backup_dir.iterdir():
            if backup_dir.is_dir() and backup_dir.stat().st_mtime < cutoff_date:
                shutil.rmtree(backup_dir)
                logger.info(f"Удален старый бэкап чекпоинтов: {backup_dir}")

    def setup_wal_archiving(self, wal_archive_dir: Optional[Path] = None) -> bool:
        """
        Настраивает WAL archiving для PostgreSQL

        WAL (Write-Ahead Logging) обеспечивает point-in-time recovery

        Args:
            wal_archive_dir: Директория для WAL файлов

        Returns:
            True если успешно
        """
        if wal_archive_dir is None:
            wal_archive_dir = self.backup_dir / "wal_archive"

        wal_archive_dir.mkdir(parents=True, exist_ok=True)

        # Парсим DATABASE_URL
        db_url = DATABASE_URL.replace("postgresql://", "")
        auth, rest = db_url.split("@")
        user, password = auth.split(":")
        host_port, dbname = rest.split("/")
        host, port = host_port.split(":") if ":" in host_port else (host_port, "5432")

        env = os.environ.copy()
        env["PGPASSWORD"] = password

        # SQL для настройки WAL archiving
        wal_config_sql = f"""
        ALTER SYSTEM SET archive_mode = on;
        ALTER SYSTEM SET archive_command = 'cp %p {wal_archive_dir}/%f';
        ALTER SYSTEM SET wal_level = replica;
        SELECT pg_reload_conf();
        """

        cmd = [
            "psql",
            "-h", host,
            "-p", port,
            "-U", user,
            "-d", dbname,
            "-c", wal_config_sql
        ]

        try:
            subprocess.run(cmd, env=env, check=True, capture_output=True)
            logger.info(f"WAL archiving настроен: {wal_archive_dir}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка настройки WAL: {e.stderr.decode()}")
            return False

    def backup_wal_files(self) -> List[Path]:
        """
        Копирует текущие WAL файлы в архив

        Returns:
            Список скопированных файлов
        """
        wal_archive_dir = self.backup_dir / "wal_archive"
        wal_archive_dir.mkdir(parents=True, exist_ok=True)

        # Парсим DATABASE_URL для получения данных
        db_url = DATABASE_URL.replace("postgresql://", "")
        auth, rest = db_url.split("@")
        user, password = auth.split(":")
        host_port, dbname = rest.split("/")
        host, port = host_port.split(":") if ":" in host_port else (host_port, "5432")

        env = os.environ.copy()
        env["PGPASSWORD"] = password

        # Принудительно переключаем WAL сегмент
        cmd = [
            "psql",
            "-h", host,
            "-p", port,
            "-U", user,
            "-d", dbname,
            "-c", "SELECT pg_switch_wal();"
        ]

        try:
            subprocess.run(cmd, env=env, check=True, capture_output=True)
            logger.info("WAL switch выполнен")
            return list(wal_archive_dir.glob("*"))
        except subprocess.CalledProcessError as e:
            logger.warning(f"WAL switch не выполнен: {e.stderr.decode()}")
            return []

    def full_backup_with_wal(self) -> dict:
        """
        Полный бэкап с WAL для point-in-time recovery

        Returns:
            Словарь с информацией о бэкапе
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        result = {
            "timestamp": timestamp,
            "db_backup": None,
            "checkpoint_backup": [],
            "wal_files": [],
            "status": "success"
        }

        try:
            # 1. Полный бэкап БД
            result["db_backup"] = str(self.backup_database(full=True))

            # 2. Бэкап чекпоинтов
            result["checkpoint_backup"] = [str(p) for p in self.backup_checkpoints()]

            # 3. WAL switch и архив
            result["wal_files"] = [str(p) for p in self.backup_wal_files()]

            # 4. Очистка старых бэкапов
            self.cleanup_old_backups(days=30)

            logger.info(f"Full backup completed: {result}")

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"Backup failed: {e}")

        # Сохраняем отчет
        report_file = self.backup_dir / f"backup_report_{timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(result, f, indent=2)

        return result


class BackupScheduler:
    """Планировщик автоматических бэкапов"""

    def __init__(self, backup_manager: BackupManager):
        self.manager = backup_manager
        self.running = False
        self._thread: Optional[threading.Thread] = None

    def start(self, daily_time: str = "03:00"):
        """
        Запускает планировщик

        Args:
            daily_time: Время ежедневного бэкапа (HH:MM)
        """
        # Daily full backup
        schedule.every().day.at(daily_time).do(self._daily_backup)

        # Hourly WAL backup
        schedule.every().hour.do(self._hourly_wal_backup)

        # Weekly cleanup
        schedule.every().sunday.at("04:00").do(self._weekly_cleanup)

        self.running = True
        self._thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._thread.start()

        logger.info(f"Backup scheduler started. Daily backup at {daily_time}")

    def stop(self):
        """Останавливает планировщик"""
        self.running = False
        schedule.clear()
        logger.info("Backup scheduler stopped")

    def _run_scheduler(self):
        """Цикл планировщика"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)

    def _daily_backup(self):
        """Ежедневный полный бэкап"""
        logger.info("Starting daily backup...")
        try:
            result = self.manager.full_backup_with_wal()
            if result["status"] == "success":
                logger.info("Daily backup completed successfully")
            else:
                logger.error(f"Daily backup failed: {result.get('error')}")
        except Exception as e:
            logger.error(f"Daily backup exception: {e}")

    def _hourly_wal_backup(self):
        """Почасовой бэкап WAL"""
        try:
            wal_files = self.manager.backup_wal_files()
            logger.info(f"Hourly WAL backup: {len(wal_files)} files")
        except Exception as e:
            logger.warning(f"WAL backup failed: {e}")

    def _weekly_cleanup(self):
        """Еженедельная очистка"""
        logger.info("Starting weekly cleanup...")
        self.manager.cleanup_old_backups(days=30)


def main():
    """CLI для бэкапов"""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description="Управление бэкапами PokerBot")
    parser.add_argument("--backup-db", action="store_true",
                       help="Создать бэкап БД")
    parser.add_argument("--backup-checkpoints", action="store_true",
                       help="Создать бэкап чекпоинтов")
    parser.add_argument("--full-backup", action="store_true",
                       help="Полный бэкап (БД + чекпоинты + WAL)")
    parser.add_argument("--limit", type=str,
                       help="Лимит для бэкапа чекпоинтов")
    parser.add_argument("--restore-db", type=str,
                       help="Восстановить БД из файла")
    parser.add_argument("--cleanup", type=int,
                       help="Удалить бэкапы старше N дней")
    parser.add_argument("--setup-wal", action="store_true",
                       help="Настроить WAL archiving")
    parser.add_argument("--scheduler", action="store_true",
                       help="Запустить планировщик бэкапов")
    parser.add_argument("--daily-time", type=str, default="03:00",
                       help="Время ежедневного бэкапа (HH:MM)")

    args = parser.parse_args()

    manager = BackupManager()

    if args.backup_db:
        manager.backup_database()

    if args.backup_checkpoints:
        manager.backup_checkpoints(args.limit)

    if args.full_backup:
        result = manager.full_backup_with_wal()
        print(f"Full backup result: {json.dumps(result, indent=2)}")

    if args.restore_db:
        manager.restore_database(Path(args.restore_db))

    if args.cleanup:
        manager.cleanup_old_backups(args.cleanup)

    if args.setup_wal:
        manager.setup_wal_archiving()

    if args.scheduler:
        print(f"Starting backup scheduler (daily at {args.daily_time})...")
        scheduler = BackupScheduler(manager)
        scheduler.start(daily_time=args.daily_time)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            scheduler.stop()
            print("Scheduler stopped")


if __name__ == "__main__":
    main()
