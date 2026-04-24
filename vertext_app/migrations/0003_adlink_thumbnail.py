from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vertext_app', '0002_adlink_thumbnail_url'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE vertext_app_adlink ADD COLUMN IF NOT EXISTS thumbnail varchar(500) DEFAULT '' NOT NULL;",
            reverse_sql="ALTER TABLE vertext_app_adlink DROP COLUMN IF EXISTS thumbnail;",
        ),
    ]
