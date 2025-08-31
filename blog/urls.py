# blog/urls.py
# This file maps the URL paths to the views in your web application.
# Each path() function connects a URL pattern to a specific view function.

from django.urls import path, reverse_lazy
from . import views
from django.contrib.auth import views as auth_views

app_name = 'blog'

urlpatterns = [
    # --- General Blog Views ---
    path('', views.home, name='home'),
    path('blogs/', views.blog_list, name='blog_list'),
    path('blog/<int:pk>/', views.blog_detail, name='blog_detail'),
    path('authors/', views.author_list, name='author_list'),
    path('author/<int:pk>/', views.author_detail, name='author_detail'),
    path('contact/', views.contact, name='contact'),
    path('contact/success/', views.contact_success, name='contact_success'),
    
    # --- Authentication Views ---
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('password-change/', views.password_change, name='password_change'),
    path('verify-email/<uuid:token>/', views.verify_email, name='verify_email'),
    path('verify-email-sent/', views.verify_email_sent_view, name='verify_email_sent'),

    # --- Blog Management Views (Logged-in users) ---
    path('blog/create/', views.blog_create, name='blog_create'),
    path('blog/<int:pk>/update/', views.blog_update, name='blog_update'),
    path('blog/<int:pk>/delete/', views.blog_delete, name='blog_delete'),
    path('blog/<int:pk>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('favorites/', views.favorite_list, name='favorite_list'),

    # --- Publish/Unpublish Views ---
    path('blog/<int:pk>/publish/', views.publish_post, name='publish_post'),
    path('blog/<int:pk>/unpublish/', views.unpublish_post, name='unpublish_post'),
    path('blog/<int:pk>/like-dislike/', views.like_dislike_post, name='like_dislike_post'),

    # --- Password Reset (Built-in Django Views) ---
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='blog/password_reset_form.html',
             email_template_name='blog/password_reset_email.html',
             html_email_template_name='blog/password_reset_email.html',
             success_url=reverse_lazy('blog:password_reset_done')
         ), 
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='blog/password_reset_done.html'),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='blog/password_reset_confirm.html',
             success_url=reverse_lazy('blog:password_reset_complete')
         ),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(template_name='blog/password_reset_complete.html'),
         name='password_reset_complete'),
]