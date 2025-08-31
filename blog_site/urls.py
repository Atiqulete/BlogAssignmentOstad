from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # This line includes the URLs from the blog app.
    # The 'home/' URL from blog.urls will be accessible at the root level.
    path('', include('blog.urls')),
    path('admin/', admin.site.urls),

]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)