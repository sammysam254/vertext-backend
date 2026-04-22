from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    bio = models.TextField(blank=True)
    avatar = models.URLField(blank=True, max_length=500)  # Supabase URL
    is_monetized = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    total_earnings = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    followers_count = models.PositiveIntegerField(default=0)
    following_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'vertext_user'


class Follow(models.Model):
    follower = models.ForeignKey(User, related_name='following', on_delete=models.CASCADE)
    following = models.ForeignKey(User, related_name='followers', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('follower', 'following')


class AdLink(models.Model):
    PLATFORM_CHOICES = [('monetag','Monetag'),('adsense','Google AdSense'),('custom','Custom')]
    title = models.CharField(max_length=200)
    platform = models.CharField(max_length=50, choices=PLATFORM_CHOICES)
    ad_code = models.TextField(blank=True)
    ad_url = models.URLField(blank=True)
    thumbnail = models.URLField(blank=True, max_length=500)
    revenue_per_view = models.DecimalField(max_digits=8, decimal_places=6, default=0.0001)
    is_active = models.BooleanField(default=True)
    show_frequency = models.PositiveIntegerField(default=7)
    created_at = models.DateTimeField(auto_now_add=True)


class Video(models.Model):
    VISIBILITY = [('public','Public'),('friends','Friends'),('private','Private')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='videos')
    # Store Supabase public URLs directly — no local file storage
    video_url = models.URLField(max_length=1000, blank=True)
    thumbnail_url = models.URLField(max_length=1000, blank=True)
    caption = models.TextField(blank=True)
    visibility = models.CharField(max_length=10, choices=VISIBILITY, default='public')
    is_ad = models.BooleanField(default=False)
    ad_link = models.ForeignKey(AdLink, null=True, blank=True, on_delete=models.SET_NULL)
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    saves_count = models.PositiveIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']


class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('user', 'video')


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    likes = models.PositiveIntegerField(default=0)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']


class Save(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('user', 'video')


class AdView(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ad_views')
    ad_link = models.ForeignKey(AdLink, on_delete=models.CASCADE)
    video = models.ForeignKey(Video, null=True, blank=True, on_delete=models.SET_NULL)
    gross_revenue = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    creator_revenue = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    platform_revenue = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.gross_revenue = self.ad_link.revenue_per_view
        self.creator_revenue = self.gross_revenue * 4 / 10
        self.platform_revenue = self.gross_revenue * 6 / 10
        super().save(*args, **kwargs)
        if self.user.is_monetized:
            from django.db.models import F
            User.objects.filter(pk=self.user.pk).update(
                balance=F('balance') + self.creator_revenue,
                total_earnings=F('total_earnings') + self.creator_revenue
            )


class Notification(models.Model):
    TYPES = [('like','Like'),('comment','Comment'),('follow','Follow'),('earnings','Earnings')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='sent_notifications')
    type = models.CharField(max_length=20, choices=TYPES)
    text = models.CharField(max_length=300)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class WithdrawalRequest(models.Model):
    STATUS = [('pending','Pending'),('approved','Approved'),('rejected','Rejected')]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=50)
    account_details = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
