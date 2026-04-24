from django.urls import path
from . import views

urlpatterns = [
    path('auth/login/', views.login_view),
    path('auth/register/', views.register),
    path('auth/me/', views.me),
    path('feed/', views.feed),
    path('feed/following/', views.following_feed),
    path('videos/upload/', views.upload_video),
    path('videos/<int:video_id>/delete/', views.delete_video),
    path('videos/<int:video_id>/like/', views.like_video),
    path('videos/<int:video_id>/save/', views.save_video),
    path('videos/<int:video_id>/view/', views.view_video),   # ← new
    path('videos/<int:video_id>/comments/', views.comments),
    path('profile/<str:username>/', views.user_profile),
    path('profile/<str:username>/follow/', views.follow_user),
    path('earnings/', views.earnings),
    path('earnings/withdraw/', views.request_withdrawal),
    path('notifications/', views.notifications),
    path('ads/', views.active_ads),
    path('ads/<int:ad_id>/view/', views.record_ad_view),
]
