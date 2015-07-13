# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('powermap', '0015_auto_20150709_1531'),
    ]

    operations = [
        migrations.AlterField(
            model_name='powercar',
            name='current_location_until',
            field=models.DateTimeField(default=datetime.datetime(2015, 7, 13, 15, 43, 36, 473293, tzinfo=utc), auto_now_add=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='powercar',
            name='eta',
            field=models.DateTimeField(default=datetime.datetime(2015, 7, 13, 15, 43, 40, 789210, tzinfo=utc), auto_now_add=True),
            preserve_default=False,
        ),
    ]
