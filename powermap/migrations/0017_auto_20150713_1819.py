# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('powermap', '0016_auto_20150713_1543'),
    ]

    operations = [
        migrations.AlterField(
            model_name='diagnostic',
            name='timestamp',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
