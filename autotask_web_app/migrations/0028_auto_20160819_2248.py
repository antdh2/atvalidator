# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-08-19 21:48
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('autotask_web_app', '0027_auto_20160819_2245'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='company_id',
            field=models.CharField(max_length=254),
        ),
    ]
