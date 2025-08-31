# In your forms.py
# This file defines all the forms used in your web application.
# Forms are a way to collect user input, validate it, and process it.
# They are essential for creating a structured and secure interface.

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
# Added Comment model to imports
from .models import Profile, Blog, Rating, Category, ContactMessage, Favorite, Comment

class UserRegisterForm(UserCreationForm):
    """
    A form for user registration with email validation.
    The email field is set to required.
    """
    email = forms.EmailField(required=True)
    
    class Meta(UserCreationForm.Meta):
        """
        Meta class to configure the UserRegisterForm.
        We inherit from UserCreationForm.Meta to keep its built-in fields.
        We only need to explicitly add the 'email' field here.
        """
        model = User
        fields = ['username', 'email']
    
    def clean_email(self):
        """
        Custom validation to ensure the email is unique.
        """
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

class UserUpdateForm(forms.ModelForm):
    """
    A form for users to update their username, email, first name, and last name.
    """
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name'] # Corrected: added first_name and last_name to fix the CrispyError

class ProfileUpdateForm(forms.ModelForm):
    """
    A form for users to update their profile information.
    """
    class Meta:
        model = Profile
        # Updated fields to match the provided Profile model
        fields = ['user_type', 'bio', 'profile_picture', 'social_media']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

class BlogForm(forms.ModelForm):
    """
    A form for creating and updating blog posts.
    Uses CheckboxSelectMultiple for categories.
    """
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    class Meta:
        model = Blog
        # Updated fields to match the provided Blog model
        fields = ['title', 'content', 'featured_image', 'categories', 'published']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10}),
        }

class RatingForm(forms.ModelForm):
    """
    A form for users to rate a blog post.
    """
    RATING_CHOICES = [(i, i) for i in range(1, 6)]
    
    score = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.RadioSelect,
        label='Rate this blog'
    )
    
    class Meta:
        model = Rating
        fields = ['score']

# New form for the contact page
class ContactForm(forms.ModelForm):
    """
    A form for the contact page, based on the ContactMessage model.
    """
    class Meta:
        model = ContactMessage
        # Updated fields to match the provided ContactMessage model
        fields = ['name', 'email', 'message']

class FavoriteForm(forms.ModelForm):
    """
    A simple form to handle favoriting a blog post.
    """
    class Meta:
        model = Favorite
        fields = [] # No fields needed as the user and blog will be set in the view

# Form for comments, added to the file
class CommentForm(forms.ModelForm):
    """
    Form for users to submit a comment on a blog post.
    """
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Write your comment here...'}),
        }
        labels = {
            'content': '' # Hides the label for a cleaner look
        }
