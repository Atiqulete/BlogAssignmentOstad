from django.contrib import admin
from django.utils.html import format_html
from .models import Profile, Blog, Category, Favorite, Rating, ContactMessage, Comment

# Admin configuration for the ContactMessage model.
class ContactMessageAdmin(admin.ModelAdmin):
    """
    Customizes the Django admin view for the ContactMessage model.
    """
    list_display = ('name', 'email', 'message_preview', 'submitted_at')
    list_filter = ('submitted_at',)
    search_fields = ('name', 'email', 'message')
    readonly_fields = ('name', 'email', 'message', 'submitted_at')
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message Preview'

    def has_add_permission(self, request):
        return False


# Admin configuration for the Comment model
class CommentAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Comment model.
    """
    list_display = ('user', 'blog', 'content_preview', 'created_at', 'parent_comment')
    list_filter = ('created_at', 'blog')
    search_fields = ('user__username', 'blog__title', 'content')
    # Corrected field name back to 'updated_at' to match the likely model field.
    readonly_fields = ('created_at',)
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'


# Registering models with the Django admin site.
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Profile model.
    """
    list_display = ['user', 'user_type', 'email_verified', 'profile_picture_preview']
    list_filter = ['user_type', 'email_verified']
    readonly_fields = ['verification_token', 'profile_picture_preview']
    
    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.profile_picture.url)
        return "No Image"
    profile_picture_preview.short_description = 'Profile Picture'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Category model.
    """
    list_display = ['name', 'blog_count']
    search_fields = ['name']
    
    def blog_count(self, obj):
        return obj.blogs.count()
    blog_count.short_description = 'Number of Blogs'


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Blog model.
    """
    list_display = ['title', 'author', 'created_at', 'published', 'featured_image_preview', 'comment_count', 'average_rating']
    list_filter = ['published', 'created_at', 'categories', 'author']
    search_fields = ['title', 'content', 'author__username']
    readonly_fields = ['created_at', 'updated_at', 'featured_image_preview']
    filter_horizontal = ['categories']
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'content', 'author', 'published')
        }),
        ('Media', {
            'fields': ('featured_image', 'featured_image_preview')
        }),
        ('Categories', {
            'fields': ('categories',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def featured_image_preview(self, obj):
        if obj.featured_image:
            return format_html('<img src="{}" width="100" height="60" style="object-fit: cover;" />', obj.featured_image.url)
        return "No Image"
    featured_image_preview.short_description = 'Featured Image Preview'
    
    def comment_count(self, obj):
        return obj.comments.count()
    comment_count.short_description = 'Comments'
    
    def average_rating(self, obj):
        avg_rating = obj.average_rating
        return f"{avg_rating:.1f}/5" if avg_rating else "No ratings"
    average_rating.short_description = 'Avg Rating'


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Favorite model.
    """
    list_display = ['user', 'blog_title', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'blog__title']
    
    def blog_title(self, obj):
        return obj.blog.title
    blog_title.short_description = 'Blog Title'


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Rating model.
    """
    list_display = ['user', 'blog_title', 'score', 'created_at']
    list_filter = ['score', 'created_at']
    search_fields = ['user__username', 'blog__title']
    
    def blog_title(self, obj):
        return obj.blog.title
    blog_title.short_description = 'Blog Title'


# Register the ContactMessage model using its custom admin class
admin.site.register(ContactMessage, ContactMessageAdmin)
admin.site.register(Comment, CommentAdmin)

# Customize admin site header and title
admin.site.site_header = "Blog Administration"
admin.site.site_title = "Blog Admin Portal"
admin.site.index_title = "Welcome to Blog Administration Portal"
