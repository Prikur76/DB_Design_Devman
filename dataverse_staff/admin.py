from django.contrib import admin

from dataverse_staff.models import (
    User, 
    Department,
    ContractManagerAssignment
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
