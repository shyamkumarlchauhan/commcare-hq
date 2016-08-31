from optparse import make_option
from django.core.management.base import BaseCommand

from corehq.apps.export.utils import migrate_domain
from corehq.apps.domain.models import Domain
from corehq.form_processor.utils.general import use_new_exports
from dimagi.utils.django.email import send_HTML_email


class Command(BaseCommand):
    help = "Migrates old exports to new ones"

    option_list = BaseCommand.option_list + (
        make_option(
            '--dry-run',
            action='store_true',
            dest='dryrun',
            default=False,
            help='Runs a dry run on the export conversations'
        ),
        make_option(
            '--limit',
            dest='limit',
            default=None,
            type='int',
            help='Limits the number of domains migrated'
        ),
    )

    def handle(self, *args, **options):
        dryrun = options.pop('dryrun')
        limit = options.pop('limit')
        count = 0

        if dryrun:
            print '*** Running in dryrun mode. Will not save any conversion ***'

        print '*** Migrating {} exports ***'.format(limit or 'ALL')
        skipped_domains = []

        for doc in Domain.get_all(include_docs=False):
            domain = doc['key']

            if not use_new_exports(domain):
                metas = migrate_domain(domain, True)

                has_skipped_tables = any(map(lambda meta: bool(meta.skipped_tables), metas))
                has_skipped_columns = any(map(lambda meta: bool(meta.skipped_columns), metas))
                if has_skipped_tables or has_skipped_columns:
                    print 'Skipping {} because we would have skipped columns'.format(domain)
                    skipped_domains.append(domain)
                    continue

                if not dryrun:
                    print 'Migrating {}'.format(domain)
                    migrate_domain(domain, False)
                else:
                    print 'No skipped tables/columns. Not migrating since dryrun is specified'
                count += 1
            if count >= limit:
                break

        send_HTML_email(
            'Export migration results',
            '{}@{}'.format('brudolph', 'dimagi.com'),

            '''
            Skipped domains: {} <br />
            Successfully migrated: {}
            '''.format(
                ', '.join(skipped_domains),
                count,
            )
        )
