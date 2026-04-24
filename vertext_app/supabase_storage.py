"""
Supabase Storage helper — uploads files and returns permanent public URLs.
Uses the storage3 Python client with the service role key.
"""
import os
import uuid
import mimetypes

SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://mzicoxnygbpmyhntcfsm.supabase.co')
SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY') or os.environ.get('SUPABASE_ANON_KEY', '')

VIDEO_BUCKET = 'videos'
AVATAR_BUCKET = 'avatars'
THUMB_BUCKET = 'thumbnails'


def _client():
    from storage3 import create_client
    headers = {
        'apiKey': SERVICE_KEY,
        'Authorization': f'Bearer {SERVICE_KEY}',
    }
    return create_client(f'{SUPABASE_URL}/storage/v1', headers, is_async=False)


def upload_file(file_obj, bucket: str, folder: str = '') -> str:
    """Upload file to Supabase Storage bucket. Returns public URL."""
    client = _client()
    name = getattr(file_obj, 'name', 'file')
    ext = os.path.splitext(name)[1] or ''
    filename = f"{folder}/{uuid.uuid4()}{ext}".lstrip('/')
    content_type = (
        getattr(file_obj, 'content_type', None) or
        mimetypes.guess_type(filename)[0] or
        'application/octet-stream'
    )
    data = file_obj.read()
    client.from_(bucket).upload(
        path=filename,
        file=data,
        file_options={'content-type': content_type, 'upsert': 'true'},
    )
    return f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{filename}"


def upload_video(f) -> str:
    return upload_file(f, VIDEO_BUCKET, 'uploads')


def upload_thumbnail(f) -> str:
    return upload_file(f, THUMB_BUCKET, 'uploads')


def upload_avatar(f) -> str:
    return upload_file(f, AVATAR_BUCKET, 'uploads')


def ensure_buckets():
    """Create public buckets if they don't exist."""
    client = _client()
    for bucket in [VIDEO_BUCKET, AVATAR_BUCKET, THUMB_BUCKET]:
        try:
            client.create_bucket(bucket, options={'public': True})
            print(f'  ✅ Created bucket: {bucket}')
        except Exception as e:
            msg = str(e).lower()
            if 'already exists' in msg or 'duplicate' in msg or '409' in msg:
                print(f'  ✓  Bucket exists: {bucket}')
            else:
                print(f'  ⚠️  Bucket {bucket}: {e}')
