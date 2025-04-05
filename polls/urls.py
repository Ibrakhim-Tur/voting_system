
from . import views
from django.urls import  path


urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('vote/<int:election_id>/', views.vote, name='vote'),
    path('results/<int:election_id>/', views.results, name='results'),
    path('', views.index, name='index'),
    path('create/', views.create_election, name='create_election'),


]