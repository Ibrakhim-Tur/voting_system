from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q, Case, When, BooleanField
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib.auth.models import User

import logging
import string
import random

from .models import Election, Candidate, Vote, ElectionOption as Option
from .forms import RegisterForm, VoteForm, CandidateForm, ElectionForm

logger = logging.getLogger(__name__)

def home(request):
    now = timezone.now()


    if request.user.is_authenticated:
        election_list = Election.objects.filter(
            Q(is_public=True) |
            Q(invited_users=request.user) |
            Q(creator=request.user)
        ).filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).distinct().order_by('-start_date').prefetch_related('options', 'candidates')
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
    user_votes = Vote.objects.filter(
        user=request.user
    ).select_related(
        'election',
        'candidate'
    ).order_by('-voted_at')

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

    return render(request, 'polls/profile.html', {
        'user': request.user,
        'user_votes': user_votes,
        'total_votes': user_votes.count()
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

    return render(request, 'polls/my_private_elections.html', {'elections': elections})

