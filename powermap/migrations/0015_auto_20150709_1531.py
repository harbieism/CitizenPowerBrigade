# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('powermap', '0014_helpnote_phone_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='powercar',
            name='current_location_until',
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name='powercar',
            name='eta',
            field=models.DateTimeField(null=True),
        ),
    ]
