from django.contrib import admin
from dataverse_contracts.models.contracts import (
    Contractor,
    PaymentScheme,       
    BaseContract, 
    PresenterHourlyContract, 
    AuthorContract,
    AuthorContent 
)
from dataverse_contracts.models.accruals import Accrual


@admin.register(Contractor)
class ContractorAdmin(admin.ModelAdmin):
    ... 
    
    
@admin.register(PaymentScheme)
class PaymentSchemeAdmin(admin.ModelAdmin):
    ... 
    
    
@admin.register(BaseContract)
class BaseContractAdmin(admin.ModelAdmin):
    ... 
    
    
@admin.register(PresenterHourlyContract)
class PresenterHourlyContractAdmin(admin.ModelAdmin):
    ... 
    
    
@admin.register(AuthorContent)
class AuthorContentAdmin(admin.ModelAdmin):
    ... 
   
   
@admin.register(AuthorContract)
class AuthorContractAdmin(admin.ModelAdmin):
    ... 
    
    
@admin.register(Accrual)
class AccrualAdmin(admin.ModelAdmin):
    ... 
