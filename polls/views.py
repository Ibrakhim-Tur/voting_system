from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q, Case, When, BooleanField
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib.auth.models import User
from .utils import update_user_achievement_progress


from django.urls import reverse
from .utils import generate_qr_code

import logging
import string
import random

from .models import Election, Candidate, Vote, ElectionOption as Option,UserAchievement,Achievement
from .forms import RegisterForm, VoteForm, CandidateForm, ElectionForm

logger = logging.getLogger(__name__)
@login_required
def home(request):
    now = timezone.now()

    if request.user.is_authenticated:
        election_list = Election.objects.filter(
            is_public=True,
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).order_by('-start_date').prefetch_related('options', 'candidates')
    else:
        election_list = Election.objects.filter(
            is_public=True,
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).order_by('-start_date').prefetch_related('options')

    paginator = Paginator(election_list, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    for election in page_obj:
        vote_url = request.build_absolute_uri(reverse('vote', args=[election.id]))
        election.qr_code = generate_qr_code(vote_url)

    # Топ 10 пользователей по количеству голосов
    top_users = User.objects.annotate(vote_count=Count('votes')).order_by('-vote_count')[:10]

    return render(request, 'polls/home.html', {
        'page_obj': page_obj,
        'top_users': top_users
    })
def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'polls/register.html', {'form': form})


@login_required
def vote(request, election_id=None, unique_link=None):
    # Получаем выборы по id или по уникальной ссылке
    if unique_link:
        election = get_object_or_404(Election, unique_link=unique_link)
    else:
        election = get_object_or_404(Election, id=election_id)

    # Проверяем видимость голосования
    if election.visibility == 'private':
        if request.user != election.creator and request.user not in election.invited_users.all():
            return HttpResponseForbidden("Это приватное голосование. У вас нет доступа.")

    # Проверяем, завершено ли голосование
    if not election.is_currently_active:
        messages.error(request, "Это голосование уже завершено.")
        return redirect('home')

    # Проверяем, голосовал ли пользователь уже
    if Vote.objects.filter(user=request.user, election=election).exists():
        messages.warning(request, "Вы уже голосовали в этом опросе.")
        return redirect('results', election_id=election.id)

    # Обрабатываем форму голосования
    if request.method == 'POST':
        form = VoteForm(request.POST, election_id=election.id)
        if form.is_valid():
            candidate = form.cleaned_data['candidate']
            # Создаем новый голос
            vote = Vote.objects.create(user=request.user, election=election, candidate=candidate)

            # Обновляем прогресс достижений
            achievements = Achievement.objects.all()  # Получаем все достижения
            for achievement in achievements:
                update_user_achievement_progress(request.user, achievement)  # Обновляем прогресс пользователя

            messages.success(request, "Ваш голос учтен!")
            return redirect('results', election_id=election.id)
    else:
        form = VoteForm(election_id=election.id)

    return render(request, 'polls/vote.html', {'form': form, 'election': election})

def results(request, election_id):
    election = get_object_or_404(Election, id=election_id)
    candidates = Candidate.objects.filter(election=election).annotate(
        total_votes=Count('votes')
    )
    return render(request, 'polls/results.html', {
        'election': election,
        'candidates': candidates
    })

@login_required
def profile(request):
    user_votes = Vote.objects.filter(
        user=request.user
    ).select_related('election', 'candidate').order_by('-voted_at')

    user_votes = user_votes.annotate(
        is_election_active=Case(
            When(
                election__start_date__lte=timezone.now(),
                election__end_date__gte=timezone.now(),
                election__is_active=True,
                then=True
            ),
            default=False,
            output_field=BooleanField()
        )
    )

    # Все достижения
    all_achievements = Achievement.objects.all()
    user_achievements = {
        ua.achievement.id: ua for ua in UserAchievement.objects.filter(user=request.user)
    }

    # Подготовка достижений с прогрессом
    achievements_data = []
    for achievement in all_achievements:
        user_ach = user_achievements.get(achievement.id)

        if user_ach:
            # Проверка, что goal не равен 0 перед расчетом прогресса
            if achievement.goal > 0:
                progress = (user_ach.votes_completed / achievement.goal) * 100
                percent = min(100, int(progress))
            else:
                progress = 0
                percent = 0  # Если goal = 0, то прогресс равен 0
            achieved = user_ach.achieved
        else:
            progress = 0
            percent = 0
            achieved = False

        achievements_data.append({
            'name': achievement.name,
            'description': achievement.description,
            'icon': achievement.icon,  # Добавление иконки достижения, если нужно
            'goal': achievement.goal,
            'progress': progress,
            'achieved': achieved,
            'percent': percent
        })

    return render(request, 'polls/profile.html', {
        'user': request.user,
        'user_votes': user_votes,
        'total_votes': user_votes.count(),
        'user_achievements': achievements_data  # Передаем подготовленные данные о достижениях
    })

def index(request):
    elections = Election.objects.all()
    return render(request, 'polls/index.html', {'elections': elections})

def election_results(request, election_id):
    election = Election.objects.get(id=election_id)
    candidates = election.candidate_set.all()
    candidates_names = [c.name for c in candidates]
    votes_count = [c.votes for c in candidates]

    return render(request, 'election_results.html', {
        'election': election,
        'candidates_names': candidates_names,
        'votes_count': votes_count,
    })

@login_required
def profile_view(request):
    return render(request, 'polls/profile.html')

@login_required
def create_election(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        visibility = request.POST.get('visibility', 'public')
        start_date = timezone.now()
        end_date = timezone.now() + timezone.timedelta(days=3)
        unique_link = generate_unique_link()

        election = Election.objects.create(
            title=title,
            description=description,
            creator=request.user,
            start_date=start_date,
            end_date=end_date,
            visibility=visibility,
            is_public=(visibility == 'public'),
            unique_link=unique_link
        )

        invited_user_ids = request.POST.getlist('invited_users')
        if invited_user_ids:
            invited_users = User.objects.filter(id__in=invited_user_ids)
            election.invited_users.set(invited_users)

        for key, value in request.POST.items():
            if key.startswith('option') and value.strip():
                Candidate.objects.create(
                    election=election,
                    name=value.strip()
                )

        messages.success(request, 'Голосование успешно создано!')
        return redirect('home')

    users = User.objects.exclude(id=request.user.id)
    return render(request, 'polls/create_election.html', {'users': users})

@login_required
def election_list(request):
    now = timezone.now()
    elections = Election.objects.filter(
        Q(is_public=True) |
        Q(invited_users=request.user) |
        Q(creator=request.user),
        start_date__lte=now,
        end_date__gte=now,
        is_active=True
    ).distinct().order_by('-start_date')

    return render(request, 'polls/election_list.html', {'elections': elections})

def generate_unique_link(length=10):
    while True:
        link = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
        if not Election.objects.filter(unique_link=link).exists():
            return link

@login_required
def manage_election(request, election_id):
    election = get_object_or_404(Election, id=election_id)


    # Проверка прав доступа: только создатель или суперпользователь
    if request.user != election.creator and not request.user.is_superuser:
        return HttpResponseForbidden()

    return render(request, 'polls/manage_election.html', {'election': election})

@login_required
def delete_election(request, election_id):
    election = get_object_or_404(Election, pk=election_id)

    # Проверка прав доступа: только создатель или суперпользователь
    if request.user != election.creator and not request.user.is_superuser:
        return HttpResponseForbidden()

    if request.method == 'POST':
        election.delete()
        messages.success(request, 'Голосование успешно удалено.')
        return redirect('home')

    return redirect('delete_election', election_id=election_id)

@login_required
def add_candidate(request, election_id):
    election = get_object_or_404(Election, pk=election_id)

    # Проверка прав доступа: только создатель или суперпользователь
    if request.user != election.creator and not request.user.is_superuser:
        return HttpResponseForbidden()

    if request.method == "POST":
        form = CandidateForm(request.POST)
        if form.is_valid():
            candidate = form.save(commit=False)
            candidate.election = election
            candidate.save()
            messages.success(request, 'Кандидат успешно добавлен.')
            return redirect('edit_election', election_id=election.id)
        else:
            messages.error(request, 'Ошибка при добавлении кандидата. Пожалуйста, проверьте форму.')
    else:
        form = CandidateForm()

    return render(request, 'polls/add_candidate.html', {
        'form': form,
        'election': election
    })

@login_required
def delete_candidate(request, election_id, candidate_id):
    election = get_object_or_404(Election, id=election_id)

    # Убедимся, что текущий пользователь — создатель голосования
    if request.user != election.creator:
        return redirect('home')  # или верни ошибку доступа

    candidate = get_object_or_404(Candidate, id=candidate_id, election=election)
    candidate.delete()
    return redirect('edit_election', election_id=election.id)
@login_required
def edit_election(request, election_id):
    election = get_object_or_404(Election, pk=election_id)

    # Проверка на создателя
    if request.user != election.creator and not request.user.is_superuser:
        messages.error(request, "Вы не можете редактировать это голосование.")
        return redirect('home')

    candidates = Candidate.objects.filter(election=election)
    users = User.objects.exclude(id=request.user.id)  # не показываем самого себя

    if request.method == 'POST':
        form = ElectionForm(request.POST, instance=election)
        if form.is_valid():
            form.save()

            # Добавление новых пользователей
            invited_users_add = request.POST.getlist('invited_users_add')
            for user_id in invited_users_add:
                try:
                    user = User.objects.get(pk=user_id)
                    election.invited_users.add(user)
                except User.DoesNotExist:
                    pass

            # Удаление приглашённых
            invited_users_remove = request.POST.getlist('invited_users_remove')
            for user_id in invited_users_remove:
                try:
                    user = User.objects.get(pk=user_id)
                    election.invited_users.remove(user)
                except User.DoesNotExist:
                    pass

            messages.success(request, "Изменения сохранены.")
            return redirect('manage_election', election.id)
    else:
        form = ElectionForm(instance=election)

    context = {
        'election': election,
        'form': form,
        'candidates': candidates,
        'users': users,
    }
    return render(request, 'polls/edit_election.html', context)

@login_required
def my_private_elections(request):
    now = timezone.now()

    elections = Election.objects.filter(
        is_public=False,
        is_active=True,
        start_date__lte=now,
        end_date__gte=now
    ).filter(
        Q(creator=request.user) | Q(invited_users=request.user)
    ).distinct().order_by('-start_date').prefetch_related('options', 'candidates')

    paginator = Paginator(elections, 6)  # Ограничение 6 голосования на страницу
    page_number = request.GET.get('page')
    elections_page = paginator.get_page(page_number)

    for election in elections_page:
        vote_url = request.build_absolute_uri(reverse('vote', args=[election.id]))
        election.qr_code = generate_qr_code(vote_url)

    return render(request, 'polls/my_private_elections.html', {'elections': elections_page})

def achievements_page(request):
    achievements = Achievement.objects.all()
    user_achievements_qs = UserAchievement.objects.filter(user=request.user).select_related('achievement')

    # Мапа от achievement.id к UserAchievement объекту
    user_achievements_map = {ua.achievement.id: ua for ua in user_achievements_qs}

    # Преобразуем данные о достижениях для пользователя
    user_achievements_data = []
    for achievement in achievements:
        user_achievement = user_achievements_map.get(achievement.id)

        if user_achievement:
            user_achievements_data.append({
                'achievement': achievement,
                'remaining_votes': user_achievement.remaining_votes,
                'progress_percentage': user_achievement.progress_percentage,
                'achieved': user_achievement.achieved,
            })
        else:
            user_achievements_data.append({
                'achievement': achievement,
                'remaining_votes': achievement.total_votes_required,
                'progress_percentage': 0,
                'achieved': False,
            })

    print(user_achievements_data)  # Выведет в консоль данные для отладки

    context = {
        'user_achievements_data': user_achievements_data,
    }

    return render(request, 'polls/achievements.html', context)
def user_search(request):
    query = request.GET.get('q', '')  # Получаем поисковый запрос
    users = User.objects.all()

    if query:
        users = users.filter(username__icontains=query)  # Ищем пользователей по имени, игнорируя регистр

    return render(request, 'polls/user_search_results.html', {'users': users, 'query': query})
@login_required
def user_profile(request, user_id):
    profile_user = get_object_or_404(User, id=user_id)

    # Получаем достижения через промежуточную модель
    user_achievements = UserAchievement.objects.filter(user=profile_user).select_related('achievement')

    # Голосования, созданные этим пользователем
    elections_created = Election.objects.filter(creator=profile_user)

    context = {
        'profile_user': profile_user,
        'achievements': [ua.achievement for ua in user_achievements],
        'elections_created': elections_created,
    }
    return render(request, 'polls/user_profile.html', context)