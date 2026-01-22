#!/usr/bin/env python3
"""
Скрипт для настройки автоматических бэкапов через systemd/cron

Использование:
    python scripts/setup_backup_scheduler.py --method systemd
    python scripts/setup_backup_scheduler.py --method cron
"""

import argparse
import os
from pathlib import Path


def create_systemd_service(backup_time: str = "03:00"):
    """Создает systemd service для автоматических бэкапов"""
    project_dir = Path(__file__).parent.parent
    service_content = f"""[Unit]
Description=PokerBot Backup Scheduler
After=network.target postgresql.service

[Service]
Type=simple
User={os.getenv('USER', 'pokerbot')}
WorkingDirectory={project_dir}
Environment="DATABASE_URL={os.getenv('DATABASE_URL', 'postgresql://pokerbot:pokerbot_dev@localhost:5432/pokerbot_db')}"
ExecStart=/usr/bin/python3 -m utils.backup --scheduler --daily-time {backup_time}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    service_file = Path("/etc/systemd/system/pokerbot-backup.service")
    print(f"Creating systemd service: {service_file}")
    print("\nService content:")
    print(service_content)
    print("\nTo install:")
    print(f"  sudo cp {service_file} /etc/systemd/system/")
    print("  sudo systemctl daemon-reload")
    print("  sudo systemctl enable pokerbot-backup")
    print("  sudo systemctl start pokerbot-backup")
    
    # Сохраняем в проект для справки
    local_service_file = project_dir / "scripts" / "pokerbot-backup.service"
    local_service_file.write_text(service_content)
    print(f"\n✅ Service file saved to: {local_service_file}")


def create_cron_job(backup_time: str = "03:00"):
    """Создает cron job для автоматических бэкапов"""
    hour, minute = backup_time.split(":")
    project_dir = Path(__file__).parent.parent
    
    cron_line = f"{minute} {hour} * * * cd {project_dir} && /usr/bin/python3 -m utils.backup --full-backup >> {project_dir}/logs/backup.log 2>&1"
    
    print("Cron job line:")
    print(cron_line)
    print("\nTo install:")
    print("  crontab -e")
    print("  # Add the line above")
    print(f"\nOr use: echo '{cron_line}' | crontab -")
    
    # Сохраняем в файл для справки
    cron_file = project_dir / "scripts" / "backup.cron"
    cron_file.write_text(cron_line + "\n")
    print(f"\n✅ Cron job saved to: {cron_file}")


def main():
    parser = argparse.ArgumentParser(description="Setup automatic backups")
    parser.add_argument("--method", choices=["systemd", "cron"], default="systemd",
                       help="Method for scheduling backups")
    parser.add_argument("--daily-time", default="03:00",
                       help="Daily backup time (HH:MM)")
    
    args = parser.parse_args()
    
    if args.method == "systemd":
        create_systemd_service(args.daily_time)
    else:
        create_cron_job(args.daily_time)


if __name__ == "__main__":
    main()
