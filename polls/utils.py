# polls/utils.py

import qrcode
from io import BytesIO
import base64
from .models import Achievement, UserAchievement
from django.db.models import F
from django import template




def generate_qr_code(data):
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=5
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_str}"


def assign_achievement(user, action_type):
    # Проверяем, нужно ли присваивать достижение в зависимости от действия
    if action_type == 'vote':  # голосование
        achievement = Achievement.objects.get(name='Первый голос')  # например, за первое голосование
        UserAchievement.objects.get_or_create(user=user, achievement=achievement)

    elif action_type == 'create_election':  # создание нового голосования
        achievement = Achievement.objects.get(name='Создатель голосований')  # за создание голосования
        UserAchievement.objects.get_or_create(user=user, achievement=achievement)


def update_user_achievement_progress(user, achievement):
    # Получаем достижение пользователя для данного достижения
    user_achievement, created = UserAchievement.objects.get_or_create(user=user, achievement=achievement)

    # Обновляем количество голосований, которые уже прошел пользователь
    user_achievement.votes_completed += 1

    # Если количество голосований равно или больше, чем нужно для достижения - устанавливаем флаг достижения
    if user_achievement.votes_completed >= achievement.total_votes_required:
        user_achievement.achieved = True

    # Сохраняем обновленную информацию
    user_achievement.save()