
# Build the React frontend
FROM node:24-slim AS frontend-build
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
# Optional public testing-token override; must match the backend runtime token.
ARG REACT_APP_BOOTSTRAP_ADMIN_TOKEN
RUN npm run build

# Install and run Django
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/ /app/backend/
COPY scripts/ /app/scripts/
COPY specification/ /app/specification/
COPY --from=frontend-build /app/frontend/build /app/frontend/build

WORKDIR /app/backend

# Generate temporary settings for collecting static files.
# These are NOT production secrets.


RUN DJANGO_SECRET_KEY="temporary-build-only-secret-key-0123456789-abcdefghijklmnopqrstuvwxyz-0123456789" \
    FIELD_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
    DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1" \
    DJANGO_CSRF_TRUSTED_ORIGINS="http://localhost" \
    python manage.py collectstatic --noinput

EXPOSE 10000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed && waitress-serve --listen=0.0.0.0:${PORT:-10000} config.wsgi:application"]
