from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vertext_app', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE vertext_app_adlink ADD COLUMN IF NOT EXISTS thumbnail_url varchar(500) NOT NULL DEFAULT '';",
            reverse_sql="ALTER TABLE vertext_app_adlink DROP COLUMN IF EXISTS thumbnail_url;",
        ),
    ]
