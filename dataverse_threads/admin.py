from django.contrib import admin

from dataverse_threads.models.education_threads import (
    EducationThread, 
    ThreadContractAssignment       
)


class ThreadContractAssignmentInline(admin.TabularInline):
    model = ThreadContractAssignment
    extra = 1
    can_delete = False
    list_per_page = 10
    

@admin.register(EducationThread)
class EducationThreadAdmin(admin.ModelAdmin):
    inlines = [ThreadContractAssignmentInline, ]
