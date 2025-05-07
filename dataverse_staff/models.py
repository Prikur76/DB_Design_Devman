from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from dataverse_contracts.models.contracts import BaseContract


class User(AbstractUser):
    ROLES = (
        ('director', 'Директор'),
        ('chief_accountant', 'Главный бухгалтер'),
        ('manager', 'Менеджер'),
        ('presenter', 'Ведущий'),
    )
    
    username = models.CharField(_('Логин'), max_length=150, unique=True)
    first_name = models.CharField(_('Имя'), max_length=150)
    last_name = models.CharField(_('Фамилия'), max_length=150)
    email = models.EmailField(_('Электронная почта'))
    phone = models.CharField(_('Телефон'), max_length=20)
    role = models.CharField(_('Роль'), max_length=20, choices=ROLES)
    department = models.ForeignKey(
        'Department', 
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_('Отдел'))
    is_superuser = models.BooleanField(_('Суперпользователь'), default=False)
    is_staff = models.BooleanField(_('Персонал'), default=False)
    is_active = models.BooleanField(_('Активен'), default=True)
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)

    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')

    def __str__(self):        
        return f"{self.username} ({self.get_role_display()})" if self.get_role_display() else self.username


class Department(models.Model):
    name = models.CharField(max_length=100)
    director = models.OneToOneField(
        'dataverse_staff.User', 
        on_delete=models.CASCADE, 
        related_name='department_director',
        verbose_name='директор'
    )
    
    class Meta:
        verbose_name = 'подразделение'
        verbose_name_plural = 'подразделения'


class ContractManagerAssignment(models.Model):
    manager = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('Менеджер'))
    contract = models.ForeignKey(
        BaseContract, 
        on_delete=models.CASCADE,
        verbose_name=_('Контракт'))
    assigned_at = models.DateTimeField(_('Дата назначения'), auto_now_add=True)

    class Meta:
        unique_together = ('contract', 'manager')
        verbose_name = 'контракт'
        verbose_name_plural = 'закрепленные контракты'

    def __str__(self):
        return f"Контракт {self.contract.contract_id} - Менеджер {self.manager.username}"

