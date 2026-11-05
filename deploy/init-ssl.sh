#!/bin/sh
# First-time HTTPS setup. Run once on the server, after DNS of $DOMAIN points
# to it and ports 80/443 are open.  Usage: ./deploy/init-ssl.sh [--staging]
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PROD="$ROOT/deploy/prod.sh"

getenv() { grep -E "^$1=" "$ROOT/.env" | tail -1 | cut -d= -f2- | tr -d '"\r'; }
DOMAIN=$(getenv DOMAIN)
LETSENCRYPT_EMAIL=$(getenv LETSENCRYPT_EMAIL)
: "${DOMAIN:?DOMAIN خالی است؛ آن را در فایل .env بنویسید}"
: "${LETSENCRYPT_EMAIL:?LETSENCRYPT_EMAIL خالی است؛ آن را در فایل .env بنویسید}"
STAGING=""
[ "${1:-}" = "--staging" ] && STAGING="--staging"

LIVE="/etc/letsencrypt/live/$DOMAIN"

echo "1/4 گواهی موقت تا nginx بتواند بالا بیاید..."
"$PROD" run --rm --entrypoint sh certbot -c "
  if [ ! -f $LIVE/fullchain.pem ]; then
    mkdir -p $LIVE &&
    openssl req -x509 -nodes -newkey rsa:2048 -days 1 -subj /CN=$DOMAIN \
      -keyout $LIVE/privkey.pem -out $LIVE/fullchain.pem && touch $LIVE/.dummy
  fi"

echo "2/4 اجرای nginx..."
"$PROD" up -d --build nginx

echo "3/4 گرفتن گواهی Let's Encrypt برای $DOMAIN ..."
"$PROD" run --rm --entrypoint sh certbot -c "
  if [ -f $LIVE/.dummy ]; then rm -rf $LIVE /etc/letsencrypt/archive/$DOMAIN /etc/letsencrypt/renewal/$DOMAIN.conf; fi &&
  certbot certonly --webroot -w /var/www/certbot $STAGING -d $DOMAIN \
    --email $LETSENCRYPT_EMAIL --agree-tos --no-eff-email --non-interactive"

echo "4/4 بارگذاری دوباره‌ی nginx..."
"$PROD" exec nginx nginx -s reload
echo "تمام شد: https://$DOMAIN/health/"
