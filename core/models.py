from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import random
import string

class Note(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='notes/') 
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Exam(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.CharField(max_length=200)
    date = models.DateTimeField()
    # NEW: Distinguish between manual missions and bulk datesheet imports
    is_datesheet_entry = models.BooleanField(default=False)
    # NEW: Store extra info like "Morning/Evening" or "3 SEM"
    details = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.subject} - {self.date}"

    def progress(self):
        total = self.topics.count()
        if total == 0: return 0
        completed = self.topics.filter(is_completed=True).count()
        return int((completed / total) * 100)

class Topic(models.Model):
    exam = models.ForeignKey(Exam, related_name='topics', on_delete=models.CASCADE)
    name = models.TextField() 
    is_completed = models.BooleanField(default=False)
    is_cho = models.BooleanField(default=False)
    source_note = models.ForeignKey(Note, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name[:50]

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    last_seen = models.DateTimeField(default=timezone.now)

    def is_online(self):
        return self.last_seen >= timezone.now() - timezone.timedelta(minutes=5)

    def __str__(self):
        return self.user.username
    
    
# core/models.py

# ... (Note and Exam models remain unchanged) ...

class Topic(models.Model):
    exam = models.ForeignKey(Exam, related_name='topics', on_delete=models.CASCADE)
    name = models.TextField() 
    is_completed = models.BooleanField(default=False)
    # NEW FIELD BELOW:
    completed_at = models.DateTimeField(null=True, blank=True) 
    is_cho = models.BooleanField(default=False)
    source_note = models.ForeignKey(Note, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name[:50]

# ... (Profile model remains unchanged) ...


# Helper to generate Invite Codes (e.g., "K9X-22")
def generate_squad_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=3)) + '-' + ''.join(random.choices(chars, k=2))

class Squad(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    code = models.CharField(max_length=10, default=generate_squad_code, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_squads')

    def __str__(self):
        return self.name

class Membership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    squad = models.ForeignKey(Squad, on_delete=models.CASCADE, related_name='members')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_leader = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'squad') # Prevents double joining

class Transmission(models.Model): # Chat Messages
    squad = models.ForeignKey(Squad, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender}: {self.content[:20]}"