from django.contrib.auth import authenticate
from django.db.models import F
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (User, Video, Like, Comment, Save, Follow,
                     AdLink, AdView, Notification, VerificationRequest, WithdrawalRequest)
from .serializers import (UserPublicSerializer, UserPrivateSerializer,
                          RegisterSerializer, VideoSerializer, VideoUploadSerializer,
                          CommentSerializer, AdLinkSerializer, NotificationSerializer)

BLUE_BADGE_LIMIT = 50  # first N new users get blue badge


def get_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}


# ── Auth ──────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    s = RegisterSerializer(data=request.data)
    if not s.is_valid():
        return Response(s.errors, status=400)
    user = s.save()

    # Badge logic wrapped in try/except - column may not exist on first deploy
    can_claim = False
    try:
        existing_count = User.objects.filter(
            date_joined__lt=user.date_joined
        ).count()
        if existing_count == 0:
            User.objects.filter(pk__lt=user.pk).update(
                is_verified=True, verification_type='black'
            )
        new_users_after_launch = User.objects.filter(
            verification_type__in=['blue', 'none', ''],
            is_verified=False,
        ).count()
        if new_users_after_launch < BLUE_BADGE_LIMIT:
            user.verification_type = 'eligible_blue'
            can_claim = True
        else:
            user.verification_type = 'none'
        user.save(update_fields=['verification_type'])
    except Exception:
        pass

    tokens = get_tokens(user)
    return Response({
        'access': tokens['access'],
        'refresh': tokens['refresh'],
        'user': UserPrivateSerializer(user).data,
        'can_claim_blue': can_claim,
    }, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')
    user = authenticate(username=username, password=password)
    if not user:
        # try by email
        try:
            u = User.objects.get(email=username)
            user = authenticate(username=u.username, password=password)
        except User.DoesNotExist:
            pass
    if not user:
        return Response({'error': 'Invalid credentials'}, status=401)
    if user.is_suspended:
        return Response({'error': 'Account suspended'}, status=403)
    tokens = get_tokens(user)
    return Response({'access': tokens['access'], 'refresh': tokens['refresh'], 'user': UserPrivateSerializer(user).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def claim_blue_badge(request):
    user = request.user
    if user.verification_type != 'eligible_blue':
        return Response({'error': 'Not eligible for blue badge'}, status=400)
    user.is_verified = True
    user.verification_type = 'blue'
    user.save(update_fields=['is_verified', 'verification_type'])
    return Response({'success': True, 'verification_type': 'blue'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_verification(request):
    reason = request.data.get('reason', '').strip()
    if not reason:
        return Response({'error': 'Provide a reason'}, status=400)
    vr = VerificationRequest.objects.create(user=request.user, reason=reason)
    return Response({'success': True, 'id': vr.id}, status=201)


# ── Profile ───────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserPrivateSerializer(request.user).data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    s = UserPrivateSerializer(request.user, data=request.data, partial=True)
    if s.is_valid():
        s.save()
        return Response(s.data)
    return Response(s.errors, status=400)


@api_view(['GET'])
@permission_classes([AllowAny])
def user_profile(request, user_id):
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    return Response(UserPublicSerializer(user).data)


# ── Videos ────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def feed(request):
    videos = Video.objects.filter(
        is_deleted=False, visibility='public'
    ).select_related('user').order_by('-created_at')[:50]
    return Response(VideoSerializer(videos, many=True, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_video(request):
    s = VideoUploadSerializer(data=request.data)
    if not s.is_valid():
        return Response(s.errors, status=400)
    video = s.save(user=request.user)
    return Response(VideoSerializer(video, context={'request': request}).data, status=201)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_video(request, video_id):
    try:
        video = Video.objects.get(pk=video_id, user=request.user)
    except Video.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    video.is_deleted = True
    video.save()
    return Response({'success': True})


@api_view(['GET'])
@permission_classes([AllowAny])
def user_videos(request, user_id):
    videos = Video.objects.filter(
        user_id=user_id, is_deleted=False, visibility='public'
    ).order_by('-created_at')
    return Response(VideoSerializer(videos, many=True, context={'request': request}).data)


# ── Interactions ──────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def like_video(request, video_id):
    try:
        video = Video.objects.get(pk=video_id)
    except Video.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    like, created = Like.objects.get_or_create(user=request.user, video=video)
    if created:
        Video.objects.filter(pk=video_id).update(likes_count=F('likes_count') + 1)
        User.objects.filter(pk=video.user_id).update(likes_count=F('likes_count') + 1)
        Notification.objects.create(
            user=video.user, sender=request.user,
            type='like', text=f'@{request.user.username} liked your video'
        )
        return Response({'liked': True, 'likes_count': video.likes_count + 1})
    else:
        like.delete()
        Video.objects.filter(pk=video_id).update(likes_count=F('likes_count') - 1)
        User.objects.filter(pk=video.user_id).update(likes_count=F('likes_count') - 1)
        return Response({'liked': False, 'likes_count': max(0, video.likes_count - 1)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def view_video(request, video_id):
    from django.core.cache import cache
    user_id = request.user.id if request.user.is_authenticated else None
    # Use cache to track unique views per user per video
    cache_key = f'view_{video_id}_{user_id or request.META.get("REMOTE_ADDR", "anon")}'
    already_viewed = cache.get(cache_key)
    if already_viewed:
        return Response({'counted': False})
    # Mark as viewed for 24 hours
    cache.set(cache_key, True, 60 * 60 * 24)
    Video.objects.filter(pk=video_id).update(views_count=F('views_count') + 1)
    counted = True
    return Response({'success': True})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def comments(request, video_id):
    try:
        video = Video.objects.get(pk=video_id)
    except Video.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    if request.method == 'GET':
        c = Comment.objects.filter(video=video, parent=None).select_related('user')
        return Response(CommentSerializer(c, many=True).data)
    s = CommentSerializer(data=request.data)
    if s.is_valid():
        comment = s.save(user=request.user, video=video)
        Video.objects.filter(pk=video_id).update(comments_count=F('comments_count') + 1)
        Notification.objects.create(
            user=video.user, sender=request.user,
            type='comment', text=f'@{request.user.username} commented: {comment.text[:60]}'
        )
        return Response(CommentSerializer(comment).data, status=201)
    return Response(s.errors, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_video(request, video_id):
    try:
        video = Video.objects.get(pk=video_id)
    except Video.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    save_obj, created = Save.objects.get_or_create(user=request.user, video=video)
    if created:
        Video.objects.filter(pk=video_id).update(saves_count=F('saves_count') + 1)
        return Response({'saved': True})
    save_obj.delete()
    Video.objects.filter(pk=video_id).update(saves_count=F('saves_count') - 1)
    return Response({'saved': False})


# ── Follow ────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def follow_user(request, user_id):
    if str(user_id) == str(request.user.id):
        return Response({'error': 'Cannot follow yourself'}, status=400)
    try:
        target = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    follow, created = Follow.objects.get_or_create(follower=request.user, following=target)
    if created:
        User.objects.filter(pk=user_id).update(followers_count=F('followers_count') + 1)
        User.objects.filter(pk=request.user.id).update(following_count=F('following_count') + 1)
        Notification.objects.create(
            user=target, sender=request.user,
            type='follow', text=f'@{request.user.username} started following you'
        )
        return Response({'following': True})
    follow.delete()
    User.objects.filter(pk=user_id).update(followers_count=F('followers_count') - 1)
    User.objects.filter(pk=request.user.id).update(following_count=F('following_count') - 1)
    return Response({'following': False})


# ── Notifications ─────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications(request):
    n = Notification.objects.filter(user=request.user).order_by('-created_at')[:40]
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response(NotificationSerializer(n, many=True).data)


# ── Search ────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def search(request):
    q = request.query_params.get('q', '').strip()
    if not q:
        return Response({'users': [], 'videos': []})
    users = User.objects.filter(username__icontains=q)[:10]
    videos = Video.objects.filter(caption__icontains=q, is_deleted=False)[:20]
    return Response({
        'users': UserPublicSerializer(users, many=True).data,
        'videos': VideoSerializer(videos, many=True, context={'request': request}).data,
    })


# ── Ads ───────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def active_ads(request):
    ads = AdLink.objects.filter(is_active=True)
    return Response(AdLinkSerializer(ads, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def record_ad_view(request, ad_id):
    try:
        ad = AdLink.objects.get(pk=ad_id, is_active=True)
    except AdLink.DoesNotExist:
        return Response({'error': 'Ad not found'}, status=404)
    video_id = request.data.get('video_id')
    video = None
    if video_id:
        try:
            video = Video.objects.get(pk=video_id)
        except Video.DoesNotExist:
            pass
    AdView.objects.create(user=request.user, ad_link=ad, video=video)
    return Response({'success': True})


# ── Withdrawal ────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_withdrawal(request):
    amount = request.data.get('amount')
    method = request.data.get('method', '')
    account = request.data.get('account_details', '')
    if not amount or not method or not account:
        return Response({'error': 'All fields required'}, status=400)
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return Response({'error': 'Invalid amount'}, status=400)
    if request.user.balance < amount:
        return Response({'error': 'Insufficient balance'}, status=400)
    WithdrawalRequest.objects.create(
        user=request.user, amount=amount, method=method, account_details=account
    )
    User.objects.filter(pk=request.user.id).update(balance=F('balance') - amount)
    return Response({'success': True})


# ── Verification application ─────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_verification(request):
    from .models import PlatformSettings
    # Check if verification is open
    try:
        cfg = PlatformSettings.objects.first()
        if cfg and not cfg.verification_open:
            return Response({'error': 'Verification applications are currently closed'}, status=400)
    except:
        pass
    
    user = request.user
    if user.is_verified:
        return Response({'error': 'Already verified'}, status=400)
    
    # Check eligibility
    if user.followers_count < 60:
        return Response({'error': f'You need at least 60 followers. You have {user.followers_count}.'}, status=400)
    
    total_views = Video.objects.filter(user=user, is_deleted=False).aggregate(
        total=__import__('django.db.models', fromlist=['Sum']).Sum('views_count')
    )['total'] or 0
    
    if total_views < 5000:
        return Response({'error': f'You need at least 5,000 total views. You have {total_views}.'}, status=400)
    
    reason = request.data.get('reason', '').strip()
    if not reason:
        return Response({'error': 'Please provide a reason'}, status=400)
    
    # Check no pending request
    if VerificationRequest.objects.filter(user=user, status='pending').exists():
        return Response({'error': 'You already have a pending application'}, status=400)
    
    VerificationRequest.objects.create(user=user, reason=reason)
    return Response({'success': True})


# ── Admin endpoints ────────────────────────────────────────────────────────────

def is_admin(user):
    return user.is_authenticated and (user.is_staff or user.username == 'samson')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_stats(request):
    if not is_admin(request.user):
        return Response({'error': 'Forbidden'}, status=403)
    from django.db.models import Sum
    return Response({
        'total_users': User.objects.count(),
        'total_videos': Video.objects.filter(is_deleted=False).count(),
        'total_views': Video.objects.aggregate(t=Sum('views_count'))['t'] or 0,
        'monetized_users': User.objects.filter(is_monetized=True).count(),
        'pending_verifications': VerificationRequest.objects.filter(status='pending').count(),
        'total_ad_revenue': str(AdView.objects.aggregate(t=Sum('gross_revenue'))['t'] or 0),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_users(request):
    if not is_admin(request.user):
        return Response({'error': 'Forbidden'}, status=403)
    users = User.objects.order_by('-date_joined')[:100]
    return Response(UserPublicSerializer(users, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_suspend_user(request, user_id):
    if not is_admin(request.user):
        return Response({'error': 'Forbidden'}, status=403)
    try:
        u = User.objects.get(pk=user_id)
        u.is_suspended = request.data.get('suspended', True)
        u.save(update_fields=['is_suspended'])
        return Response({'success': True})
    except User.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_monetize_user(request, user_id):
    if not is_admin(request.user):
        return Response({'error': 'Forbidden'}, status=403)
    try:
        u = User.objects.get(pk=user_id)
        u.is_monetized = request.data.get('monetized', True)
        u.save(update_fields=['is_monetized'])
        return Response({'success': True})
    except User.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_verification_requests(request):
    if not is_admin(request.user):
        return Response({'error': 'Forbidden'}, status=403)
    reqs = VerificationRequest.objects.filter(status='pending').select_related('user').order_by('-created_at')
    data = []
    for r in reqs:
        from django.db.models import Sum
        total_views = Video.objects.filter(user=r.user, is_deleted=False).aggregate(t=Sum('views_count'))['t'] or 0
        data.append({
            'id': r.id,
            'username': r.user.username,
            'followers_count': r.user.followers_count,
            'total_views': total_views,
            'reason': r.reason,
            'created_at': str(r.created_at),
        })
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_approve_verification(request, req_id):
    if not is_admin(request.user):
        return Response({'error': 'Forbidden'}, status=403)
    try:
        r = VerificationRequest.objects.get(pk=req_id)
        r.status = 'approved'
        r.save()
        r.user.is_verified = True
        r.user.verification_type = 'blue'
        r.user.save(update_fields=['is_verified', 'verification_type'])
        return Response({'success': True})
    except VerificationRequest.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_reject_verification(request, req_id):
    if not is_admin(request.user):
        return Response({'error': 'Forbidden'}, status=403)
    try:
        r = VerificationRequest.objects.get(pk=req_id)
        r.status = 'rejected'
        r.save()
        return Response({'success': True})
    except VerificationRequest.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_verify_user(request, user_id):
    if not is_admin(request.user):
        return Response({'error': 'Forbidden'}, status=403)
    try:
        u = User.objects.get(pk=user_id)
        verified = request.data.get('verified', True)
        u.is_verified = verified
        u.verification_type = 'blue' if verified else 'none'
        u.save(update_fields=['is_verified', 'verification_type'])
        return Response({'success': True, 'is_verified': verified})
    except User.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def admin_manage_ads(request):
    if not is_admin(request.user):
        return Response({'error': 'Forbidden'}, status=403)
    if request.method == 'POST':
        title = request.data.get('title', '').strip()
        if not title:
            return Response({'error': 'Title required'}, status=400)
        ad = AdLink.objects.create(
            title=title,
            platform=request.data.get('platform', 'monetag'),
            ad_url=request.data.get('ad_url', ''),
            ad_code=request.data.get('ad_code', ''),
            thumbnail_url=request.data.get('thumbnail_url', ''),
            revenue_per_view=float(request.data.get('revenue_per_view', 0.0001)),
            show_frequency=int(request.data.get('show_frequency', 7)),
            is_active=True,
        )
        return Response({
            'id': ad.id, 'title': ad.title, 'platform': ad.platform,
            'ad_url': ad.ad_url, 'revenue_per_view': str(ad.revenue_per_view),
            'show_frequency': ad.show_frequency, 'is_active': ad.is_active,
        }, status=201)
    ads = AdLink.objects.order_by('-created_at')
    return Response([{
        'id': a.id, 'title': a.title, 'platform': a.platform,
        'ad_url': a.ad_url, 'revenue_per_view': str(a.revenue_per_view),
        'show_frequency': a.show_frequency, 'is_active': a.is_active,
    } for a in ads])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_toggle_ad(request, ad_id):
    if not is_admin(request.user):
        return Response({'error': 'Forbidden'}, status=403)
    try:
        ad = AdLink.objects.get(pk=ad_id)
        ad.is_active = request.data.get('is_active', not ad.is_active)
        ad.save(update_fields=['is_active'])
        return Response({'success': True, 'is_active': ad.is_active})
    except AdLink.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def admin_delete_ad(request, ad_id):
    if not is_admin(request.user):
        return Response({'error': 'Forbidden'}, status=403)
    try:
        AdLink.objects.get(pk=ad_id).delete()
        return Response({'success': True})
    except AdLink.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def admin_settings(request):
    if not is_admin(request.user):
        return Response({'error': 'Forbidden'}, status=403)
    from .models import PlatformSettings
    cfg, _ = PlatformSettings.objects.get_or_create(pk=1)
    if request.method == 'POST':
        for key in ['verification_open', 'monetization_open', 'registration_open']:
            if key in request.data:
                setattr(cfg, key, request.data[key])
        cfg.save()
    return Response({
        'verification_open': cfg.verification_open,
        'monetization_open': cfg.monetization_open,
        'registration_open': cfg.registration_open,
    })


# ── Username-based profile helpers (used by mobile app) ──────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def user_profile_by_username(request, username):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    videos = Video.objects.filter(user=user, is_deleted=False, visibility='public').order_by('-created_at')
    return Response({
        'user': UserPublicSerializer(user).data,
        'videos': VideoSerializer(videos, many=True, context={'request': request}).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def follow_user_by_username(request, username):
    try:
        target = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    if str(target.pk) == str(request.user.id):
        return Response({'error': 'Cannot follow yourself'}, status=400)
    follow, created = Follow.objects.get_or_create(follower=request.user, following=target)
    if created:
        from django.db.models import F
        User.objects.filter(pk=target.pk).update(followers_count=F('followers_count') + 1)
        User.objects.filter(pk=request.user.id).update(following_count=F('following_count') + 1)
        Notification.objects.create(
            user=target, sender=request.user,
            type='follow', text=f'@{request.user.username} started following you'
        )
        return Response({'following': True})
    follow.delete()
    from django.db.models import F
    User.objects.filter(pk=target.pk).update(followers_count=F('followers_count') - 1)
    User.objects.filter(pk=request.user.id).update(following_count=F('following_count') - 1)
    return Response({'following': False})


@api_view(['GET'])
@permission_classes([AllowAny])
def user_videos_by_username(request, username):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    videos = Video.objects.filter(user=user, is_deleted=False, visibility='public').order_by('-created_at')
    return Response(VideoSerializer(videos, many=True, context={'request': request}).data)


# ── Fixed upload view (replaces the broken one above) ────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_video_v2(request):
    video_file = request.FILES.get('video_file')
    if not video_file:
        return Response({'error': 'No video file provided'}, status=400)
    try:
        from .supabase_storage import upload_video as sup_upload_video, upload_thumbnail
        video_url = sup_upload_video(video_file)
        thumbnail_url = ''
        thumb_file = request.FILES.get('thumbnail')
        if thumb_file:
            thumbnail_url = upload_thumbnail(thumb_file)
    except Exception as e:
        return Response({'error': f'Upload failed: {str(e)}'}, status=500)
    video = Video.objects.create(
        user=request.user,
        video_url=video_url,
        thumbnail_url=thumbnail_url,
        caption=request.data.get('caption', ''),
        visibility=request.data.get('visibility', 'public'),
    )
    return Response(VideoSerializer(video, context={'request': request}).data, status=201)


# ── Fixed upload view (replaces the broken one above) ────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_video_v2(request):
    video_file = request.FILES.get('video_file')
    if not video_file:
        return Response({'error': 'No video file provided'}, status=400)
    try:
        from .supabase_storage import upload_video as sup_upload_video, upload_thumbnail
        video_url = sup_upload_video(video_file)
        thumbnail_url = ''
        thumb_file = request.FILES.get('thumbnail')
        if thumb_file:
            thumbnail_url = upload_thumbnail(thumb_file)
    except Exception as e:
        return Response({'error': f'Upload failed: {str(e)}'}, status=500)
    video = Video.objects.create(
        user=request.user,
        video_url=video_url,
        thumbnail_url=thumbnail_url,
        caption=request.data.get('caption', ''),
        visibility=request.data.get('visibility', 'public'),
    )
    return Response(VideoSerializer(video, context={'request': request}).data, status=201)
