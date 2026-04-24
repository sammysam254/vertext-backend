#!/usr/bin/env bash
set -o errexit

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Vertext Backend Build"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "🔍 Checking environment..."
python -c "
import os
db = os.environ.get('SUPABASE_DB_URL') or os.environ.get('DATABASE_URL') or ''
if db:
    # Mask password for logging
    parts = db.split('@')
    safe = parts[0].split(':')[0] + ':***@' + parts[1] if len(parts) > 1 else '***'
    print(f'  ✅ DB URL found: {safe}')
else:
    print('  ⚠️  No DB URL — will use SQLite')
print(f'  SUPABASE_URL: {os.environ.get(\"SUPABASE_URL\", \"not set\")}')
print(f'  SERVICE_KEY: {\"set\" if os.environ.get(\"SUPABASE_SERVICE_KEY\") else \"not set\"}')
"

echo ""
echo "📁 Collecting static files..."
python manage.py collectstatic --no-input

echo ""
echo "🗄️ Running migrations..."
python manage.py makemigrations vertext_app --no-input
python manage.py migrate --fake-initial --no-input

echo ""
echo "🪣 Creating Supabase storage buckets..."
python manage.py shell -c "
try:
    from vertext_app.supabase_storage import ensure_buckets
    ensure_buckets()
except Exception as e:
    print(f'Storage setup skipped: {e}')
"

echo ""
echo "👑 Setting up admin user..."
python manage.py shell -c "
from vertext_app.models import User
try:
    # Clean up any conflicting records
    User.objects.filter(email='sammyseth260@gmail.com').exclude(username='samson').delete()
    u, created = User.objects.get_or_create(username='samson')
    u.email = 'sammyseth260@gmail.com'
    u.is_staff = True
    u.is_superuser = True
    u.is_monetized = True
    u.is_verified = True
    u.is_active = True
    u.bio = 'Vertext Founder 👑'
    u.set_password('41516512#Sam')
    u.save()
    print(f'  ✅ Admin: samson / 41516512#Sam ({'created' if created else 'updated'})')
except Exception as e:
    print(f'  ❌ Admin error: {e}')

try:
    d, dc = User.objects.get_or_create(username='demo')
    d.email = 'demo@vertext.app'
    d.is_monetized = True
    d.bio = 'Demo Creator ✨'
    d.set_password('demo1234')
    d.save()
    print(f'  ✅ Demo: demo / demo1234')
except Exception as e:
    print(f'  ❌ Demo error: {e}')

# Create default Ad Link so earnings work immediately
from vertext_app.models import AdLink
if not AdLink.objects.filter(is_active=True).exists():
    AdLink.objects.create(
        title='Vertext Feed Ad',
        platform='monetag',
        revenue_per_view=0.000100,
        is_active=True,
        show_frequency=7,
    )
    print('  ✅ Default ad link created (KES 0.013 per 1000 views)')
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Build complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
