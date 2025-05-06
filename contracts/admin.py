from django.contrib import admin
from .models import (
    Contractor, Contract, PresenterHourlyContract, AuthorContract
)

@admin.register(Contractor)
class ContractorAdmin(admin.ModelAdmin):
    ... 
    
@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    ... 
    
@admin.register(PresenterHourlyContract)
class PresenterHourlyContractAdmin(admin.ModelAdmin):
    ... 
    
@admin.register(AuthorContract)
class AuthorContractAdmin(admin.ModelAdmin):
    ... 