from django.contrib import admin
from .models import Election, Candidate, Vote
from import_export.admin import ImportExportModelAdmin

@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'start_date')
    search_fields = ('title',)
    date_hierarchy = 'start_date'

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('name', 'election', 'votes')

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'candidate', 'voted_at')  # заменили 'timestamp' -> 'voted_at'
    list_filter = ('voted_at',)                       # убрали 'timestamp'
    search_fields = ('user__username', 'candidate__name')
