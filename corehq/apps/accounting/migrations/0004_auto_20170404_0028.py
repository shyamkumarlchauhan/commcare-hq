# Generated by Django 1.10.6 on 2017-04-04 00:28

from django.db import migrations

from corehq.apps.hqadmin.management.commands.cchq_prbac_bootstrap import cchq_prbac_bootstrap



class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0003_auto_20170328_2102'),
    ]

    operations = [
        migrations.RunPython(cchq_prbac_bootstrap),
    ]
