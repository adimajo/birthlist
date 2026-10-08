#!/bin/sh
# Copy to deploy.private.sh (git-ignored), fill in your values, run it on the TrueNAS shell.
# It prepares the datasets' directories and a private env file; it never leaves your server.
set -eu

POOL="tank"                         # your pool name
APP_DIR="/mnt/$POOL/apps/birthlist" # parent dataset (create it in the UI first: Datasets -> Add Dataset)

mkdir -p "$APP_DIR/data" "$APP_DIR/content/templates" "$APP_DIR/content/static"
chown -R 568:568 "$APP_DIR/data"    # 568 = "apps" user, the container user

if [ ! -f "$APP_DIR/birthlist.env" ]; then
  SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(60))')
  cat > "$APP_DIR/birthlist.env" <<ENV
SECRET_KEY=$SECRET
SITE_URL=https://birthlist.example.org
ALLOWED_HOSTS=birthlist.example.org
REGISTRATION_CODE=change-me
SITE_TITLE=Liste de naissance
COUPLE_NAMES=Alex et Sam
BABY_NAME=Bébé
EMAIL_HOST=smtp.example.org
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=
REPLY_TO_EMAIL=
CC_LIST=
ENV
  chmod 600 "$APP_DIR/birthlist.env"
  echo "Created $APP_DIR/birthlist.env -- edit it now."
fi
echo "Next: copy your private overlay (welcome text, e-mail templates, photos) into $APP_DIR/content/"
