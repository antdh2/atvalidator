# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-08-19 22:35
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('autotask_web_app', '0030_company_password'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='picklist',
            name='profile',
        ),
        migrations.AddField(
            model_name='picklist',
            name='company',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='autotask_web_app.Company'),
            preserve_default=False,
        ),
    ]
