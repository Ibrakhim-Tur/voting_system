from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse,JsonResponse
from django.contrib import messages
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from .models import Election, Candidate, Vote,User
from .forms import RegisterForm, VoteForm
from .forms import ElectionForm
from .models import ElectionOption as Option
from django.utils import timezone
from django.db import models
import logging
from django.shortcuts import render, redirect
from .forms import ElectionForm
from .models import Election
from django.http import HttpResponseForbidden
logger = logging.getLogger(__name__)
from .models import Election, ElectionOption
import string
import random

from django.contrib.auth.models import User


def home(request):
    now = timezone.now()
    election_list = Election.objects.filter(
        is_public=True,
        is_active=True,
        start_date__lte=now,
        end_date__gte=now
    ).order_by('-start_date').prefetch_related('candidates')

    paginator = Paginator(election_list, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'polls/home.html', {'page_obj': page_obj})


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
    if unique_link:
        election = get_object_or_404(Election, unique_link=unique_link)
    else:
        election = get_object_or_404(Election, id=election_id)

    if election.visibility == 'private':
        if request.user != election.creator and request.user not in election.invited_users.all():
            return HttpResponseForbidden("Это приватное голосование. У вас нет доступа.")

    if not election.is_currently_active:
        messages.error(request, "Это голосование уже завершено.")
        return redirect('home')

    if Vote.objects.filter(user=request.user, election=election).exists():
        messages.warning(request, "Вы уже голосовали в этом опросе.")
        return redirect('results', election_id=election.id)

    if request.method == 'POST':
        form = VoteForm(request.POST, election_id=election.id)
        if form.is_valid():
            candidate = form.cleaned_data['candidate']
            Vote.objects.create(user=request.user, election=election, candidate=candidate)
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
    # Получаем голоса пользователя с предзагрузкой связанных данных
    user_votes = Vote.objects.filter(
        user=request.user
    ).select_related(
        'election',
        'candidate'
    ).order_by('-voted_at')  # Сортировка по дате (новые сначала)

    # Добавляем аннотацию для проверки активности голосований
    user_votes = user_votes.annotate(
        is_election_active=models.Case(
            models.When(
                election__start_date__lte=timezone.now(),
                election__end_date__gte=timezone.now(),
                election__is_active=True,
                then=True
            ),
            default=False,
            output_field=models.BooleanField()
        )
    )

    return render(request, 'polls/profile.html', {
        'user': request.user,
        'user_votes': user_votes,
        'total_votes': user_votes.count()  # Добавляем общее количество голосов
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

        # ✅ Обработка invited_users (несколько)
        invited_user_ids = request.POST.getlist('invited_users')
        if invited_user_ids:
            invited_users = User.objects.filter(id__in=invited_user_ids)
            election.invited_users.set(invited_users)  # ManyToMany связь

        # Варианты ответа
        for key in request.POST:
            if key.startswith('option') and request.POST[key].strip():
                ElectionOption.objects.create(
                    election=election,
                    text=request.POST[key].strip()
                )

        messages.success(request, 'Голосование успешно создано!')
        return redirect('home')

    users = User.objects.exclude(id=request.user.id)  # опционально, исключаем себя
    return render(request, 'polls/create_election.html', {'users': users})

def election_list(request):
    now = timezone.now()
    elections = Election.objects.filter(
        is_public=True,
        start_date__lte=now,
        end_date__gte=now,
        is_active=True
    ).order_by('-start_date')
    return render(request, 'polls/election_list.html', {'elections': elections})


def generate_unique_link(length=10):
    while True:
        link = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
        if not Election.objects.filter(unique_link=link).exists():
            return link




@login_required
def manage_election(request, election_id):
    election = get_object_or_404(Election, id=election_id)

    if request.user != election.creator and not request.user.is_superuser:
        return render(request, '403.html')  # или HttpResponseForbidden()

    return render(request, 'polls/manage_election.html', {'election': election})
def add_candidate(request, election_id):
    election = get_object_or_404(Election, id=election_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Candidate.objects.create(name=name, election=election)
            return redirect('manage_election', election_id=election.id)

    return render(request, 'polls/add_candidate.html', {'election': election})
@login_required
def delete_election(request, election_id):
    election = get_object_or_404(Election, pk=election_id)
    if request.user != election.creator and not request.user.is_superuser:
        return HttpResponseForbidden()

    if request.method == 'POST':
        election.delete()
        return redirect('home')  # или другой URL после удаления

    return redirect('manage_election', election_id)
def manage_election(request, election_id):
    election = get_object_or_404(Election, pk=election_id)
    return render(request, 'polls/manage_election.html', {'election': election})


def add_candidate(request, election_id):
    if request.method == 'POST':
        election = get_object_or_404(Election, pk=election_id)
        name = request.POST.get('name')
        if name:
            Candidate.objects.create(election=election, name=name)
            messages.success(request, 'Кандидат успешно добавлен')
        return redirect('manage_election', election_id=election_id)

def delete_candidate(request, election_id, candidate_id):
    if request.method == 'POST':
        candidate = get_object_or_404(Candidate, pk=candidate_id, election_id=election_id)
        candidate.delete()
        messages.success(request, 'Кандидат успешно удален')
        return redirect('manage_election', election_id=election_id)

def edit_election(request, election_id):
    election = get_object_or_404(Election, pk=election_id)
    # Реализуйте логику редактирования
    return redirect('manage_election', election_id=election_id)