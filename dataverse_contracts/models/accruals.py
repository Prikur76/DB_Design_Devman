from datetime import timedelta
from django.utils import timezone
from django.apps import apps
from django.db import models
from django.db.models import Q, DurationField, Case, When, Value, CharField
from django.db.models.functions import Now
from django.utils.translation import gettext_lazy as _


class AccrualManager(models.Manager):
    def confirmed(self):
        """Подтвержденные начисления"""
        return self.filter(confirmed_at__isnull=False).select_related('contract')

    def paid(self):
        """Оплаченные начисления"""
        return self.filter(paid_at__isnull=False).select_related('contract')

    def pending(self):
        """Ожидаемые начисления"""
        return self.filter(confirmed_at__isnull=True, paid_at__isnull=True)

    def overdue(self):
        """Просроченные начисления"""
        return self.filter(
            Q(confirmed_at__lt=Now() - DurationField(default='30 days')) &
            Q(paid_at__isnull=True)
        )
        
    def by_status(self, status):
        """Фильтрация по статусу начисления"""
        status_filters = {
            'paid': Q(paid_at__isnull=False),
            'confirmed': Q(confirmed_at__isnull=False, paid_at__isnull=True),
            'overdue': Q(
                confirmed_at__lt=Now() - DurationField(default='30 days'),
                paid_at__isnull=True
            ),
            'pending': Q(confirmed_at__isnull=True, paid_at__isnull=True)
        }
        
        if status in status_filters:
            return self.filter(status_filters[status]).select_related('contract')
        return self.none()

    def annotate_status(self):
        """Аннотация статуса начисления для SQL-запросов"""
        return self.annotate(
            status_annotation=Case(
                When(paid_at__isnull=False, then=Value('paid')),
                When(
                    confirmed_at__isnull=False,
                    paid_at__isnull=True,
                    confirmed_at__lt=Now() - DurationField(default='30 days'),
                    then=Value('overdue')
                ),
                When(confirmed_at__isnull=False, paid_at__isnull=True, then=Value('confirmed')),
                default=Value('pending'),
                output_field=CharField()
            )
        )

    def by_contractor(self, contractor_id):
        """Начисления по контрагенту"""
        return self.filter(
            Q(contract__authorcontract__author_id=contractor_id) |
            Q(contract__presenterhourlycontract__presenter_id=contractor_id)
        ).distinct().select_related('contract')

    def by_date_range(self, start_date, end_date):
        """Начисления в заданном диапазоне дат"""
        return self.filter(
            Q(created_at__range=(start_date, end_date)) |
            Q(confirmed_at__range=(start_date, end_date)) |
            Q(paid_at__range=(start_date, end_date))
        ).select_related('contract')

    def total_amount(self):
        """Общая сумма начислений"""
        return self.aggregate(total=models.Sum('amount'))['total'] or 0

    def average_amount(self):
        """Средняя сумма начисления"""
        return self.aggregate(average=models.Avg('amount'))['average'] or 0

    def by_currency(self, currency):
        """Начисления по валюте"""
        return self.filter(currency=currency).select_related('contract')


class Accrual(models.Model):
    # contract = models.ForeignKey(
    #     BaseContract,
    #     on_delete=models.CASCADE,
    #     verbose_name=_('Контракт'))
    contract_id = models.PositiveIntegerField(_('ID контракта'))
    amount = models.DecimalField(_('Сумма'), max_digits=10, decimal_places=2)
    confirmed_at = models.DateTimeField(
        _('Дата подтверждения'), null=True, blank=True, db_index=True)
    paid_at = models.DateTimeField(_('Дата оплаты'), null=True, blank=True)
    is_automated = models.BooleanField(_('Автоматически'), default=False)
    comment = models.TextField(_('Комментарий'), null=True, blank=True)
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    
    objects = AccrualManager()

    class Meta:
        verbose_name = _('Начисление')
        verbose_name_plural = _('Начисления')
        indexes = [
            models.Index(name='confirmed_and_paid_idx', fields=['confirmed_at', 'paid_at']),
            models.Index(name='confirmed_contracts_idx', fields=['contract_id', 'confirmed_at']),
        ]

    def __str__(self):
        return f"Начисление {self.amount} {self.currency} по контракту {self.contract.contract_id}"

    @property
    def status(self):
        """Вычисляемое свойство: статус начисления"""
        now = timezone.now()
        
        if self.paid_at:
            return 'paid'
        elif self.confirmed_at:
            # Проверяем просрочку: если подтверждено более 30 дней назад
            if (now - self.confirmed_at) > timedelta(days=30):
                return 'overdue'
            return 'confirmed'
        else:
            return 'pending'
        
    def get_contract_details(self):
        """
        Возвращает связанный контракт через динамический импорт модели
        """
        # Получаем модель BaseContract
        BaseContract = apps.get_model('dataverse_contracts', 'BaseContract')
        
        try:
            contract = BaseContract.objects.get(id=self.contract_id)
            return {
                'contract_id': contract.contract_id,
                'currency': contract.currency
            }
        except BaseContract.DoesNotExist:
            return {"error": "Контракт не найден"}
