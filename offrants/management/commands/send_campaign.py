from django.core.management import BaseCommand, CommandError

from offrants.campaigns import CAMPAIGNS


class Command(BaseCommand):
    help = (
        "Send an e-mail campaign to the guests who have not received it yet. Without --send nothing is sent (dry run)."
    )

    def add_arguments(self, parser):
        parser.add_argument("campaign", choices=sorted(CAMPAIGNS), help="announcement (annonce) or notice (faire-part)")
        parser.add_argument("--send", action="store_true", help="Actually send the e-mails")
        parser.add_argument("--mark-sent", action="store_true", help="Remember who received it (requires --send)")
        parser.add_argument("--reset", action="store_true", help="Forget who already received this campaign")
        parser.add_argument("--delay", type=float, default=1.0, help="Seconds to wait between e-mails")

    def handle(self, *args, campaign, send, mark_sent, reset, delay, **options):
        if mark_sent and not send:
            raise CommandError("--mark-sent only makes sense together with --send")
        selected = CAMPAIGNS[campaign]
        if reset:
            self.stdout.write(f"Reset {selected.reset_sent()} guests")
        sent, failed = selected.send_all(send=send, mark_sent=mark_sent, delay=delay, stdout=self.stdout)
        if send:
            self.stdout.write(f"{sent} sent, {failed} failed")
        if failed:
            raise CommandError(f"{failed} e-mails could not be sent")
