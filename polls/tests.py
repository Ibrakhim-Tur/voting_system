from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Election, Candidate, Vote
from django.utils import timezone
from datetime import timedelta

class VoteTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', password='pass')
        self.election = Election.objects.create(
            title="Test Election",
            description="Test Description",
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=1),
            is_active=True
        )
        self.candidate = Candidate.objects.create(name="Test Candidate", election=self.election)

    def test_single_vote(self):
        self.client.login(username='testuser', password='pass')

        # Первый голос
        response = self.client.post(reverse('vote', args=[self.election.id]), {
            'candidate': self.candidate.id
        })
        self.assertEqual(response.status_code, 302)  # редирект на страницу результатов
        self.assertEqual(Vote.objects.count(), 1)

        # Повторный голос
        response = self.client.post(reverse('vote', args=[self.election.id]), {
            'candidate': self.candidate.id
        })
        self.assertEqual(Vote.objects.count(), 1)
        self.assertEqual(response.status_code, 400)


class UserDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.election = Election.objects.create(title="Test Election")

    def test_dashboard_access(self):
        self.client.login(username='testuser', password='12345')
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)