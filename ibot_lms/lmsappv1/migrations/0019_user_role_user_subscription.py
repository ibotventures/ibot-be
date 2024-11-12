# Generated by Django 5.1.1 on 2024-10-29 10:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lmsappv1', '0018_user_username'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('purchasedUser', 'purchasedUser'), ('CourseSubscribedUser', 'CourseSubscribedUser'), ('admin', 'admin'), ('visitor', 'visitor')], default='visitor', max_length=50),
        ),
        migrations.AddField(
            model_name='user',
            name='subscription',
            field=models.BooleanField(default=False),
        ),
    ]