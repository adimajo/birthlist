# Deploying on TrueNAS SCALE (24.10 and later)

The app ships as one container (gunicorn + WhiteNoise, SQLite). TLS and the public hostname are handled by whatever
reverse proxy / tunnel you already use in front of it (it only speaks plain HTTP on port 8000).

## 1. Datasets
Create a dataset `apps/birthlist` and run `deploy.example.sh` (after copying it to `deploy.private.sh` and
adjusting it). You get:

| Path | Purpose |
|---|---|
| `…/birthlist/data` | SQLite database, owned by uid/gid 568. **Snapshot this dataset** for backups. |
| `…/birthlist/content` | Private overlay mounted read-only (see below). |
| `…/birthlist/birthlist.env` | All settings and secrets (`chmod 600`). See `.env.example` for every variable. |

## 2. Image
Either pull the image published by the GitHub workflow (set the repository variable `PUBLISH_IMAGE=true`; image is
`ghcr.io/<owner>/birthlist:<git-sha>`) or build it on a machine with Docker and push it to a registry you control:

```bash
docker build -t ghcr.io/<owner>/birthlist:$(git rev-parse HEAD) .
```

Always reference an immutable tag (the git sha) or digest in `compose.yaml`; roll back by switching to the previous tag.

## 3. Install the app
Apps -> Discover Apps -> **Install via YAML**, paste `compose.yaml` (adjust pool name and image tag). The container
runs migrations and collects static files on every start; `/healthz` is the healthcheck.

## 4. First steps
In the app's shell (Apps -> birthlist -> Shell, or `docker exec -it <container> sh`):

```bash
python manage.py createsuperuser           # then log in at /admin/
python manage.py import_guests /data/guests.csv --dry-run   # CSV: first name, last name, email (header row first)
python manage.py import_guests /data/guests.csv
python manage.py send_campaign announcement                 # dry run: lists who would get the e-mail
python manage.py send_campaign announcement --send --mark-sent
python manage.py purge_guests --older-than-days 180         # retention clean-up (never touches staff)
```

Add gifts in `/admin/`. `/dashboard/` (staff only) shows who has not opened their e-mail and can send test e-mails
to yourself.

## 5. Private overlay (`content/`)
Anything in `content/templates` takes precedence over the repository templates and `content/static` is added to the
static files. Typical files:

```
content/templates/partials/welcome.html                      # welcome text on the home page
content/templates/offrants/email_templates/announcement.html # e-mail wording
content/templates/offrants/email_templates/notice.html
content/static/bigday/images/hero.jpg                        # set HEADER_IMAGE / EMAIL_HERO_IMAGE accordingly
```

Keep this directory out of the public repository (it is git-ignored); versioning it in a separate private repository is
a good idea.

## 6. Migrating data from the old jail
A fresh database is the simplest option. If you want to keep the gifts, run `dumpdata birthlist.Cadeau` against the
old install and `loaddata` it here (guests re-import from CSV so everyone gets new personal links).
