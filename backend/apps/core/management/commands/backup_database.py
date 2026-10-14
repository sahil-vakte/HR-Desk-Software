from pathlib import Path
import sqlite3
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
class Command(BaseCommand):
    help='Create a consistent SQLite backup using the online backup API, including committed WAL data.'
    def add_arguments(self,parser):parser.add_argument('destination')
    def handle(self,*args,**options):
        if connection.vendor!='sqlite':raise CommandError('Use your PostgreSQL backup tooling for this database.')
        path=Path(options['destination']).resolve()
        if path.exists():raise CommandError('Destination already exists; choose a new backup filename.')
        if settings.STATIC_ROOT.resolve() in path.parents:raise CommandError('Backups must be outside the public web root.')
        path.parent.mkdir(parents=True,exist_ok=True)
        connection.ensure_connection()
        with sqlite3.connect(path) as output:
            connection.connection.backup(output)
            if output.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise CommandError('Backup integrity check failed.')
        path.chmod(0o600)
        self.stdout.write(f'Created verified backup: {path}')
