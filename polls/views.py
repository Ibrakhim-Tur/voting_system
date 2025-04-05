from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse,JsonResponse
from django.contrib import messages
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from .models import Election, Candidate, Vote
from .forms import RegisterForm, VoteForm
from .forms import ElectionForm
from .models import ElectionOption as Option


def home(request):
    election_list = Election.objects.filter(is_active=True).order_by('-start_date').prefetch_related('candidate_set')

    if not election_list.exists():
        messages.info(request, "Сейчас нет активных голосований. Возвращайтесь позже!")

    paginator = Paginator(election_list, 5)  # пагинация: 3 выборов на странице
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
def vote(request, election_id):
    election = get_object_or_404(Election, id=election_id)

    if Vote.objects.filter(user=request.user, election=election).exists():
        return HttpResponse("Вы уже голосовали в этом опросе!", status=400)

    if request.method == 'POST':
        form = VoteForm(request.POST, election_id=election_id)
        if form.is_valid():
            candidate = form.cleaned_data['candidate']
            Vote.objects.create(
                user=request.user,
                election=election,
                candidate=candidate
            )


            send_mail(
                'Ваш голос учтен',
                f'Вы успешно проголосовали в голосовании "{election.title}".\n\n'
                f'Выбранный кандидат: {candidate.name}',
                'noreply@ваш_сайт.ru',
                [request.user.email],
                fail_silently=False,
            )

            return redirect('results', election_id=election.id)
    else:
        form = VoteForm(election_id=election_id)

    return render(request, 'polls/vote.html', {'form': form, 'election': election})


def results(request, election_id):
    election = get_object_or_404(Election, id=election_id)
    candidates = Candidate.objects.filter(election=election).annotate(
        total_votes=Count('vote')
    )
    return render(request, 'polls/results.html', {
        'election': election,
        'candidates': candidates
    })
@login_required
def profile(request):
    user_votes = Vote.objects.filter(user=request.user).select_related('election', 'candidate')
    return render(request, 'polls/profile.html', {'user_votes': user_votes})



def create_election(request):
    if request.method == 'POST':
        form = ElectionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('index')
    else:
        form = ElectionForm()
    return render(request, 'polls/create_election.html', {'form': form})
from django.shortcuts import render, redirect
from .forms import ElectionForm
from .models import Election

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