"""Скрипты бэкапов БД и чекпоинтов"""

import os
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

from data.database import DATABASE_URL


class BackupManager:
    """Менеджер бэкапов"""
    
    def __init__(self, backup_dir: Optional[Path] = None):
        """
        Args:
            backup_dir: Директория для бэкапов (по умолчанию ./backups)
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
    
    def backup_database(self, full: bool = True) -> Path:
        """
        Создает бэкап PostgreSQL БД
        
        Args:
            full: True для полного бэкапа, False для инкрементального
            
        Returns:
            Путь к файлу бэкапа
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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
        cutoff_date = datetime.now().timestamp() - (days * 24 * 3600)
        
        for backup_file in self.db_backup_dir.glob("*.sql"):
            if backup_file.stat().st_mtime < cutoff_date:
                backup_file.unlink()
                metadata_file = backup_file.with_suffix(".json")
                if metadata_file.exists():
                    metadata_file.unlink()
                print(f"Удален старый бэкап: {backup_file}")
        
        for backup_dir in self.checkpoint_backup_dir.iterdir():
            if backup_dir.is_dir() and backup_dir.stat().st_mtime < cutoff_date:
                shutil.rmtree(backup_dir)
                print(f"Удален старый бэкап чекпоинтов: {backup_dir}")


def main():
    """CLI для бэкапов"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Управление бэкапами")
    parser.add_argument("--backup-db", action="store_true",
                       help="Создать бэкап БД")
    parser.add_argument("--backup-checkpoints", action="store_true",
                       help="Создать бэкап чекпоинтов")
    parser.add_argument("--limit", type=str,
                       help="Лимит для бэкапа чекпоинтов")
    parser.add_argument("--restore-db", type=str,
                       help="Восстановить БД из файла")
    parser.add_argument("--cleanup", type=int, default=30,
                       help="Удалить бэкапы старше N дней")
    
    args = parser.parse_args()
    
    manager = BackupManager()
    
    if args.backup_db:
        manager.backup_database()
    
    if args.backup_checkpoints:
        manager.backup_checkpoints(args.limit)
    
    if args.restore_db:
        manager.restore_database(Path(args.restore_db))
    
    if args.cleanup:
        manager.cleanup_old_backups(args.cleanup)


if __name__ == "__main__":
    main()
