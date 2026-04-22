#!/usr/bin/env bash
set -o errexit

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "📁 Collecting static files..."
python manage.py collectstatic --no-input

echo "🗄️ Running migrations..."
python manage.py makemigrations vertext_app --no-input
python manage.py migrate --no-input

echo "👑 Creating admin user..."
python manage.py shell -c "
from vertext_app.models import User
try:
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
    print('✅ Admin ready: samson / 41516512#Sam')
except Exception as e:
    print('Admin error:', e)
try:
    d, _ = User.objects.get_or_create(username='demo')
    d.email = 'demo@vertext.app'
    d.is_monetized = True
    d.bio = 'Demo Creator'
    d.set_password('demo1234')
    d.save()
    print('✅ Demo ready: demo / demo1234')
except Exception as e:
    print('Demo error:', e)
"
echo "✅ Build complete!"
