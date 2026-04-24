from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vertext_app', '0007_platform_settings'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS django_cache (
                cache_key varchar(255) NOT NULL PRIMARY KEY,
                value text NOT NULL,
                expires bigint NOT NULL
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS django_cache;",
        ),
    ]
