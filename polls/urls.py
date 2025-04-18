from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required

urlpatterns = [
    # Главная страница — список публичных голосований
    path('', views.home, name='home'),

    path('', views.home, name='election_list'),  # или name='home'
    path('manage/<int:election_id>/', views.manage_election, name='manage_election'),
    path('election/<int:election_id>/add-candidate/', views.add_candidate, name='add_candidate'),# urls.py
    path('election/<int:election_id>/delete/', views.delete_election, name='delete_election'),


    # Альтернативная домашняя страница (только активные)
    path('home/', views.home, name='home'),

    # Регистрация и профиль
    path('register/', views.register, name='register'),
    path('profile/', login_required(views.profile), name='profile'),

    # Создание голосования
    path('create/', login_required(views.create_election), name='create_election'),

    # Голосование и результаты
    path('elections/<int:election_id>/vote/', views.vote, name='vote'),
    path('elections/<int:election_id>/results/', views.results, name='results'),

    # Приватное голосование
    path('invite/<str:unique_link>/', login_required(views.vote), name='vote_by_invite'),
    path('manage/<int:election_id>/', views.manage_election, name='manage_election'),
    path('manage/<int:election_id>/delete/', views.delete_election, name='delete_election'),
    path('manage/<int:election_id>/candidate/add/', views.add_candidate, name='add_candidate'),
    path('manage/<int:election_id>/candidate/<int:candidate_id>/delete/', views.delete_candidate,
         name='delete_candidate'),
    path('manage/<int:election_id>/edit/', views.edit_election, name='edit_election'),
    path('my-private/', views.my_private_elections, name='my_private_elections'),
]