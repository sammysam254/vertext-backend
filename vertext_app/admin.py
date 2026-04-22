from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as Base
from .models import User, Video, AdLink, AdView, Comment, WithdrawalRequest

@admin.register(User)
class UserAdmin(Base):
    list_display = ['username','email','is_monetized','is_verified','is_suspended','followers_count','total_earnings']
    list_filter = ['is_monetized','is_verified','is_suspended','is_staff']
    search_fields = ['username','email']
    actions = ['monetize','suspend','unsuspend','verify']
    fieldsets = Base.fieldsets + (('Vertext', {'fields': ('bio','avatar','is_monetized','is_verified','is_suspended','followers_count','following_count','likes_count','total_earnings','balance')}),)
    readonly_fields = ['followers_count','following_count','likes_count','total_earnings','balance']
    @admin.action(description='✅ Monetize') 
    def monetize(self, r, qs): qs.update(is_monetized=True)
    @admin.action(description='🚫 Suspend')
    def suspend(self, r, qs): qs.update(is_suspended=True, is_active=False)
    @admin.action(description='✅ Unsuspend')
    def unsuspend(self, r, qs): qs.update(is_suspended=False, is_active=True)
    @admin.action(description='✓ Verify')
    def verify(self, r, qs): qs.update(is_verified=True)

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ['id','user','caption','likes_count','views_count','is_deleted','created_at']
    list_filter = ['is_deleted','visibility','is_ad']
    search_fields = ['user__username','caption']
    actions = ['soft_delete','restore']
    @admin.action(description='🗑 Delete')
    def soft_delete(self, r, qs): qs.update(is_deleted=True)
    @admin.action(description='♻ Restore')
    def restore(self, r, qs): qs.update(is_deleted=False)

@admin.register(AdLink)
class AdLinkAdmin(admin.ModelAdmin):
    list_display = ['title','platform','revenue_per_view','is_active']

@admin.register(WithdrawalRequest)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ['user','amount','method','status','created_at']
    list_filter = ['status']
    actions = ['approve','reject']
    @admin.action(description='✅ Approve')
    def approve(self, r, qs):
        from django.utils import timezone
        qs.update(status='approved', processed_at=timezone.now())
    @admin.action(description='❌ Reject')
    def reject(self, r, qs):
        from django.utils import timezone
        qs.update(status='rejected', processed_at=timezone.now())

admin.site.site_header = 'Vertext Admin'
admin.site.site_title = 'Vertext'
admin.site.index_title = 'Platform Management'
