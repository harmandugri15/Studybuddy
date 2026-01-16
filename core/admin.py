from django.contrib import admin
from .models import Note, Exam, Profile

# This makes your models visible in the Admin Panel
admin.site.register(Note)
admin.site.register(Exam)
admin.site.register(Profile)