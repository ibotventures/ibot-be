# Generated by Django 5.1.2 on 2025-01-07 10:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lmsappv1', '0009_user_inactive'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='course_cover_image',
            field=models.ImageField(blank=True, null=True, upload_to='course/'),
        ),
        migrations.AlterField(
            model_name='module',
            name='activity',
            field=models.FileField(blank=True, null=True, upload_to='activity/'),
        ),
        migrations.AlterField(
            model_name='module',
            name='content',
            field=models.FileField(blank=True, null=True, upload_to='content/'),
        ),
        migrations.AlterField(
            model_name='module',
            name='intro',
            field=models.FileField(blank=True, null=True, upload_to='intro/'),
        ),
    ]
