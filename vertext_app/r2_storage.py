"""
Cloudflare R2 Storage helper — uploads files to R2 and returns public CDN URLs.
Uses boto3 (S3-compatible API) to talk to Cloudflare R2.
Supabase is only used for the database — all media is served from R2.
"""
import os
import uuid
import mimetypes
import boto3
from botocore.config import Config

R2_ACCOUNT_ID     = os.environ.get('R2_ACCOUNT_ID', '')
R2_ACCESS_KEY_ID  = os.environ.get('R2_ACCESS_KEY_ID', '')
R2_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY', '')
R2_BUCKET_NAME    = os.environ.get('R2_BUCKET_NAME', 'vertextdigital')
R2_S3_ENDPOINT    = os.environ.get('R2_S3_ENDPOINT', f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com')
R2_PUBLIC_URL     = os.environ.get('R2_PUBLIC_URL', f'https://pub-{R2_ACCOUNT_ID}.r2.dev')


def _client():
    return boto3.client(
        's3',
        endpoint_url=R2_S3_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4'),
        region_name='auto',
    )


def upload_file(file_obj, folder: str = 'uploads') -> str:
    """Upload file to R2. Returns public CDN URL."""
    client = _client()
    name = getattr(file_obj, 'name', 'file')
    ext = os.path.splitext(name)[1] or ''
    filename = f"{folder}/{uuid.uuid4()}{ext}"
    content_type = (
        getattr(file_obj, 'content_type', None) or
        mimetypes.guess_type(filename)[0] or
        'application/octet-stream'
    )
    data = file_obj.read()
    client.put_object(
        Bucket=R2_BUCKET_NAME,
        Key=filename,
        Body=data,
        ContentType=content_type,
    )
    return f"{R2_PUBLIC_URL}/{filename}"


def upload_video(f) -> str:
    return upload_file(f, 'videos')


def upload_thumbnail(f) -> str:
    return upload_file(f, 'thumbnails')


def upload_avatar(f) -> str:
    return upload_file(f, 'avatars')


def delete_file(url: str) -> bool:
    """Delete file from R2 given its public URL."""
    try:
        if R2_PUBLIC_URL not in url:
            return False
        key = url.replace(f"{R2_PUBLIC_URL}/", '')
        _client().delete_object(Bucket=R2_BUCKET_NAME, Key=key)
        return True
    except Exception as e:
        print(f'R2 delete error: {e}')
        return False


def ensure_bucket():
    """Make sure the bucket exists and is public."""
    try:
        client = _client()
        client.head_bucket(Bucket=R2_BUCKET_NAME)
        print(f'  ✓  R2 bucket exists: {R2_BUCKET_NAME}')
    except Exception as e:
        print(f'  ⚠️  R2 bucket check: {e}')
