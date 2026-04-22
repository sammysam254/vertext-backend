from django.db import models as M
from django.utils import timezone
from datetime import timedelta
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken
from .models import (User, Video, Like, Comment, Save, Follow,
                     AdLink, AdView, Notification, WithdrawalRequest)
from .serializers import (UserPublicSerializer, UserPrivateSerializer,
    RegisterSerializer, VideoSerializer, CommentSerializer,
    AdLinkSerializer, NotificationSerializer)


# ── Auth ──────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    from .serializers import RegisterSerializer
    ser = RegisterSerializer(data=request.data)
    if not ser.is_valid():
        first_error = next(iter(ser.errors.values()))[0]
        return Response({'detail': str(first_error)}, status=400)
    user = ser.save()
    refresh = RefreshToken.for_user(user)
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserPrivateSerializer(user).data,
    }, status=201)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    from django.contrib.auth import authenticate
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')
    if not username or not password:
        return Response({'detail': 'Username and password required'}, status=400)
    user = authenticate(username=username, password=password)
    if not user:
        try:
            u = User.objects.get(email__iexact=username)
            user = authenticate(username=u.username, password=password)
        except User.DoesNotExist:
            pass
    if not user:
        return Response({'detail': 'Wrong username or password'}, status=401)
    if user.is_suspended:
        return Response({'detail': 'Account suspended. Contact support.'}, status=403)
    refresh = RefreshToken.for_user(user)
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserPrivateSerializer(user).data,
    })


@api_view(['GET', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def me(request):
    if request.method == 'GET':
        return Response(UserPrivateSerializer(request.user).data)
    # Handle avatar upload
    if request.FILES.get('avatar'):
        try:
            from .supabase_storage import upload_avatar
            url = upload_avatar(request.FILES['avatar'])
            request.user.avatar = url
            request.user.save(update_fields=['avatar'])
        except Exception as e:
            return Response({'detail': f'Avatar upload failed: {e}'}, status=400)
    # Handle other fields
    allowed = ['bio', 'first_name', 'last_name']
    for field in allowed:
        if field in request.data:
            setattr(request.user, field, request.data[field])
    request.user.save()
    return Response(UserPrivateSerializer(request.user).data)


# ── Feed ──────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticatedOrReadOnly])
def feed(request):
    videos = Video.objects.filter(
        visibility='public', is_deleted=False
    ).select_related('user').order_by('-created_at')[:50]
    return Response(VideoSerializer(videos, many=True, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def following_feed(request):
    ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    if ids:
        qs = Video.objects.filter(user__in=ids, visibility__in=['public','friends'], is_deleted=False)
    else:
        qs = Video.objects.filter(visibility='public', is_deleted=False)
    return Response(VideoSerializer(
        qs.select_related('user').order_by('-created_at')[:30],
        many=True, context={'request': request}
    ).data)


# ── Video Upload — stores in Supabase Storage ──────────────

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_video(request):
    video_file = request.FILES.get('video_file')
    thumbnail_file = request.FILES.get('thumbnail')
    caption = request.data.get('caption', '')
    visibility = request.data.get('visibility', 'public')

    if not video_file:
        return Response({'detail': 'No video file provided'}, status=400)

    try:
        from .supabase_storage import upload_video as sb_upload_video, upload_thumbnail
        # Upload video to Supabase
        video_url = sb_upload_video(video_file)
        # Upload thumbnail if provided
        thumb_url = ''
        if thumbnail_file:
            thumb_url = upload_thumbnail(thumbnail_file)

        video = Video.objects.create(
            user=request.user,
            video_url=video_url,
            thumbnail_url=thumb_url,
            caption=caption,
            visibility=visibility,
        )
        return Response(VideoSerializer(video, context={'request': request}).data, status=201)

    except Exception as e:
        return Response({'detail': f'Upload failed: {str(e)}'}, status=500)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_video(request, video_id):
    try:
        video = Video.objects.get(pk=video_id)
    except Video.DoesNotExist:
        return Response({'detail': 'Not found'}, status=404)
    if video.user != request.user and not request.user.is_staff:
        return Response({'detail': 'Forbidden'}, status=403)
    video.is_deleted = True
    video.save()
    return Response({'detail': 'Deleted'})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def like_video(request, video_id):
    try:
        video = Video.objects.get(pk=video_id, is_deleted=False)
    except Video.DoesNotExist:
        return Response({'detail': 'Not found'}, status=404)
    like, created = Like.objects.get_or_create(user=request.user, video=video)
    if not created:
        like.delete()
        Video.objects.filter(pk=video_id).update(likes_count=M.F('likes_count') - 1)
        User.objects.filter(pk=video.user.pk).update(likes_count=M.F('likes_count') - 1)
        return Response({'liked': False})
    Video.objects.filter(pk=video_id).update(likes_count=M.F('likes_count') + 1)
    User.objects.filter(pk=video.user.pk).update(likes_count=M.F('likes_count') + 1)
    if video.user != request.user:
        Notification.objects.create(
            user=video.user, sender=request.user, type='like',
            text=f'@{request.user.username} liked your video'
        )
    return Response({'liked': True})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def save_video(request, video_id):
    try:
        video = Video.objects.get(pk=video_id, is_deleted=False)
    except Video.DoesNotExist:
        return Response({'detail': 'Not found'}, status=404)
    sv, created = Save.objects.get_or_create(user=request.user, video=video)
    if not created:
        sv.delete()
        Video.objects.filter(pk=video_id).update(saves_count=M.F('saves_count') - 1)
        return Response({'saved': False})
    Video.objects.filter(pk=video_id).update(saves_count=M.F('saves_count') + 1)
    return Response({'saved': True})


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticatedOrReadOnly])
def comments(request, video_id):
    try:
        video = Video.objects.get(pk=video_id, is_deleted=False)
    except Video.DoesNotExist:
        return Response({'detail': 'Not found'}, status=404)
    if request.method == 'GET':
        qs = video.comments.filter(parent=None).select_related('user').order_by('-created_at')
        return Response(CommentSerializer(qs, many=True).data)
    ser = CommentSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    c = ser.save(user=request.user, video=video)
    Video.objects.filter(pk=video_id).update(comments_count=M.F('comments_count') + 1)
    if video.user != request.user:
        Notification.objects.create(
            user=video.user, sender=request.user, type='comment',
            text=f'@{request.user.username} commented: {c.text[:50]}'
        )
    return Response(CommentSerializer(c).data, status=201)


# ── Profile ───────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticatedOrReadOnly])
def user_profile(request, username):
    try:
        user = User.objects.get(username=username, is_active=True)
    except User.DoesNotExist:
        return Response({'detail': 'User not found'}, status=404)
    is_following = (Follow.objects.filter(follower=request.user, following=user).exists()
                    if request.user.is_authenticated else False)
    videos = Video.objects.filter(
        user=user, visibility='public', is_deleted=False
    ).order_by('-created_at')[:30]
    return Response({
        'user': {**UserPublicSerializer(user).data, 'is_following': is_following},
        'videos': VideoSerializer(videos, many=True, context={'request': request}).data,
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def follow_user(request, username):
    try:
        target = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'detail': 'User not found'}, status=404)
    if target == request.user:
        return Response({'detail': 'Cannot follow yourself'}, status=400)
    follow, created = Follow.objects.get_or_create(follower=request.user, following=target)
    if not created:
        follow.delete()
        User.objects.filter(pk=target.pk).update(followers_count=M.F('followers_count') - 1)
        User.objects.filter(pk=request.user.pk).update(following_count=M.F('following_count') - 1)
        return Response({'following': False})
    User.objects.filter(pk=target.pk).update(followers_count=M.F('followers_count') + 1)
    User.objects.filter(pk=request.user.pk).update(following_count=M.F('following_count') + 1)
    Notification.objects.create(
        user=target, sender=request.user, type='follow',
        text=f'@{request.user.username} started following you'
    )
    return Response({'following': True})


# ── Earnings ──────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def earnings(request):
    u = request.user
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    views = AdView.objects.filter(user=u)
    daily = []
    for i in range(7):
        day = now - timedelta(days=i)
        ds = day.replace(hour=0, minute=0, second=0, microsecond=0)
        de = ds + timedelta(days=1)
        dv = views.filter(created_at__gte=ds, created_at__lt=de)
        daily.append({
            'date': day.strftime('%a'),
            'amount': float(dv.aggregate(t=M.Sum('creator_revenue'))['t'] or 0),
            'ads': dv.count()
        })
    return Response({
        'total_earnings': float(u.total_earnings),
        'balance': float(u.balance),
        'this_week': float(views.filter(created_at__gte=week_start).aggregate(t=M.Sum('creator_revenue'))['t'] or 0),
        'today': float(views.filter(created_at__gte=today_start).aggregate(t=M.Sum('creator_revenue'))['t'] or 0),
        'ad_views_count': views.count(),
        'daily_breakdown': daily,
        'rate': 0.40,
        'is_monetized': u.is_monetized,
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def request_withdrawal(request):
    amount = float(request.data.get('amount', 0))
    if amount < 7.7:
        return Response({'detail': 'Minimum withdrawal is KES 1,000'}, status=400)
    if float(request.user.balance) < amount:
        return Response({'detail': 'Insufficient balance'}, status=400)
    WithdrawalRequest.objects.create(
        user=request.user, amount=amount,
        method=request.data.get('method', 'mpesa'),
        account_details=request.data.get('account', ''),
    )
    User.objects.filter(pk=request.user.pk).update(balance=M.F('balance') - amount)
    return Response({'detail': 'Withdrawal submitted successfully'})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notifications(request):
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')[:50]
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response(NotificationSerializer(notifs, many=True).data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticatedOrReadOnly])
def active_ads(request):
    return Response(AdLinkSerializer(AdLink.objects.filter(is_active=True), many=True).data)
