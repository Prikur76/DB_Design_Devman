from django.contrib import admin

from dataverse_threads.models.users import (
    User, 
    Department,
    ContractManagerAssignment
)
from dataverse_threads.models.education_threads import (
    EducationThread, 
    ThreadContractAssignment       
)


class ContractManagerAssignmentInline(admin.TabularInline):
    model = ContractManagerAssignment
    extra=1
    can_delete = False
    list_per_page = 10


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    inlines = [ContractManagerAssignmentInline, ]
    ... 


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    ... 

    
class ThreadContractAssignmentInline(admin.TabularInline):
    model = ThreadContractAssignment
    extra = 1
    can_delete = False
    list_per_page = 10
    

@admin.register(EducationThread)
class EducationThreadAdmin(admin.ModelAdmin):
    inlines = [ThreadContractAssignmentInline, ]

    