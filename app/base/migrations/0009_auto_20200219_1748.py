# Generated by Django 2.2.9 on 2020-02-19 16:48

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0008_remove_class_collectionid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='imageannotation',
            name='userid',
            field=models.ForeignKey(db_column='userid', on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL, null=True),
        ),
    ]