from django.db import models
from threads.models import User, Course, EducationThread


class Contractor(models.Model):
    
    TYPE_CHOICES = [
        ('individual', 'Individual'),
        ('ip', 'IP'),
        ('self_employed', 'Self-Employed'),
        ('legal_entity', 'Legal Entity'),
        ('non_resident', 'Non-Resident'),
    ]
    
    name = models.CharField(max_length=255, verbose_name='имя')
    contractor_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='тип контрагента')
    inn = models.CharField(max_length=12, unique=True, null=True, blank=True)
    kpp = models.CharField(max_length=9, null=True, blank=True)
    passport_data = models.JSONField(null=True, blank=True)
    bank_details = models.JSONField(null=True, blank=True)
    elba_id = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        verbose_name = 'контрагент'
        verbose_name_plural = 'контрагенты'


class Contract(models.Model):

    TYPE_CHOICES = [
        ('hourly_presenter', 'Hourly Presenter'),
        ('author', 'Author'),
        ('project', 'Project'),
        ('corporate_training', 'Corporate Training'),
    ]

    contract_id = models.CharField(max_length=50, unique=True)
    contract_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    replaced_contract = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, related_name='replacements')
    contractor = models.ForeignKey(Contractor, on_delete=models.CASCADE, related_name='contracts')
    currency = models.CharField(max_length=3, default='RUB')  # RUB, USD, EUR
    comment = models.TextField(null=True, blank=True)
    is_template = models.BooleanField(default=False)
    allow_new_accruals = models.BooleanField(default=True)
    non_financial_terms = models.JSONField(null=True, blank=True)
    signed_at = models.DateField(null=True, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    validity_date = models.DateField(null=True, blank=True)
    actual_created_at = models.DateField(auto_now_add=True)
    
    class Meta:        
        verbose_name = 'контракт'
        verbose_name_plural = 'контракты'
    

class ContractManagerAssignment(models.Model):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='managers')
    manager = models.ForeignKey(User, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)    
    

class PresenterHourlyContract(models.Model):
    
    PAYMENT_SCHEDULE_CHOICES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('after_flow', 'After Flow'),
    ]
    
    contract = models.OneToOneField(Contract, on_delete=models.CASCADE, primary_key=True, related_name='presenter_contract')
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=4)
    payment_schedule = models.CharField(max_length=20, choices=PAYMENT_SCHEDULE_CHOICES)
    payment_day_of_week = models.PositiveSmallIntegerField(null=True, blank=True)
    contractor = models.ForeignKey(Contractor, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=[('lead', 'Lead'), ('co_presenter', 'Co-Presenter')])
    tax_compensation = models.BooleanField(default=False)
    compensation_details = models.JSONField(null=True, blank=True)
    hours_worked = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    rate_type = models.CharField(max_length=10, default='standard')
    
    class Meta:
        verbose_name = 'контракт с ведущим (почасовой)'
        verbose_name_plural = 'контракты с ведущими (почасовые)'
    

class AuthorContract(models.Model):
    
    COMMISSION_TYPE_CHOICES = [
        ('fixed', 'Fixed'),
        ('percentage_revenue', 'Percentage Revenue'),
        ('percentage_profit', 'Percentage Profit'),
        ('hourly_rate', 'Hourly Rate'),
        ('experimental', 'Experimental'),
        ('fixed_plus_percentage', 'Fixed + Percentage'),
    ]
    
    contract = models.OneToOneField(Contract, on_delete=models.CASCADE, primary_key=True, related_name='author_contract')
    commission_type = models.CharField(max_length=30, choices=COMMISSION_TYPE_CHOICES)
    commission_value = models.DecimalField(max_digits=5, decimal_places=2)
    fixed_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    percentage_value = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True)
    is_global = models.BooleanField(default=True)
    linked_hourly_contract = models.ForeignKey(PresenterHourlyContract, on_delete=models.SET_NULL, null=True)
    dynamic_commission_formula = models.JSONField(null=True, blank=True)
    experimental_details = models.JSONField(null=True, blank=True)
    first_flow_bonus = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = 'контракт с автором'
        verbose_name_plural = 'контракты с авторами'


