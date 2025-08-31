# blog_app/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Avg
import uuid

# User Profile Model
class Profile(models.Model):
    """Extends the default Django User model with additional fields."""
    USER_TYPES = (
        ('admin', 'Admin'),
        ('author', 'Author'),
        ('reader', 'Reader'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='reader')
    bio = models.TextField(blank=True, null=True)
    # এখানে প্রোফাইল ছবির জন্য ImageField যুক্ত করা হয়েছে।
    profile_picture = models.ImageField(
        upload_to='profile_pics/', 
        blank=True, 
        null=True,
        default='profile_pics/default.jpg'
    )
    social_media = models.URLField(blank=True, null=True)
    email_verified = models.BooleanField(default=False)
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False)

    def __str__(self):
        return f"{self.user.username}'s Profile"

# Signal to create a Profile for new Users
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Creates a Profile instance whenever a new User is created."""
    if created:
        Profile.objects.create(user=instance)

# Category Model
class Category(models.Model):
    """Represents a category for blog posts."""
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

# Blog Post Model
class Blog(models.Model):
    """Represents a single blog post."""
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts')
    categories = models.ManyToManyField(Category, related_name='blogs')
    # এখানে ব্লগ পোস্টের প্রধান ছবির জন্য ImageField যুক্ত করা হয়েছে।
    featured_image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title
    
    @property
    def average_rating(self):
        """Calculates the average rating for the blog post using database aggregation."""
        ratings = self.blog_ratings.aggregate(Avg('score'))
        return round(ratings['score__avg'], 1) if ratings['score__avg'] else 0

    class Meta:
        ordering = ['-created_at']



class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'blog')

class Dislike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'blog')


# Favorite Model
class Favorite(models.Model):
    """Allows a user to favorite a blog post."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'blog')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} favorited {self.blog.title}"

# Rating Model
class Rating(models.Model):
    """Allows a user to rate a blog post."""
    RATING_CHOICES = [(i, i) for i in range(1, 6)]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='blog_ratings')
    score = models.IntegerField(choices=RATING_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'blog')
    
    def __str__(self):
        return f"{self.user.username} rated {self.blog.title} as {self.score}"

# Contact Message Model
class ContactMessage(models.Model):
    """Stores messages submitted via the contact form."""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} on {self.submitted_at.strftime('%Y-%m-%d')}"
    
    class Meta:
        ordering = ['-submitted_at']

# Comment Model - নতুন যুক্ত করা হয়েছে
class Comment(models.Model):
    """
    Represents a comment on a blog post, with support for nested replies.
    """
    blog = models.ForeignKey(
        'Blog',
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Blog Post'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='User'
    )
    content = models.TextField(verbose_name='Comment Content')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Posted At')
    parent_comment = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='Parent Comment'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Comment'
        verbose_name_plural = 'Comments'

    def __str__(self):
        return f'Comment by {self.user.username} on {self.blog.title[:30]}'

    def get_replies(self):
        """Returns all replies to this comment."""
        return self.replies.all()
