from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vertext_app', '0006_add_verification_type'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS vertext_app_platformsettings (
                id bigserial PRIMARY KEY,
                verification_open boolean NOT NULL DEFAULT false,
                monetization_open boolean NOT NULL DEFAULT true,
                registration_open boolean NOT NULL DEFAULT true
            );
            INSERT INTO vertext_app_platformsettings (id, verification_open, monetization_open, registration_open)
            VALUES (1, false, true, true)
            ON CONFLICT (id) DO NOTHING;
            """,
            reverse_sql="DROP TABLE IF EXISTS vertext_app_platformsettings;",
        ),
    ]
