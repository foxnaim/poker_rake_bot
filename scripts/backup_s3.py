#!/usr/bin/env python3
"""
Автоматический backup PostgreSQL на S3/MinIO

Функции:
- Создание pg_dump
- Сжатие gzip
- Загрузка в S3
- Ротация старых бэкапов (retention)
- Уведомления при ошибках

Использование:
    # Разовый backup
    python scripts/backup_s3.py

    # С конкретными параметрами
    python scripts/backup_s3.py --bucket my-bucket --retention 30

    # Установка в cron
    python scripts/backup_s3.py --setup-cron

Переменные окружения:
    DATABASE_URL - URL базы данных
    AWS_ACCESS_KEY_ID - AWS/MinIO access key
    AWS_SECRET_ACCESS_KEY - AWS/MinIO secret key
    S3_BUCKET - имя бакета
    S3_ENDPOINT_URL - endpoint для MinIO (опционально)
    BACKUP_RETENTION_DAYS - дней хранения (по умолчанию 30)
"""

import os
import sys
import gzip
import subprocess
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
import json

# Добавляем корень проекта
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_env(key: str, default: str = None, required: bool = False) -> Optional[str]:
    """Получает переменную окружения"""
    value = os.getenv(key, default)
    if required and not value:
        print(f"ERROR: {key} environment variable is required")
        sys.exit(1)
    return value


def parse_database_url(url: str) -> dict:
    """Парсит DATABASE_URL в компоненты"""
    # postgresql://user:pass@host:port/dbname
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "user": parsed.username or "pokerbot",
        "password": parsed.password or "",
        "dbname": parsed.path.lstrip("/") or "pokerbot_db"
    }


def create_pg_dump(db_config: dict, output_path: Path) -> bool:
    """Создаёт pg_dump и сжимает его"""
    print(f"Creating backup: {output_path}")

    env = os.environ.copy()
    env["PGPASSWORD"] = db_config["password"]

    dump_cmd = [
        "pg_dump",
        "-h", db_config["host"],
        "-p", str(db_config["port"]),
        "-U", db_config["user"],
        "-d", db_config["dbname"],
        "--format=custom",
        "--compress=9",
        "-f", str(output_path)
    ]

    try:
        result = subprocess.run(
            dump_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=600  # 10 минут максимум
        )

        if result.returncode != 0:
            print(f"pg_dump error: {result.stderr}")
            return False

        print(f"Backup created: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
        return True

    except subprocess.TimeoutExpired:
        print("pg_dump timeout!")
        return False
    except FileNotFoundError:
        print("pg_dump not found. Install PostgreSQL client tools.")
        return False
    except Exception as e:
        print(f"pg_dump error: {e}")
        return False


def upload_to_s3(
    file_path: Path,
    bucket: str,
    s3_key: str,
    endpoint_url: Optional[str] = None
) -> bool:
    """Загружает файл в S3/MinIO"""
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        print("boto3 not installed. Run: pip install boto3")
        return False

    print(f"Uploading to s3://{bucket}/{s3_key}")

    try:
        config = Config(
            signature_version='s3v4',
            retries={'max_attempts': 3}
        )

        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            config=config
        )

        # Загружаем с прогрессом
        file_size = file_path.stat().st_size

        def progress_callback(bytes_transferred):
            percent = (bytes_transferred / file_size) * 100
            print(f"\r  Progress: {percent:.1f}%", end="", flush=True)

        s3_client.upload_file(
            str(file_path),
            bucket,
            s3_key,
            Callback=progress_callback
        )

        print(f"\n  Uploaded: s3://{bucket}/{s3_key}")
        return True

    except Exception as e:
        print(f"\nS3 upload error: {e}")
        return False


def cleanup_old_backups(
    bucket: str,
    prefix: str,
    retention_days: int,
    endpoint_url: Optional[str] = None
) -> int:
    """Удаляет бэкапы старше retention_days"""
    try:
        import boto3
    except ImportError:
        return 0

    print(f"Cleaning up backups older than {retention_days} days...")

    try:
        s3_client = boto3.client('s3', endpoint_url=endpoint_url)

        # Получаем список объектов
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix
        )

        if 'Contents' not in response:
            print("  No existing backups found")
            return 0

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        deleted_count = 0

        for obj in response['Contents']:
            if obj['LastModified'] < cutoff_date:
                s3_client.delete_object(Bucket=bucket, Key=obj['Key'])
                print(f"  Deleted: {obj['Key']}")
                deleted_count += 1

        print(f"  Cleaned up {deleted_count} old backups")
        return deleted_count

    except Exception as e:
        print(f"Cleanup error: {e}")
        return 0


def setup_cron():
    """Настраивает cron job для ежедневного бэкапа"""
    script_path = Path(__file__).resolve()
    python_path = sys.executable

    cron_line = f"0 3 * * * {python_path} {script_path} >> /var/log/pokerbot-backup.log 2>&1"

    print("Add this line to crontab (crontab -e):")
    print()
    print(cron_line)
    print()
    print("This will run backup daily at 3:00 AM")


def main():
    parser = argparse.ArgumentParser(description="Backup PostgreSQL to S3")
    parser.add_argument("--bucket", default=os.getenv("S3_BUCKET"), help="S3 bucket name")
    parser.add_argument("--prefix", default="backups/pokerbot", help="S3 key prefix")
    parser.add_argument("--retention", type=int, default=int(os.getenv("BACKUP_RETENTION_DAYS", "30")),
                        help="Days to keep backups")
    parser.add_argument("--endpoint", default=os.getenv("S3_ENDPOINT_URL"), help="S3 endpoint URL (for MinIO)")
    parser.add_argument("--setup-cron", action="store_true", help="Show cron setup instructions")
    parser.add_argument("--local-only", action="store_true", help="Only create local backup, don't upload")
    args = parser.parse_args()

    if args.setup_cron:
        setup_cron()
        return

    # Проверяем конфигурацию
    database_url = get_env("DATABASE_URL", required=True)
    db_config = parse_database_url(database_url)

    if not args.local_only:
        if not args.bucket:
            print("ERROR: S3_BUCKET or --bucket is required")
            print("Use --local-only for local backup only")
            sys.exit(1)

        # Проверяем AWS credentials
        if not os.getenv("AWS_ACCESS_KEY_ID"):
            print("WARNING: AWS_ACCESS_KEY_ID not set")

    # Создаём backup
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(__file__).parent.parent / "backups"
    backup_dir.mkdir(exist_ok=True)

    backup_filename = f"pokerbot_{timestamp}.dump"
    backup_path = backup_dir / backup_filename

    success = create_pg_dump(db_config, backup_path)

    if not success:
        print("Backup FAILED!")
        sys.exit(1)

    # Загружаем в S3
    if not args.local_only and args.bucket:
        s3_key = f"{args.prefix}/{backup_filename}"

        upload_success = upload_to_s3(
            backup_path,
            args.bucket,
            s3_key,
            args.endpoint
        )

        if upload_success:
            # Удаляем локальный файл после успешной загрузки
            backup_path.unlink()
            print(f"Local backup removed: {backup_path}")

            # Чистим старые бэкапы
            cleanup_old_backups(
                args.bucket,
                args.prefix,
                args.retention,
                args.endpoint
            )
        else:
            print("Upload failed, keeping local backup")
            sys.exit(1)
    else:
        print(f"Local backup saved: {backup_path}")

    # Сохраняем метаданные последнего бэкапа
    metadata = {
        "timestamp": timestamp,
        "filename": backup_filename,
        "size_bytes": backup_path.stat().st_size if backup_path.exists() else 0,
        "database": db_config["dbname"],
        "s3_bucket": args.bucket,
        "s3_key": f"{args.prefix}/{backup_filename}" if args.bucket else None
    }

    metadata_path = backup_dir / "last_backup.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print("\nBackup completed successfully!")


if __name__ == "__main__":
    main()
