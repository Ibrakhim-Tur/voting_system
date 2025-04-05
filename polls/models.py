from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinLengthValidator
from django.core.validators import FileExtensionValidator

class Election(models.Model):
    title = models.CharField(
        max_length=200,
        validators=[MinLengthValidator(5)],
        verbose_name='Название выборов'
    )
    description = models.TextField(
        verbose_name='Описание',
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    start_date = models.DateTimeField(
        verbose_name='Дата начала'
    )
    end_date = models.DateTimeField(
        verbose_name='Дата окончания'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активно'
    )

    class Meta:
        verbose_name = 'Выборы'
        verbose_name_plural = 'Выборы'
        ordering = ['-start_date']

    def __str__(self):
        return self.title

    @property
    def is_currently_active(self):
        """Проверяет, активны ли выборы в данный момент"""
        now = timezone.now()
        return self.start_date <= now <= self.end_date and self.is_active


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
        """Количество голосов за кандидата"""
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
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'election'],
                name='unique_user_election_vote'
            )
        ]
        ordering = ['-voted_at']

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

    class Meta:
        verbose_name = 'Вариант выборов'
        verbose_name_plural = 'Варианты выборов'

    def __str__(self):
        return f"{self.text} ({self.election.title})"

    photo = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Ссылка на фото'
    )
    photo = models.ImageField(
        upload_to='candidates/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
        null=True,
        blank=True
    )