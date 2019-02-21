# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2019-01-05 00:21
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import print_function

import sys
import traceback

from django.core.management import call_command
from django.db import migrations

from corehq.sql_db.operations import HqRunPython


BLOBMETAS_NOT_MIGRATED_ERROR = """
Blob metadata needs to be migrated before this environment can be upgraded to
the latest version of CommCareHQ. Instructions for running the migration can be
found at this link:

https://github.com/dimagi/commcare-cloud/blob/master/docs/changelog/0009-blob-metadata-part-2.md

If you are unable to run the management command because it has been deleted,
you will need to checkout an older version of CommCareHQ first:

git checkout acc40116a96a40c64efb8613fb2ba5933122b151
"""


def get_num_attachments(connection):
    """Get the number of attachments that need to be migrated"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM form_processor_xformattachmentsql")
        return cursor.fetchone()[0]


def _assert_blobmetas_migrated(apps, schema_editor):
    """Check if migrated. Raises SystemExit if not migrated"""
    num_attachments = get_num_attachments(schema_editor.connection)

    migrated = num_attachments == 0
    if migrated:
        return

    if num_attachments < 10000:
        try:
            call_command(
                "run_sql",
                "simple_move_form_attachments_to_blobmeta",
                dbname=schema_editor.connection.alias,
            )
            migrated = get_num_attachments(schema_editor.connection) == 0
            if not migrated:
                print("Automatic migration failed")
                migrated = False
        except Exception:
            traceback.print_exc()
    else:
        print("Found %s attachments." % num_attachments)
        print("Too many to migrate automatically.")

    if not migrated:
        print("")
        print(BLOBMETAS_NOT_MIGRATED_ERROR)
        sys.exit(1)


class Migration(migrations.Migration):

    dependencies = [
        ('form_processor', '0077_null_properties'),
    ]

    operations = [
        HqRunPython(_assert_blobmetas_migrated, migrations.RunPython.noop)
    ]
