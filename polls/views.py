from django.shortcuts import render
from .models import Election

def home(request):
    elections = Election.objects.filter(is_active=True)
    return render(request, 'polls/home.html', {'elections': elections})