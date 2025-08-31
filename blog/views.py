# --- Imports from your file ---
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q, Avg, Count, QuerySet, Sum
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

import uuid
import json
from functools import wraps

# Import all models and forms used in the views
from .models import Blog, Profile, Favorite, Rating, Category, ContactMessage, Comment, Like, Dislike
from .forms import (
    UserRegisterForm, UserUpdateForm, ProfileUpdateForm,
    BlogForm, RatingForm, ContactForm, CommentForm
)


# --- Custom Decorator ---

def author_or_staff_required(view_func):
    """
    A custom decorator to check if the user is the blog's author or a staff member.
    This prevents unnecessary permission checks within the views themselves.
    """
    @wraps(view_func)
    def _wrapped_view(request: HttpRequest, pk: int, *args, **kwargs) -> HttpResponse:
        try:
            blog = Blog.objects.get(pk=pk)
        except Blog.DoesNotExist:
            messages.error(request, 'The blog post you are trying to access does not exist.')
            return redirect('blog:blog_list')

        if blog.author != request.user and not request.user.is_staff:
            messages.error(request, 'You can only edit or delete your own blogs.')
            return redirect('blog:blog_list')
        
        return view_func(request, pk, *args, **kwargs)
    return _wrapped_view


# --- Public Views ---

def home(request: HttpRequest) -> HttpResponse:
    """
    Renders the homepage. Since `index.html` has been removed, this view now
    simply redirects to the main blog list page.
    """
    return redirect('blog:blog_list')


def blog_list(request: HttpRequest) -> HttpResponse:
    """
    Displays a list of all published blogs. It includes functionality to
    search, filter, and sort based on query parameters.
    """
    blogs: QuerySet = Blog.objects.filter(published=True).select_related('author__profile').prefetch_related('categories')
    
    query = request.GET.get('q')
    if query:
        # Filter blogs by title, content, or author's username (case-insensitive)
        blogs = blogs.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(author__username__icontains=query)
        )
    
    category_name = request.GET.get('category')
    if category_name:
        blogs = blogs.filter(categories__name=category_name)
    
    author_username = request.GET.get('author')
    if author_username:
        blogs = blogs.filter(author__username=author_username)
    
    sort_by = request.GET.get('sort')
    if sort_by == 'rating':
        # Order by the average rating of each blog.
        blogs = blogs.annotate(avg_rating=Avg('blog_ratings__score')).order_by('-avg_rating')
    else:
        # Default to sorting by creation date.
        blogs = blogs.order_by('-created_at')
    
    # Pagination - show 10 blogs per page
    paginator = Paginator(blogs, 10)
    page = request.GET.get('page')
    
    try:
        blogs = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        blogs = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results.
        blogs = paginator.page(paginator.num_pages)
    
    # Get 5 most recent blogs for the sidebar.
    recent_blogs = Blog.objects.filter(published=True).order_by('-created_at')[:5]
    
    categories = Category.objects.all()
    authors = User.objects.filter(profile__user_type='author')
    
    context = {
        'blogs': blogs,
        'categories': categories,
        'authors': authors,
        'recent_blogs': recent_blogs,
    }
    return render(request, 'blog/blog_list.html', context)


def blog_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Displays a single blog post and handles the submission of user ratings and comments.
    """
    blog = get_object_or_404(Blog, pk=pk)
    
    is_favorited = False
    user_rating = None
    user_liked = False
    user_disliked = False
    
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=request.user, blog=blog).exists()
        try:
            user_rating = Rating.objects.get(user=request.user, blog=blog)
        except Rating.DoesNotExist:
            pass
        
        # Check if user has liked or disliked the post
        user_liked = Like.objects.filter(user=request.user, blog=blog).exists()
        user_disliked = Dislike.objects.filter(user=request.user, blog=blog).exists()
    
    # Handle comment submission
    if request.method == 'POST' and 'comment_form' in request.POST:
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid() and request.user.is_authenticated:
            # Get parent comment ID from form data if it exists for replies
            parent_comment_id = request.POST.get('parent_comment_id')
            parent_comment = None
            if parent_comment_id:
                try:
                    parent_comment = Comment.objects.get(id=parent_comment_id)
                except Comment.DoesNotExist:
                    messages.error(request, 'Invalid comment to reply to.')
                    return redirect('blog:blog_detail', pk=blog.pk)

            new_comment = comment_form.save(commit=False)
            new_comment.blog = blog
            new_comment.user = request.user
            new_comment.parent_comment = parent_comment
            new_comment.save()
            messages.success(request, 'Your comment has been posted!')
            return redirect('blog:blog_detail', pk=blog.pk)
        else:
            messages.error(request, 'There was an error posting your comment.')
    else:
        comment_form = CommentForm()
    
    # Handle rating submission
    if request.method == 'POST' and 'rating_form' in request.POST and request.user.is_authenticated:
        rating_form = RatingForm(request.POST)
        if rating_form.is_valid():
            Rating.objects.update_or_create(
                user=request.user,
                blog=blog,
                defaults={'score': rating_form.cleaned_data['score']}
            )
            messages.success(request, 'Your rating has been saved!')
            return redirect('blog:blog_detail', pk=blog.pk)
    else:
        rating_form = RatingForm(instance=user_rating)
    
    # Get all comments for the blog post (only top-level comments)
    comments = Comment.objects.filter(blog=blog, parent_comment=None).order_by('-created_at')
    
    # Paginate comments - show 10 comments per page
    comment_paginator = Paginator(comments, 10)
    comment_page = request.GET.get('comment_page')
    
    try:
        comments = comment_paginator.page(comment_page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        comments = comment_paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results.
        comments = comment_paginator.page(comment_paginator.num_pages)
    
    # Get a few recent blogs for the sidebar or related section.
    recent_blogs = Blog.objects.filter(published=True).order_by('-created_at')[:5]
    
    context = {
        'blog': blog,
        'is_favorited': is_favorited,
        'rating_form': rating_form,
        'user_rating': user_rating,
        'recent_blogs': recent_blogs,
        'comments': comments,
        'comment_form': comment_form,
        'user_liked': user_liked,
        'user_disliked': user_disliked,
    }
    return render(request, 'blog/blog_detail.html', context)


def author_list(request: HttpRequest) -> HttpResponse:
    """
    Displays a list of all authors, including the count of blogs they have published.
    """
    authors = User.objects.filter(profile__user_type='author').annotate(
        blog_count=Count('blog_posts', filter=Q(blog_posts__published=True)),
        total_likes=Count('blog_posts__like', filter=Q(blog_posts__published=True)),  # Changed from Sum to Count
        total_comments=Count('blog_posts__comments', filter=Q(blog_posts__published=True)),  # Changed from Sum to Count
        total_favorites=Count('blog_posts__favorited_by', filter=Q(blog_posts__published=True)),  # Changed from Sum to Count
        avg_rating=Avg('blog_posts__blog_ratings__score', filter=Q(blog_posts__published=True))
    ).order_by('username')

    # Pagination - show 12 authors per page
    paginator = Paginator(authors, 12)
    page = request.GET.get('page')
    
    try:
        authors = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        authors = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results.
        authors = paginator.page(paginator.num_pages)
    
    return render(request, 'blog/author_list.html', {'authors': authors})


def author_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Displays the profile of a specific author and their published blog posts.
    """
    author = get_object_or_404(User, pk=pk)
    
    if not hasattr(author, 'profile') or author.profile.user_type != 'author':
        messages.error(request, 'This user is not an author.')
        return redirect('blog:author_list')
    
    # Get published blogs with aggregated data
    blogs = Blog.objects.filter(author=author, published=True).annotate(
        like_count=Count('like'),
        dislike_count=Count('dislike'),
        favorite_count=Count('favorited_by'),
        comment_count=Count('comments')
    ).order_by('-created_at')
    
    # Calculate totals for the author
    total_likes = blogs.aggregate(total_likes=Sum('like_count'))['total_likes'] or 0
    total_dislikes = blogs.aggregate(total_dislikes=Sum('dislike_count'))['total_dislikes'] or 0
    total_favorites = blogs.aggregate(total_favorites=Sum('favorite_count'))['total_favorites'] or 0
    total_comments = blogs.aggregate(total_comments=Sum('comment_count'))['total_comments'] or 0
    
    # Pagination - show 6 blogs per page
    paginator = Paginator(blogs, 6)
    page = request.GET.get('page')
    
    try:
        blogs = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        blogs = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results.
        blogs = paginator.page(paginator.num_pages)
    
    context = {
        'author': author,
        'blogs': blogs,
        'total_likes': total_likes,
        'total_dislikes': total_dislikes,
        'total_favorites': total_favorites,
        'total_comments': total_comments,
    }
    
    return render(request, 'blog/author_detail.html', context)


# --- Authentication Views ---

def register(request: HttpRequest) -> HttpResponse:
    """
    Handles new user registration and sends a verification email.
    """
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Deactivate until email is verified
            user.save()
            
            # The profile is created automatically via the signal.
            profile = user.profile
            profile.verification_token = uuid.uuid4()
            profile.save()
            
            verification_link = request.build_absolute_uri(
                reverse('blog:verify_email', kwargs={'token': str(profile.verification_token)})
            )
            
            try:
                send_mail(
                    'Verify your email for Blog App',
                    f'Please click the following link to verify your email: {verification_link}',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                messages.success(request, 'Account created! Please check your email to verify your account.')
            except Exception as e:
                print(f"Failed to send verification email: {e}")
                messages.warning(request, 'Account created, but we could not send a verification email. Please contact support.')
            
            return redirect('blog:verify_email_sent')
    else:
        form = UserRegisterForm()
    return render(request, 'blog/register.html', {'form': form})


def verify_email_sent_view(request: HttpRequest) -> HttpResponse:
    """Renders a page to confirm a verification email has been sent."""
    return render(request, 'blog/verify_email_sent.html')


def verify_email(request: HttpRequest, token: str) -> HttpResponse:
    """
    Activates a user's account if the provided token is valid.
    """
    try:
        profile = Profile.objects.get(verification_token=token)
        profile.email_verified = True
        profile.user.is_active = True
        profile.user.save()
        profile.save()
        messages.success(request, 'Email verified! You can now log in.')
    except Profile.DoesNotExist:
        messages.error(request, 'Invalid verification token.')
    
    return redirect('blog:login')


def login_view(request: HttpRequest) -> HttpResponse:
    """Handles user login."""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                return redirect('blog:blog_list')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'blog/login.html', {'form': form})


def logout_view(request: HttpRequest) -> HttpResponse:
    """Handles user logout."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('blog:blog_list')


@login_required
def profile(request: HttpRequest) -> HttpResponse:
    """
    Allows a user to view and update their profile.
    """
    # Get user's blog posts for the management section
    user_posts = Blog.objects.filter(author=request.user).order_by('-created_at')
    
    # Calculate total likes and dislikes for user's posts
    total_likes = Like.objects.filter(blog__author=request.user).count()
    total_dislikes = Dislike.objects.filter(blog__author=request.user).count()
    
    # Calculate total favorites and comments for user's posts
    total_favorites = Favorite.objects.filter(blog__author=request.user).count()
    total_comments = Comment.objects.filter(blog__author=request.user).count()
    
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        # request.FILES is added here
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('blog:profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)
    
    context = {
        'u_form': u_form,
        'p_form': p_form,
        'user_posts': user_posts,
        'total_likes': total_likes,
        'total_dislikes': total_dislikes,
        'total_favorites': total_favorites,
        'total_comments': total_comments,
    }
    
    return render(request, 'blog/profile.html', context)


@login_required
def password_change(request: HttpRequest) -> HttpResponse:
    """
    View for a user to change their password.
    The user must be logged in to access this page.
    """
    if request.method == 'POST':
        # Create a form instance with the user and POST data.
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            # Save the new password.
            user = form.save()
            # This is essential to prevent the user from being logged out.
            update_session_auth_hash(request, user)
            # Display a success message.
            messages.success(request, 'Your password was successfully updated!')
            # Redirect to the user's profile page or another success page.
            return redirect('blog:profile')
        else:
            # If the form is not valid, show an error message.
            messages.error(request, 'Please correct the error below.')
    else:
        # For a GET request, create an empty form instance.
        form = PasswordChangeForm(request.user)

    context = {
        'form': form,
    }
    return render(request, 'blog/password_change.html', context)


def is_author_or_staff(user):
    """Custom function to check if the user is an author or staff."""
    return user.is_staff or (hasattr(user, 'profile') and user.profile.user_type == 'author')

@login_required
@user_passes_test(is_author_or_staff)
def blog_create(request: HttpRequest) -> HttpResponse:
    """
    Handles creating a new blog post.
    Only allows authors or staff members to create blogs.
    """
    if request.method == 'POST':
        # request.FILES is added here
        form = BlogForm(request.POST, request.FILES)
        if form.is_valid():
            blog = form.save(commit=False)
            blog.author = request.user
            blog.save()
            form.save_m2m() # Save ManyToMany relationships (categories)
            messages.success(request, 'Blog created successfully!')
            return redirect('blog:blog_detail', pk=blog.pk)
    else:
        form = BlogForm()
    
    return render(request, 'blog/blog_form.html', {'form': form, 'title': 'Create a Blog'})


@login_required
@author_or_staff_required
def blog_update(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Handles updating an existing blog post.
    Only allows the author or a staff member to update the blog.
    """
    blog = get_object_or_404(Blog, pk=pk)
    
    if request.method == 'POST':
        # request.FILES is added here
        form = BlogForm(request.POST, request.FILES, instance=blog)
        if form.is_valid():
            form.save()
            messages.success(request, 'Blog updated successfully!')
            return redirect('blog:blog_detail', pk=blog.pk)
    else:
        form = BlogForm(instance=blog)
    
    return render(request, 'blog/blog_form.html', {'form': form, 'title': 'Update Blog'})


@login_required
@author_or_staff_required
def blog_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Handles deleting a blog post.
    Only allows the author or a staff member to delete the blog.
    """
    blog = get_object_or_404(Blog, pk=pk)
    
    if request.method == 'POST':
        blog.delete()
        messages.success(request, 'Blog deleted successfully!')
        return redirect('blog:blog_list')
    
    return render(request, 'blog/blog_confirm_delete.html', {'blog': blog})


@login_required
def toggle_favorite(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Adds or removes a blog post from a user's favorites and sends an email notification.
    """
    blog = get_object_or_404(Blog, pk=pk)
    favorite, created = Favorite.objects.get_or_create(user=request.user, blog=blog)
    
    if not created:
        favorite.delete()
        messages.success(request, 'Removed from favorites.')
    else:
        messages.success(request, 'Added to favorites!')
        # Send an email to the user.
        try:
            send_mail(
                'New Favorite Added!',
                f'You have successfully added "{blog.title}" to your favorites.',
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send favorite email: {e}")
            messages.warning(request, 'Blog was added to favorites, but we could not send you an email confirmation.')
    
    return redirect('blog:blog_detail', pk=blog.pk)


@login_required
def favorite_list(request: HttpRequest) -> HttpResponse:
    """Displays a list of all blogs favorited by the logged-in user."""
    favorites = Favorite.objects.filter(user=request.user).order_by('-created_at')
    
    # Pagination - show 12 favorites per page
    paginator = Paginator(favorites, 12)
    page = request.GET.get('page')
    
    try:
        favorites = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        favorites = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results.
        favorites = paginator.page(paginator.num_pages)
    
    return render(request, 'blog/favorite_list.html', {'favorites': favorites})


# --- Contact Form Views ---

def contact(request: HttpRequest) -> HttpResponse:
    """
    Handles the submission of the contact form.
    Saves the message to the database and sends an email notification.
    """
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_message = form.save()
            
            try:
                send_mail(
                    f'New Contact Message from {contact_message.name}',
                    f"Name: {contact_message.name}\nEmail: {contact_message.email}\n\nMessage:\n{contact_message.message}",
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.CONTACT_EMAIL], # This email should be defined in your settings.py file.
                    fail_silently=False,
                )
                messages.success(request, 'Your message was sent successfully! We will get back to you shortly.')
                return redirect('blog:contact_success')
            except Exception as e:
                print(f"Failed to send contact email: {e}")
                messages.error(request, 'There was an error sending your message. Please try again later.')
        else:
            messages.error(request, 'Please correct the errors below.')
        
    else:
        form = ContactForm()
        
    return render(request, 'blog/contact.html', {'form': form})


def contact_success(request: HttpRequest) -> HttpResponse:
    """
    Renders a page to confirm the contact form was submitted successfully.
    """
    return render(request, 'blog/contact_success.html')


# --- Publish/Unpublish Views ---

@login_required
@author_or_staff_required
def publish_post(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Publishes a blog post (sets published=True).
    Only allows the author or a staff member to publish the blog.
    """
    blog = get_object_or_404(Blog, pk=pk)
    
    if request.method == 'POST':
        blog.published = True
        blog.save()
        messages.success(request, 'Blog published successfully!')
    
    return redirect('blog:blog_detail', pk=blog.pk)


@login_required
@author_or_staff_required
def unpublish_post(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Unpublishes a blog post (sets published=False).
    Only allows the author or a staff member to unpublish the blog.
    """
    blog = get_object_or_404(Blog, pk=pk)
    
    if request.method == 'POST':
        blog.published = False
        blog.save()
        messages.success(request, 'Blog unpublished successfully!')
    
    return redirect('blog:blog_detail', pk=blog.pk)


# --- Like/Dislike Views ---

@require_POST
@csrf_exempt
def like_dislike_post(request, pk):
    """
    Handles AJAX requests for liking and disliking blog posts.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=403)
    
    try:
        blog = Blog.objects.get(pk=pk)
    except Blog.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Blog post not found'}, status=404)
    
    # Get reaction type from request
    data = json.loads(request.body)
    reaction = data.get('reaction')
    
    if reaction == 'like':
        # Check if user already liked
        like_exists = Like.objects.filter(user=request.user, blog=blog).exists()
        dislike_exists = Dislike.objects.filter(user=request.user, blog=blog).exists()
        
        if like_exists:
            # Remove like if already exists
            Like.objects.filter(user=request.user, blog=blog).delete()
        else:
            # Add like and remove dislike if exists
            Like.objects.create(user=request.user, blog=blog)
            if dislike_exists:
                Dislike.objects.filter(user=request.user, blog=blog).delete()
        
    elif reaction == 'dislike':
        # Check if user already disliked
        dislike_exists = Dislike.objects.filter(user=request.user, blog=blog).exists()
        like_exists = Like.objects.filter(user=request.user, blog=blog).exists()
        
        if dislike_exists:
            # Remove dislike if already exists
            Dislike.objects.filter(user=request.user, blog=blog).delete()
        else:
            # Add dislike and remove like if exists
            Dislike.objects.create(user=request.user, blog=blog)
            if like_exists:
                Like.objects.filter(user=request.user, blog=blog).delete()
    
    # Get updated counts
    likes_count = blog.like_set.count()
    dislikes_count = blog.dislike_set.count()
    
    # Check user's current reaction
    user_reaction = None
    if Like.objects.filter(user=request.user, blog=blog).exists():
        user_reaction = 'like'
    elif Dislike.objects.filter(user=request.user, blog=blog).exists():
        user_reaction = 'dislike'
    
    return JsonResponse({
        'status': 'success',
        'likes_count': likes_count,
        'dislikes_count': dislikes_count,
        'user_reaction': user_reaction
    })