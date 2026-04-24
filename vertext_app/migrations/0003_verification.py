from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vertext_app', '0002_adlink_thumbnail_url'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE vertext_user ADD COLUMN IF NOT EXISTS verification_type varchar(10) NOT NULL DEFAULT 'none';",
            reverse_sql="ALTER TABLE vertext_user DROP COLUMN IF EXISTS verification_type;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS vertext_app_verificationrequest (
                id bigserial PRIMARY KEY,
                reason text NOT NULL,
                status varchar(20) NOT NULL DEFAULT 'pending',
                created_at timestamp with time zone NOT NULL DEFAULT now(),
                reviewed_at timestamp with time zone NULL,
                user_id bigint NOT NULL REFERENCES vertext_user(id) ON DELETE CASCADE
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS vertext_app_verificationrequest;",
        ),
    ]
