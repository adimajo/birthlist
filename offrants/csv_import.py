import csv
import io
import logging

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from offrants.models import Offrant

logger = logging.getLogger(__name__)

HEADERS = ["first_name", "last_name", "email"]


def import_guests(path, dry_run=False):
    """Import guests from a CSV file with the columns ``first name, last name, email`` (header row first).

    Extra columns are ignored. Guests are matched on their e-mail address (case-insensitive), so running the
    import again updates names instead of creating duplicates. Rows without a valid e-mail are skipped.
    Returns ``(created, updated, skipped)``.
    """
    created = updated = skipped = 0
    with open(path, newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)  # header
        for line_number, row in enumerate(reader, start=2):
            if not any(cell.strip() for cell in row):
                continue
            if len(row) < 3:
                logger.warning("Line %d skipped: expected 3 columns, got %d", line_number, len(row))
                skipped += 1
                continue
            first_name, last_name, email = (cell.strip() for cell in row[:3])
            email = Offrant.objects.normalize_email(email)
            try:
                validate_email(email)
            except ValidationError:
                logger.warning("Line %d skipped: invalid or missing e-mail %r", line_number, email)
                skipped += 1
                continue
            existing = Offrant.objects.filter(email__iexact=email).first()
            if existing is None:
                created += 1
                if not dry_run:
                    Offrant.objects.create_user(first_name=first_name, last_name=last_name, email=email)
            else:
                updated += 1
                if not dry_run and (existing.first_name, existing.last_name) != (first_name, last_name):
                    existing.first_name, existing.last_name = first_name, last_name
                    existing.save(update_fields=["first_name", "last_name"])
    return created, updated, skipped


def export_guests():
    file = io.StringIO()
    writer = csv.writer(file)
    writer.writerow(HEADERS)
    for offrant in Offrant.objects.all():
        writer.writerow([offrant.first_name, offrant.last_name, offrant.email])
    return file
