# Generated by Django 1.11.21 on 2019-07-23 16:43

from django.core.management import call_command
from django.db import migrations

from corehq.privileges import (
    CASE_SHARING_GROUPS,
    CHILD_CASES,
)
from corehq.util.django_migrations import skip_on_fresh_install


@skip_on_fresh_install
def _grandfather_case_privs(apps, schema_editor):
    call_command('cchq_prbac_bootstrap')
    call_command(
        'cchq_prbac_grandfather_privs',
        CASE_SHARING_GROUPS,
        CHILD_CASES,
        noinput=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0042_domain_user_history__unique__and__nonnullable'),
    ]

    operations = [
        migrations.RunPython(_grandfather_case_privs),
    ]
