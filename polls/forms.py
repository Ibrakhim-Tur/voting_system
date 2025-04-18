from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Candidate
from django import forms, template
from .models import Election



class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']



class VoteForm(forms.Form):
    candidate = forms.ModelChoiceField(
        queryset=Candidate.objects.none(),
        widget=forms.RadioSelect,
        empty_label=None,
        label="Выберите кандидата"
    )

    def __init__(self, *args, **kwargs):
        election_id = kwargs.pop('election_id', None)
        super().__init__(*args, **kwargs)
        if election_id is not None:
            self.fields['candidate'].queryset = Candidate.objects.filter(election_id=election_id)


class ElectionForm(forms.ModelForm):
    class Meta:
        model = Election
        fields = ['title', 'description', 'start_date', 'end_date','is_public','visibility', 'invited_users'  ]


        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'invited_users': forms.CheckboxSelectMultiple
        }
        labels = {
            'title': 'Название голосования',
            'description': 'Описание',
        }
class ElectionForm(forms.ModelForm):
    invited_users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'size': '10'}),
        required=False,
        label="Пригласить пользователей"
    )

    class Meta:
        model = Election
        fields = ['title', 'description', 'visibility', 'invited_users']