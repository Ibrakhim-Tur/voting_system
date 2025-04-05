def vote(request, election_id):
    election = get_object_or_404(Election, id=election_id)
    if Vote.objects.filter(user=request.user, election=election).exists():
        return HttpResponse("Вы уже голосовали в этом опросе!", status=400)
from django.shortcuts import render
from .models import Election

def home(request):
    elections = Election.objects.filter(is_active=True)
    return render(request, 'polls/home.html', {'elections': elections})
from .forms import RegisterForm

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'polls/register.html', {'form': form})
from .forms import VoteForm

def vote(request, election_id):
    election = get_object_or_404(Election, id=election_id)
    if request.method == 'POST':
        form = VoteForm(request.POST, election_id=election_id)
        if form.is_valid():
            candidate = form.cleaned_data['candidate']
            Vote.objects.create(
                user=request.user,
                election=election,
                candidate=candidate
            )
            return redirect('results', election_id=election.id)
    else:
        form = VoteForm(election_id=election_id)
    return render(request, 'polls/vote.html', {'form': form, 'election': election})
from django.db.models import Count

def results(request, election_id):
    election = get_object_or_404(Election, id=election_id)
    candidates = Candidate.objects.filter(election=election).annotate(
        total_votes=Count('vote')
    )
    return render(request, 'polls/results.html', {
        'election': election,
        'candidates': candidates
    })
from django.shortcuts import render
from .models import Election
from django.shortcuts import render
from .models import Election
from django.contrib import messages


def home(request):
    elections = Election.objects.filter(is_active=True).prefetch_related('candidate_set')

    if not elections.exists():
        messages.info(request, "Сейчас нет активных голосований. Возвращайтесь позже!")

    return render(request, 'polls/home.html', {
        'elections': elections
    })