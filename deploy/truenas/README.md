# Deploying on TrueNAS SCALE (25.04 and later, Docker apps)

Layout: a **Caddy** container terminates HTTPS on its own LAN address (macvlan), and the Django app (gunicorn +
SQLite) is only reachable from Caddy. Certificates come from Let's Encrypt with the TLS-ALPN-01 challenge, which only
needs **port 443** to be reachable from the internet (no port 80, no DNS API).

```
internet :443 -> router port forward -> LAN_IP:443 (Caddy) -> birthlist:8000 (Django)
```

## 1. Prerequisites
- A hostname pointing to your public IP (any DNS provider, including No-IP DDNS), and a router port forward
  `public:443 -> LAN_IP:443`. `LAN_IP` must be a free address outside the DHCP range.
- A dataset for the app, e.g. `POOL/Apps/birthlist` (the deploy script creates the sub-folders).
- SSH access as root to the NAS (key based).
- Two private, git-ignored files on your workstation:
  - `deploy/truenas/deploy.private.env`, copied from `deploy.env.example` (dataset path, host name, LAN IP, NIC name,
    subnet, gateway; `ACME_CA` for the Let's Encrypt staging CA while testing).
  - `prod.private.env`, copied from `.env.example` (all app settings and secrets).
- Optionally a `content/` directory next to the repository with your private overlay (see below).

## 2. Deploy / update
```bash
SSH_OPTS="-i ~/.ssh/my_key -o IdentitiesOnly=yes" deploy/truenas/deploy.sh root@nas
```
The script (needs a clean git tree) uploads the committed sources, your env files and the overlay, builds the image on
the NAS (tagged with the commit), renders `compose.yaml` and creates or updates the `birthlist` custom app via the
TrueNAS API. The container runs migrations and collects static files on every start; `/healthz` is the healthcheck.

Tip: set `ACME_CA=https://acme-staging-v02.api.letsencrypt.org/directory` for the first run to validate the whole path
(router forward, DNS) without hitting Let's Encrypt rate limits, then remove it and deploy again.

Notes
- With macvlan the NAS itself cannot reach `LAN_IP` (Docker limitation); other LAN machines can. Test from another device:
  `curl --resolve host:443:LAN_IP https://host/healthz`.
- Data lives in `<APP_DIR>/data` (SQLite, owned by uid 568): snapshot that dataset for backups. Caddy keeps its
  certificates in `<APP_DIR>/caddy`.

## 3. First steps
```bash
docker exec -it ix-birthlist-birthlist-1 python manage.py createsuperuser       # then log in at /admin/
docker cp guests.csv ...   # or place guests.csv in <APP_DIR>/data (chown 568:568), then:
docker exec ix-birthlist-birthlist-1 python manage.py import_guests /data/guests.csv --dry-run
docker exec ix-birthlist-birthlist-1 python manage.py import_guests /data/guests.csv
docker exec ix-birthlist-birthlist-1 python manage.py send_campaign announcement                 # dry run
docker exec ix-birthlist-birthlist-1 python manage.py send_campaign announcement --send --mark-sent
docker exec ix-birthlist-birthlist-1 python manage.py purge_guests --older-than-days 180
```
Add gifts in `/admin/`. `/dashboard/` (staff only) shows who has not opened their e-mail and can send test e-mails to
yourself.

## 4. Private overlay (`content/`)
Anything in `content/templates` takes precedence over the repository templates and `content/static` is added to the
static files:

```
content/templates/partials/welcome.html                      # welcome text on the home page
content/templates/offrants/email_templates/announcement.html # e-mail wording
content/templates/offrants/email_templates/notice.html
content/static/bigday/images/hero.jpg                        # set HEADER_IMAGE / EMAIL_HERO_IMAGE accordingly
```
The directory is git-ignored; versioning it in a separate private repository is a good idea.

## 5. Keeping a dynamic IP up to date
If your ISP can change your public IP, make your router (or a cron job on the NAS) update the DNS record; the app
itself does not depend on the IP.
