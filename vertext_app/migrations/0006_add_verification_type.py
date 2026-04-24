from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('vertext_app', '0005_merge'),
    ]
    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE vertext_user ADD COLUMN IF NOT EXISTS verification_type varchar(20) NOT NULL DEFAULT 'none';",
            reverse_sql="ALTER TABLE vertext_user DROP COLUMN IF EXISTS verification_type;",
        ),
    ]
