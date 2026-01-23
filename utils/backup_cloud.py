"""
Интеграция бэкапов с облачными хранилищами (S3/GCS)

Поддерживает:
- AWS S3
- Google Cloud Storage
- Локальное хранилище (fallback)
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class CloudBackupStorage:
    """Абстракция для облачного хранилища бэкапов"""

    def __init__(self, provider: str = "local", **config):
        """
        Args:
            provider: "s3", "gcs", или "local"
            **config: Конфигурация провайдера
        """
        self.provider = provider
        self.config = config

    def upload(self, local_path: Path, remote_path: str) -> bool:
        """Загружает файл в облако"""
        try:
            if self.provider == "s3":
                return self._upload_s3(local_path, remote_path)
            elif self.provider == "gcs":
                return self._upload_gcs(local_path, remote_path)
            else:
                # Локальное хранилище - просто копируем
                return self._upload_local(local_path, remote_path)
        except Exception as e:
            logger.error(f"Failed to upload {local_path} to {self.provider}: {e}")
            return False

    def download(self, remote_path: str, local_path: Path) -> bool:
        """Скачивает файл из облака"""
        try:
            if self.provider == "s3":
                return self._download_s3(remote_path, local_path)
            elif self.provider == "gcs":
                return self._download_gcs(remote_path, local_path)
            else:
                return self._download_local(remote_path, local_path)
        except Exception as e:
            logger.error(f"Failed to download {remote_path} from {self.provider}: {e}")
            return False

    def list_backups(self, prefix: str = "") -> list:
        """Список бэкапов в облаке"""
        try:
            if self.provider == "s3":
                return self._list_s3(prefix)
            elif self.provider == "gcs":
                return self._list_gcs(prefix)
            else:
                return self._list_local(prefix)
        except Exception as e:
            logger.error(f"Failed to list backups from {self.provider}: {e}")
            return []

    def delete(self, remote_path: str) -> bool:
        """Удаляет файл из облака"""
        try:
            if self.provider == "s3":
                return self._delete_s3(remote_path)
            elif self.provider == "gcs":
                return self._delete_gcs(remote_path)
            else:
                return self._delete_local(remote_path)
        except Exception as e:
            logger.error(f"Failed to delete {remote_path} from {self.provider}: {e}")
            return False

    # ============================================
    # AWS S3 Implementation
    # ============================================

    def _upload_s3(self, local_path: Path, remote_path: str) -> bool:
        """Загрузка в S3"""
        try:
            import boto3
            from botocore.exceptions import ClientError

            s3_client = boto3.client(
                's3',
                aws_access_key_id=self.config.get("aws_access_key_id") or os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=self.config.get("aws_secret_access_key") or os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=self.config.get("aws_region") or os.getenv("AWS_REGION", "us-east-1")
            )

            bucket = self.config.get("bucket") or os.getenv("S3_BACKUP_BUCKET")
            if not bucket:
                logger.error("S3 bucket not configured")
                return False

            s3_client.upload_file(str(local_path), bucket, remote_path)
            logger.info(f"Uploaded {local_path} to s3://{bucket}/{remote_path}")
            return True

        except ImportError:
            logger.warning("boto3 not installed, S3 backup disabled")
            return False
        except ClientError as e:
            logger.error(f"S3 upload error: {e}")
            return False

    def _download_s3(self, remote_path: str, local_path: Path) -> bool:
        """Скачивание из S3"""
        try:
            import boto3
            from botocore.exceptions import ClientError

            s3_client = boto3.client(
                's3',
                aws_access_key_id=self.config.get("aws_access_key_id") or os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=self.config.get("aws_secret_access_key") or os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=self.config.get("aws_region") or os.getenv("AWS_REGION", "us-east-1")
            )

            bucket = self.config.get("bucket") or os.getenv("S3_BACKUP_BUCKET")
            if not bucket:
                return False

            local_path.parent.mkdir(parents=True, exist_ok=True)
            s3_client.download_file(bucket, remote_path, str(local_path))
            logger.info(f"Downloaded s3://{bucket}/{remote_path} to {local_path}")
            return True

        except ImportError:
            return False
        except ClientError as e:
            logger.error(f"S3 download error: {e}")
            return False

    def _list_s3(self, prefix: str) -> list:
        """Список файлов в S3"""
        try:
            import boto3

            s3_client = boto3.client(
                's3',
                aws_access_key_id=self.config.get("aws_access_key_id") or os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=self.config.get("aws_secret_access_key") or os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=self.config.get("aws_region") or os.getenv("AWS_REGION", "us-east-1")
            )

            bucket = self.config.get("bucket") or os.getenv("S3_BACKUP_BUCKET")
            if not bucket:
                return []

            response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            return [obj["Key"] for obj in response.get("Contents", [])]

        except ImportError:
            return []
        except Exception as e:
            logger.error(f"S3 list error: {e}")
            return []

    def _delete_s3(self, remote_path: str) -> bool:
        """Удаление из S3"""
        try:
            import boto3

            s3_client = boto3.client(
                's3',
                aws_access_key_id=self.config.get("aws_access_key_id") or os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=self.config.get("aws_secret_access_key") or os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=self.config.get("aws_region") or os.getenv("AWS_REGION", "us-east-1")
            )

            bucket = self.config.get("bucket") or os.getenv("S3_BACKUP_BUCKET")
            if not bucket:
                return False

            s3_client.delete_object(Bucket=bucket, Key=remote_path)
            logger.info(f"Deleted s3://{bucket}/{remote_path}")
            return True

        except ImportError:
            return False
        except Exception as e:
            logger.error(f"S3 delete error: {e}")
            return False

    # ============================================
    # Google Cloud Storage Implementation
    # ============================================

    def _upload_gcs(self, local_path: Path, remote_path: str) -> bool:
        """Загрузка в GCS"""
        try:
            from google.cloud import storage
            from google.cloud.exceptions import GoogleCloudError

            client = storage.Client()
            bucket_name = self.config.get("bucket") or os.getenv("GCS_BACKUP_BUCKET")
            if not bucket_name:
                logger.error("GCS bucket not configured")
                return False

            bucket = client.bucket(bucket_name)
            blob = bucket.blob(remote_path)
            blob.upload_from_filename(str(local_path))
            logger.info(f"Uploaded {local_path} to gs://{bucket_name}/{remote_path}")
            return True

        except ImportError:
            logger.warning("google-cloud-storage not installed, GCS backup disabled")
            return False
        except GoogleCloudError as e:
            logger.error(f"GCS upload error: {e}")
            return False

    def _download_gcs(self, remote_path: str, local_path: Path) -> bool:
        """Скачивание из GCS"""
        try:
            from google.cloud import storage
            from google.cloud.exceptions import GoogleCloudError

            client = storage.Client()
            bucket_name = self.config.get("bucket") or os.getenv("GCS_BACKUP_BUCKET")
            if not bucket_name:
                return False

            bucket = client.bucket(bucket_name)
            blob = bucket.blob(remote_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(str(local_path))
            logger.info(f"Downloaded gs://{bucket_name}/{remote_path} to {local_path}")
            return True

        except ImportError:
            return False
        except GoogleCloudError as e:
            logger.error(f"GCS download error: {e}")
            return False

    def _list_gcs(self, prefix: str) -> list:
        """Список файлов в GCS"""
        try:
            from google.cloud import storage

            client = storage.Client()
            bucket_name = self.config.get("bucket") or os.getenv("GCS_BACKUP_BUCKET")
            if not bucket_name:
                return []

            bucket = client.bucket(bucket_name)
            blobs = bucket.list_blobs(prefix=prefix)
            return [blob.name for blob in blobs]

        except ImportError:
            return []
        except Exception as e:
            logger.error(f"GCS list error: {e}")
            return []

    def _delete_gcs(self, remote_path: str) -> bool:
        """Удаление из GCS"""
        try:
            from google.cloud import storage

            client = storage.Client()
            bucket_name = self.config.get("bucket") or os.getenv("GCS_BACKUP_BUCKET")
            if not bucket_name:
                return False

            bucket = client.bucket(bucket_name)
            blob = bucket.blob(remote_path)
            blob.delete()
            logger.info(f"Deleted gs://{bucket_name}/{remote_path}")
            return True

        except ImportError:
            return False
        except Exception as e:
            logger.error(f"GCS delete error: {e}")
            return False

    # ============================================
    # Local Storage Implementation (fallback)
    # ============================================

    def _upload_local(self, local_path: Path, remote_path: str) -> bool:
        """Локальное копирование"""
        import shutil
        dest = Path(self.config.get("local_backup_dir", "backups/cloud")) / remote_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, dest)
        logger.info(f"Copied {local_path} to {dest}")
        return True

    def _download_local(self, remote_path: str, local_path: Path) -> bool:
        """Локальное копирование"""
        import shutil
        source = Path(self.config.get("local_backup_dir", "backups/cloud")) / remote_path
        if not source.exists():
            return False
        local_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, local_path)
        return True

    def _list_local(self, prefix: str) -> list:
        """Список локальных файлов"""
        backup_dir = Path(self.config.get("local_backup_dir", "backups/cloud"))
        if not backup_dir.exists():
            return []
        return [str(p.relative_to(backup_dir)) for p in backup_dir.rglob("*") if p.is_file() and str(p).startswith(str(backup_dir / prefix))]

    def _delete_local(self, remote_path: str) -> bool:
        """Удаление локального файла"""
        file_path = Path(self.config.get("local_backup_dir", "backups/cloud")) / remote_path
        if file_path.exists():
            file_path.unlink()
            return True
        return False


def get_cloud_storage(provider: Optional[str] = None) -> Optional[CloudBackupStorage]:
    """
    Создает CloudBackupStorage на основе env переменных

    Env переменные:
    - BACKUP_PROVIDER: "s3", "gcs", или "local" (по умолчанию)
    - Для S3: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BACKUP_BUCKET
    - Для GCS: GOOGLE_APPLICATION_CREDENTIALS, GCS_BACKUP_BUCKET
    """
    provider = provider or os.getenv("BACKUP_PROVIDER", "local")
    return CloudBackupStorage(provider=provider)
