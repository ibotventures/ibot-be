# Generated by Django 5.1.2 on 2025-01-02 09:39

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lmsappv1', '0005_alter_cartdata_transact'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartdata',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='cartdata',
            name='updated_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
