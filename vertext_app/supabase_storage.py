"""
Supabase Storage helper — uploads files to Supabase and returns public URLs.
Videos and images are stored permanently in Supabase Storage buckets.
"""
import os
import uuid
import mimetypes
from storage3 import create_client

SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://mzicoxnygbpmyhntcfsm.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_ANON_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im16aWNveG55Z2JwbXlobnRjZnNtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY4MDY3MDcsImV4cCI6MjA5MjM4MjcwN30.eu8jeQOxsz2SzL2wnguY0jeKOXh1ybNnlBgr19Xv-KY')
SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', SUPABASE_KEY)

VIDEO_BUCKET = 'videos'
AVATAR_BUCKET = 'avatars'
THUMB_BUCKET = 'thumbnails'

def get_storage_client():
    headers = {'apiKey': SERVICE_KEY, 'Authorization': f'Bearer {SERVICE_KEY}'}
    return create_client(f'{SUPABASE_URL}/storage/v1', headers, is_async=False)

def upload_file(file_obj, bucket: str, folder: str = '') -> str:
    """Upload a file to Supabase Storage. Returns public URL."""
    client = get_storage_client()
    ext = ''
    if hasattr(file_obj, 'name'):
        ext = os.path.splitext(file_obj.name)[1] or ''
    filename = f"{folder}/{uuid.uuid4()}{ext}".lstrip('/')
    content_type = getattr(file_obj, 'content_type', None) or mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    file_bytes = file_obj.read()
    client.from_(bucket).upload(
        path=filename,
        file=file_bytes,
        file_options={'content-type': content_type, 'upsert': 'true'},
    )
    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{filename}"
    return public_url

def upload_video(file_obj) -> str:
    return upload_file(file_obj, VIDEO_BUCKET, 'uploads')

def upload_thumbnail(file_obj) -> str:
    return upload_file(file_obj, THUMB_BUCKET, 'uploads')

def upload_avatar(file_obj) -> str:
    return upload_file(file_obj, AVATAR_BUCKET, 'uploads')

def ensure_buckets():
    """Create buckets if they don't exist (call once on startup)."""
    client = get_storage_client()
    for bucket in [VIDEO_BUCKET, AVATAR_BUCKET, THUMB_BUCKET]:
        try:
            client.create_bucket(bucket, options={'public': True})
            print(f'✅ Created bucket: {bucket}')
        except Exception as e:
            if 'already exists' in str(e).lower() or 'Duplicate' in str(e):
                print(f'✓ Bucket exists: {bucket}')
            else:
                print(f'⚠ Bucket {bucket}: {e}')
