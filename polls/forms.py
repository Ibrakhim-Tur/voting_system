from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class RegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
from .models import Election, Candidate

class VoteForm(forms.Form):
    candidate = forms.ModelChoiceField(
        queryset=Candidate.objects.none(),
        widget=forms.RadioSelect
    )

    def __init__(self, *args, **kwargs):
        election_id = kwargs.pop('election_id')
        super().__init__(*args, **kwargs)
        self.fields['candidate'].queryset = Candidate.objects.filter(election_id=election_id)