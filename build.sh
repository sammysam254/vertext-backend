#!/usr/bin/env bash
set -o errexit

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "📁 Collecting static files..."
python manage.py collectstatic --no-input

echo "🗄️ Running migrations..."
python manage.py makemigrations vertext_app --no-input
python manage.py migrate --no-input

echo "🪣 Creating Supabase storage buckets..."
python manage.py shell -c "
from vertext_app.supabase_storage import ensure_buckets
ensure_buckets()
"

echo "👑 Creating admin user..."
python manage.py shell -c "
from vertext_app.models import User
try:
    # Remove any user with same email but different username
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
    print('✅ Admin:', u.username, '/', '41516512#Sam', '(', 'new' if created else 'updated', ')')
except Exception as e:
    print('❌ Admin error:', e)
"
echo "✅ Build complete!"
