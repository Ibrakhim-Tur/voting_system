# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class Election(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

class Candidate(models.Model):
    name = models.CharField(max_length=100)
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    votes = models.IntegerField(default=0)

    def __str__(self):
        return self.name

class Vote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'election')]  # 1 голос от пользователя