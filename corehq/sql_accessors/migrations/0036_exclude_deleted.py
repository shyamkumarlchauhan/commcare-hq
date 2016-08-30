# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from corehq.sql_db.operations import RawSQLMigration
from corehq.form_processor.models import XFormInstanceSQL

migrator = RawSQLMigration(('corehq', 'sql_accessors', 'sql_templates'), {})


class Migration(migrations.Migration):

    dependencies = [
        ('sql_accessors', '0035_add_undelete_functions'),
    ]

    operations = [
        migrator.get_migration('get_case_by_location_id_1.sql'),
    ]
