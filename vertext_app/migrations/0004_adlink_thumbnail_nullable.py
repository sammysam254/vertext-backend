from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vertext_app', '0003_adlink_thumbnail'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE vertext_app_adlink ALTER COLUMN thumbnail DROP NOT NULL;",
            reverse_sql="ALTER TABLE vertext_app_adlink ALTER COLUMN thumbnail SET NOT NULL;",
        ),
    ]
