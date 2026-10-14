"""Create or extend local environment files without overwriting configured values."""
from pathlib import Path
import secrets
import base64
import os

root=Path(__file__).resolve().parent.parent
for directory in ['backend','frontend']:
    target=root/directory/'.env'
    content=target.read_text() if target.exists() else ''
    existing={line.split('=',1)[0] for line in content.splitlines() if '=' in line and not line.startswith('#')}
    additions=[]
    for line in (root/directory/'.env.example').read_text().splitlines():
        if '=' not in line or line.startswith('#'):continue
        key,value=line.split('=',1)
        if key in existing:continue
        if key=='DJANGO_SECRET_KEY':value=secrets.token_urlsafe(60)
        if key=='FIELD_ENCRYPTION_KEY':value=base64.urlsafe_b64encode(os.urandom(32)).decode()
        additions.append(key+'='+value)
    if additions:
        target.write_text(content.rstrip()+'\n'+'\n'.join(additions)+'\n');target.chmod(0o600)
    print(f'{directory}/.env ready; added {len(additions)} missing settings. Existing values preserved.')
