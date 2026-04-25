from rest_framework import serializers
from .models import User, Video, Comment, Like, Save, AdLink, Notification, Follow


class UserPublicSerializer(serializers.ModelSerializer):
    is_followed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'avatar', 'is_verified', 'verification_type',
                  'followers_count', 'following_count', 'likes_count', 'bio', 'is_followed']

    def get_is_followed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Follow.objects.filter(follower=request.user, following=obj).exists()
        return False


class UserPrivateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'avatar', 'bio', 'is_verified',
                  'verification_type', 'is_monetized', 'followers_count',
                  'following_count', 'likes_count', 'total_earnings', 'balance', 'date_joined']
        read_only_fields = ['is_verified', 'verification_type', 'is_monetized',
                            'total_earnings', 'balance',
                            'followers_count', 'following_count', 'likes_count']


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=4)

    def validate_username(self, v):
        if User.objects.filter(username=v).exists():
            raise serializers.ValidationError("Username already taken")
        return v

    def validate_email(self, v):
        if User.objects.filter(email=v).exists():
            raise serializers.ValidationError("Email already registered")
        return v

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
        )


class VideoSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()

    def get_user(self, obj):
        return UserPublicSerializer(obj.user, context=self.context).data

    class Meta:
        model = Video
        fields = ['id', 'user', 'video_url', 'thumbnail_url', 'caption',
                  'likes_count', 'comments_count', 'shares_count', 'saves_count',
                  'views_count', 'is_liked', 'is_saved', 'is_ad', 'visibility', 'created_at']

    def get_is_liked(self, obj):
        req = self.context.get('request')
        if req and req.user.is_authenticated:
            return Like.objects.filter(user=req.user, video=obj).exists()
        return False

    def get_is_saved(self, obj):
        req = self.context.get('request')
        if req and req.user.is_authenticated:
            return Save.objects.filter(user=req.user, video=obj).exists()
        return False


class VideoUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ['video_url', 'thumbnail_url', 'caption', 'visibility']


class CommentSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'user', 'text', 'likes', 'parent', 'created_at']
        read_only_fields = ['likes']


class AdLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdLink
        fields = ['id', 'title', 'platform', 'ad_url', 'revenue_per_view']


class NotificationSerializer(serializers.ModelSerializer):
    sender = UserPublicSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'sender', 'type', 'text', 'is_read', 'created_at']
