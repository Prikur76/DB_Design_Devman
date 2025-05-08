from django.contrib import admin
from dataverse_contracts.models.contracts import (
    Contractor,   
    BaseContract, 
    PresenterHourlyContract, 
    AuthorContract,
    AuthorContent 
)
from dataverse_contracts.models.accruals import Accrual


@admin.register(Contractor)
class ContractorAdmin(admin.ModelAdmin):
    ... 
    
    
    
@admin.register(BaseContract)
class BaseContractAdmin(admin.ModelAdmin):
    ... 
    
    
@admin.register(PresenterHourlyContract)
class PresenterHourlyContractAdmin(admin.ModelAdmin):
    ... 
    

class AuthorContentInline(admin.TabularInline):
    model = AuthorContent
    extra = 0
    list_per_page = 10 

   
@admin.register(AuthorContract)
class AuthorContractAdmin(admin.ModelAdmin):
    inlines = [AuthorContentInline, ]
    ... 
    
    
@admin.register(Accrual)
class AccrualAdmin(admin.ModelAdmin):
    ... 
