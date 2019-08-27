# flake8: noqa
# Generated by Django 1.11.20 on 2019-02-25 19:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aaa', '0005_auto_20190225_1822'),
    ]

    operations = [
        migrations.AddField(
            model_name='ccsrecord',
            name='preg_reg_date',
            field=models.DateField(null=True),
        ),
        migrations.AddField(
            model_name='ccsrecord',
            name='woman_weight_at_preg_reg',
            field=models.DecimalField(decimal_places=2, max_digits=6, null=True),
        ),
        migrations.AddField(
            model_name='woman',
            name='blood_group',
            field=models.TextField(null=True),
        ),
    ]
