# birthlist

A small, self-hosted Django site to share a **birth gift list** with family and friends.

- Guests log in with a **personal link** received by e-mail (or create an account with a shared access code).
- They see the list, say they are *interested* in a gift (to team up with others) and mark it as *bought* (to avoid duplicates).
- The couple manage gifts and guests in the Django admin, import guests from a CSV and send two e-mail campaigns
  (an *announcement* and a *birth notice*) with per-guest links; a staff-only dashboard shows who opened them.
- Container image + TrueNAS SCALE instructions included. Everything personal (names, texts, photos, SMTP
  credentials) lives in environment variables and a private overlay directory, never in the repository.

The project started as a fork of [django-wedding-website](https://github.com/czue/django-wedding-website) by Cory Zue
(Apache-2.0); see `NOTICE`.

## Quick start (development)

```bash
cp .env.example .env            # set DEBUG=true and EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Tests and checks:

```bash
uv run python manage.py test
uv run ruff check . && uv run ruff format --check .
```

## Configuration

All settings are environment variables (a `.env` file at the project root is loaded automatically, without overriding
real environment variables); `.env.example` lists them with comments. The important ones:

| Variable | Meaning |
|---|---|
| `SECRET_KEY` | Required when `DEBUG` is off |
| `SITE_URL`, `ALLOWED_HOSTS` | Public URL / host names (used for links in e-mails, CSRF and secure cookies) |
| `REGISTRATION_CODE` | Phrase guests must enter to self-register; empty disables `/register/` |
| `COUPLE_NAMES`, `BABY_NAME`, `SITE_TITLE`, `GIFT_POT_URL`, `POSTAL_ADDRESS` | Shown in the default texts |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL`, `REPLY_TO_EMAIL`, `CC_LIST` | SMTP and campaign headers |
| `DB_PATH` | SQLite file location |
| `SITE_CONTENT_DIR` | Private overlay with `templates/` and `static/` that override the defaults |

### Private overlay
Put your own `partials/welcome.html`, `offrants/email_templates/announcement.html` / `notice.html` and images in
`SITE_CONTENT_DIR` (default `./content`, git-ignored). Reference images with `HEADER_IMAGE` (web page header) and
`EMAIL_HERO_IMAGE` (embedded in e-mails).

## Operating

| Task | Command |
|---|---|
| Import guests (CSV: first name, last name, email) | `manage.py import_guests guests.csv [--dry-run]` |
| Export guests | `manage.py export_guests > guests.csv` |
| Send a campaign | `manage.py send_campaign announcement\|notice [--send] [--mark-sent] [--reset] [--delay S]` (dry run unless `--send`) |
| Delete old guests (retention) | `manage.py purge_guests --older-than-days 180` |
| Delete all guests | `manage.py wipe_guest_list` |

Staff-only pages: `/admin/` and `/dashboard/`. Password (re)set goes through an e-mailed link at `/password/reset/`.

## Security notes
- Personal links contain a secret token and log the guest in: tell guests not to forward the e-mail.
- Guests who join see the other interested guests' names and e-mail addresses (that is how they coordinate); only share the
  registration code with people you trust and purge old data.
- The guest list cannot be exported through the web interface, only via the admin or `manage.py`.
- Run behind HTTPS; the container trusts `X-Forwarded-Proto` from your proxy.

## Deployment
See [`deploy/truenas/README.md`](deploy/truenas/README.md) (TrueNAS SCALE 25.04+: Caddy with automatic HTTPS in front of the app, deployed with `deploy/truenas/deploy.sh`) and `compose.yaml`.
Dependencies are locked with [uv](https://docs.astral.sh/uv/) (`uv.lock`); the image is built with `uv sync --locked`
from digest-pinned base images, and Dependabot proposes updates through CI-checked pull requests.

## License
Apache License 2.0, see `LICENSE` and `NOTICE`.
