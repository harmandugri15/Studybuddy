# studybuddy/studyvault/core/middleware.py

from django.utils import timezone
from .models import Profile

class UpdateLastSeenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Update last_seen timestamp
            Profile.objects.update_or_create(
                user=request.user,
                defaults={'last_seen': timezone.now()}
            )
        
        response = self.get_response(request)
        return response