# -*- coding: utf-8 -*-
# Generated by Django 1.11.27 on 2020-01-24 19:04
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dhis2', '0007_populate_sqldhis2connection'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='SQLDhis2Connection',
            new_name='Dhis2Connection',
        ),
    ]
