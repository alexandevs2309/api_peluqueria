"""
Rotate all local secrets in .env and .env.prod.
Third-party keys (Stripe, PayPal, SendGrid, Cloudinary) must be rotated
manually in their respective dashboards.
"""
import os
import re
import secrets
import string


def random_key(length=50):
    chars = string.ascii_letters + string.digits + '!@#%^&*(-_=+)'
    return ''.join(secrets.choice(chars) for _ in range(length))


def random_password(length=25):
    return secrets.token_urlsafe(length).rstrip('-_')


def update_env_file(filepath, updates):
    if not os.path.exists(filepath):
        print(f"SKIP: {filepath} not found")
        return

    with open(filepath, 'r') as f:
        content = f.read()

    for key, value in updates.items():
        pattern = re.compile(rf'^{re.escape(key)}=.*', re.MULTILINE)
        if pattern.search(content):
            content = pattern.sub(f'{key}={value}', content)
            print(f"  UPDATED {key}")
        else:
            print(f"  SKIP {key} (not found in file)")

    with open(filepath, 'w') as f:
        f.write(content)


new_secrets = {
    'SECRET_KEY': random_key(50),
    'DB_PASSWORD': random_password(25),
    'REDIS_PASSWORD': random_password(25),
    'JWT_SIGNING_KEY': random_key(50),
    'SUPERADMIN_PASSWORD': random_password(30),
    'GRAFANA_PASSWORD': random_password(16),
}

# Update REDIS_URL and CELERY URLs with new password
redis_pass = new_secrets['REDIS_PASSWORD']
new_secrets['REDIS_URL'] = f'redis://:{redis_pass}@redis:6379/0'
new_secrets['CELERY_BROKER_URL'] = f'redis://:{redis_pass}@redis:6379/0'
new_secrets['CELERY_RESULT_BACKEND'] = f'redis://:{redis_pass}@redis:6379/0'

print("=== Rotating .env ===")
update_env_file('.env', new_secrets)

print("\n=== Rotating .env.prod ===")
update_env_file('.env.prod', new_secrets)

print("\n=== Generated Values (save these) ===")
for k, v in new_secrets.items():
    if k in ('REDIS_URL', 'CELERY_BROKER_URL', 'CELERY_RESULT_BACKEND'):
        continue
    print(f"  {k}={v}")
