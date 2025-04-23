from django.contrib import admin
from .models import Election, Candidate, Vote,Achievement
from import_export.admin import ImportExportModelAdmin



@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'required_votes')
    search_fields = ('name',)
    list_filter = ('required_votes',)

@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_date', 'end_date', 'is_active','total_votes')
    list_filter = ('is_active', 'start_date')
    search_fields = ('title',)
    date_hierarchy = 'start_date'

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('name', 'election', 'vote_count')

    def vote_count(self, obj):
        return obj.votes.count()
    vote_count.short_description = 'Количество голосов'

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'candidate', 'voted_at','election')
    list_filter = ('voted_at',)
    search_fields = ('user__username', 'candidate__name')
