from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinLengthValidator, FileExtensionValidator



import uuid
from django.utils.text import slugify



from django.utils.crypto import get_random_string





class Election(models.Model):
    VISIBILITY_CHOICES = [
        ('public', 'Публичное'),
        ('private', 'Приватное'),
    ]

    title = models.CharField(max_length=200, verbose_name="Название голосования")
    description = models.TextField(verbose_name="Описание", blank=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Создатель", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateTimeField(verbose_name="Дата начала")
    end_date = models.DateTimeField(verbose_name="Дата окончания")
    is_active = models.BooleanField(default=True, verbose_name="Активно")
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='public', verbose_name="Видимость")
    is_public = models.BooleanField(default=True)
    invited_users = models.ManyToManyField(User, related_name='invited_elections', blank=True,
                                           verbose_name="Приглашенные пользователи")

    unique_link = models.CharField(max_length=50, unique=True, blank=True, verbose_name="Уникальная ссылка")

    def save(self, *args, **kwargs):
        if not self.unique_link and self.visibility == 'private':
            self.unique_link = get_random_string(length=50)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def is_currently_active(self):
        now = timezone.now()
        return self.start_date <= now <= self.end_date and self.is_active

    @property
    def total_votes(self):
        return self.votes.count()  # Убедись, что в модели Vote есть related_name='votes'


class Candidate(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name='Имя кандидата'
    )
    election = models.ForeignKey(
        Election,
        on_delete=models.CASCADE,
        related_name='candidates',
        verbose_name='Выборы'
    )
    bio = models.TextField(
        verbose_name='Биография',
        blank=True
    )
    photo = models.ImageField(
        upload_to='candidates/',
        null=True,
        blank=True,
        verbose_name='Фотография'
    )

    class Meta:
        verbose_name = 'Кандидат'
        verbose_name_plural = 'Кандидаты'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.election.title})"

    @property
    def vote_count(self):
        return self.votes.count()


class Vote(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='votes',
        verbose_name='Пользователь'
    )
    election = models.ForeignKey(
        Election,
        on_delete=models.CASCADE,
        related_name='votes',
        verbose_name='Выборы'
    )
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name='votes',
        verbose_name='Кандидат'
    )
    voted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Время голосования'
    )
    class Meta:
        verbose_name = 'Голос'
        verbose_name_plural = 'Голоса'
        ordering = ['-voted_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'election'],
                name='unique_user_election_vote'
            )
        ]


    def __str__(self):
        return f"{self.user.username} → {self.candidate.name} ({self.election.title})"


class ElectionOption(models.Model):
    election = models.ForeignKey(
        Election,
        on_delete=models.CASCADE,
        related_name='options',
        verbose_name='Выборы'
    )
    text = models.CharField(
        max_length=200,
        verbose_name='Текст варианта'
    )
    description = models.TextField(
        verbose_name='Описание',
        blank=True
    )
    photo = models.ImageField(
        upload_to='candidates/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
        null=True,
        blank=True,
        verbose_name='Фото'
    )



    class Meta:
        verbose_name = 'Вариант выборов'
        verbose_name_plural = 'Варианты выборов'

    def __str__(self):
        return f"{self.text} ({self.election.title})"

creator = models.ForeignKey(
    User,
    on_delete=models.CASCADE,
    verbose_name="Создатель",
    null=True,  # временно разрешаем null
    blank=True
)

class Achievement(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    required_votes = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)  # автоматическая установка при создании
    total_votes_required = models.PositiveIntegerField(help_text="Количество голосований, которые необходимо пройти для достижения")
    goal = models.PositiveIntegerField(default=0, help_text="Цель для достижения")  # Новый атрибут
    icon = models.ImageField(upload_to='achievement_icons/', blank=True, null=True)  # Добавление поля icon

    def __str__(self):
        return self.name


class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    votes_completed = models.PositiveIntegerField(default=0)  # Количество голосований, которые пользователь уже прошел
    achieved = models.BooleanField(default=False)

    @property
    def remaining_votes(self):
        """Вычисляем, сколько голосований осталось до выполнения достижения."""
        if not self.achieved:
            remaining = self.achievement.total_votes_required - self.votes_completed
            return remaining if remaining > 0 else 0  # Возвращаем 0, если голосований не осталось
        return 0

    @property
    def progress_percentage(self):
        """Вычисляем прогресс в процентах."""
        if self.achievement.total_votes_required > 0:
            progress = (self.votes_completed / self.achievement.total_votes_required) * 100
            return min(progress, 100)  # Ограничиваем прогресс 100%
        return 0