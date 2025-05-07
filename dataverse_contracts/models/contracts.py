from django.utils import timezone
from django.db import models
from django.db.models import Q, F, Count, Exists, OuterRef
from django.db.models.functions import Now
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

from dataverse_contracts.models.accruals import Accrual


class BaseContractManager(models.Manager):
    def active(self):
        """Действующие контракты (вступили в силу и не истекли)"""
        now = Now()
        return self.filter(
            issue_at__lte=now,
            expire_at__gt=now
        ).select_related('payment_scheme', 'replaced_contract')

    def completed(self):
        """Завершенные контракты (истекли или заменены)"""
        now = Now()
        return self.filter(
            Q(expire_at__lte=now) | Q(replaced_contract__isnull=False)
        ).select_related('payment_scheme')

    def partially_executed(self):
        """Контракты с частично выполненными обязательствами"""
        return self.annotate(
            obligations_count=Count('non_financial_terms'),
            executed_count=Count('accruals', filter=Q(accruals__paid_at__isnull=False))
        ).filter(
            executed_count__lt=F('obligations_count'),
            executed_count__gt=0
        ).prefetch_related('accruals')

    def by_status(self, status):
        """Контракты по статусу начислений"""
        return self.filter(
            accruals__status=status
        ).distinct().select_related('payment_scheme')

    def author_contracts(self):
        """Авторские контракты"""
        return self.filter(
            Exists(AuthorContract.objects.filter(contract=OuterRef('pk')))
        ).select_related('payment_scheme')

    def hourly_presenter_contracts(self):
        """Почасовые контракты с ведущими"""
        return self.filter(
            Exists(PresenterHourlyContract.objects.filter(contract=OuterRef('pk')))
        ).select_related('payment_scheme')

    def by_payment_scheme(self, scheme_id):
        """Контракты по схеме оплаты"""
        return self.filter(payment_scheme_id=scheme_id).select_related('payment_scheme')

    def by_currency(self, currency):
        """Контракты по валюте"""
        return self.filter(currency=currency)

    def by_date_range(self, start_date, end_date):
        """Контракты, активные в заданном диапазоне дат"""
        return self.filter(
            Q(issue_at__lte=end_date) & 
            Q(expire_at__gte=start_date)
        ).select_related('payment_scheme')

    def with_unpaid_accruals(self):
        """Контракты с непогашенными начислениями"""
        return self.filter(
            Exists(Accrual.objects.filter(contract=OuterRef('pk'), paid_at__isnull=True))
        )

    def with_confirmed_accruals(self):
        """Контракты с подтвержденными начислениями"""
        return self.filter(
            Exists(Accrual.objects.filter(contract=OuterRef('pk'), confirmed_at__isnull=False))
        )

    def expired_soon(self, days=7):
        """Контракты, истекающие в ближайшие N дней"""
        now = models.functions.Now()
        return self.filter(
            expire_at__range=(now, now + models.DurationField(default=f'{days} days')),
            issue_at__lte=now
        )

    def by_contractor(self, contractor_id):
        """Контракты по контрагенту"""
        return self.filter(
            Q(authorcontract__author_id=contractor_id) | 
            Q(presenterhourlycontract__presenter_id=contractor_id)
        ).distinct().select_related('payment_scheme')

    def by_template(self, is_template=True):
        """Фильтр по шаблону"""
        return self.filter(is_template=is_template)

    def annotate_payment_stats(self):
        """Аннотировать статистику по начислениям"""
        return self.annotate(
            total_accruals=Count('accruals'),
            paid_accruals=Count('accruals', filter=Q(accruals__paid_at__isnull=False)),
            unpaid_accruals=Count('accruals', filter=Q(accruals__paid_at__isnull=True)),
            total_amount=models.Sum('accruals__amount')
        )


class Contractor(models.Model):
    CONTRACTOR_TYPES = (
        ('individual', 'Физическое лицо'),
        ('ip', 'Индивидуальный предприниматель'),
        ('self_employed', 'Самозанятый'),
        ('legal_entity', 'Юридическое лицо'),
        ('non_resident', 'Нерезидент'),
    )
    
    name = models.CharField(_('Наименование'), max_length=255)
    contractor_type = models.CharField(
        _('Тип контрагента'), 
        max_length=20, 
        choices=CONTRACTOR_TYPES)
    inn = models.CharField(_('ИНН'), max_length=17, unique=True, null=True, blank=True)
    kpp = models.CharField(_('КПП'), max_length=9, null=True, blank=True)
    passport_data = models.JSONField(_('Паспортные данные'), null=True, blank=True)
    bank_details = models.JSONField(_('Реквизиты банка'), null=True, blank=True)
    elba_id = models.CharField(_('Контур Эльба'), max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)

    class Meta:
        verbose_name = _('Контрагент')
        verbose_name_plural = _('Контрагенты')

    def __str__(self):
        return f"{self.name} ({self.get_contractor_type_display()})"
    
    
class PaymentScheme(models.Model):
    name = models.CharField(_('Название схемы'), max_length=50)
    description = models.TextField(_('Описание схемы'))
    parameters = models.JSONField(_('Параметры схемы'))
    is_active = models.BooleanField(_('Активна'), default=True)

    class Meta:
        verbose_name = _('Схема оплаты')
        verbose_name_plural = _('Схемы оплаты')

    def __str__(self):
        return self.name


class BaseContract(models.Model):
    CURRENCIES = (
        ('RUB', 'Рубли'),
        ('USD', 'Доллары США'),
        ('EUR', 'Евро'),
    )
    
    contract_id = models.CharField(_('ID контракта'), max_length=50, unique=True, db_index=True)
    replaced_contract = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        verbose_name=_('Замененный контракт'))
    currency = models.CharField(_('Валюта'), max_length=3, choices=CURRENCIES)
    comment = models.TextField(_('Комментарий'))
    is_template = models.BooleanField(_('Шаблон'), default=False)
    payment_scheme = models.ForeignKey(
        PaymentScheme,
        on_delete=models.CASCADE,
        verbose_name=_('Схема оплаты'))
    non_financial_terms = models.JSONField(_('Нефинансовые условия'), null=True, blank=True)
    signed_at = models.DateField(_('Дата подписания'), blank=True, null=True)
    issue_at = models.DateField(_('Дата начала действия'), blank=True, null=True)
    expire_at = models.DateField(_('Дата окончания действия'), blank=True, null=True)
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)

    objects = BaseContractManager()
    
    class Meta:
        verbose_name = _('Контракт')
        verbose_name_plural = _('Контракты')
        indexes = [
            models.Index(name='signed_expired_idx', fields=['signed_at', 'expire_at']),
            models.Index(name='issued_expired_idx', fields=['issue_at', 'expire_at']),
            models.Index(name='currency_payment_scheme_idx', fields=['currency', 'payment_scheme']),
            models.Index(name='replaced_contract_idx', fields=['replaced_contract'])
        ]

    def __str__(self):
        return f"{self.contract_id} ({self.get_currency_display()})"
    
    @property
    def is_active(self):
        """Вычисляемое свойство: активен ли контракт на текущую дату"""
        now = timezone.now().date()
        
        if not self.issue_at or not self.expire_at:
            return False
        
        return self.issue_at <= now <= self.expire_at


class PresenterHourlyContract(models.Model):
    PAYMENT_SCHEDULES = (
        ('weekly', 'Еженедельно'),
        ('monthly', 'Ежемесячно'),
        ('after_flow', 'После потока'),
    )
    
    ROLES = (
        ('lead', 'Основной ведущий'),
        ('co_presenter', 'Соведущий'),
    )
    
    contract = models.OneToOneField(
        BaseContract,
        on_delete=models.CASCADE, 
        primary_key=True,
        verbose_name=_('Контракт'))
    payment_schedule = models.CharField(
        _('График платежей'), 
        max_length=10, 
        choices=PAYMENT_SCHEDULES)
    payment_day_of_week = models.PositiveSmallIntegerField(
        _('День платежа'),
        validators=[MinValueValidator(1), MaxValueValidator(7)], 
        null=True, blank=True)
    presenter = models.ForeignKey(
        Contractor, 
        on_delete=models.CASCADE,
        verbose_name=_('ведущий'))
    role = models.CharField(_('роль'), max_length=20, choices=ROLES, db_index=True)
    hours_worked = models.DecimalField(_('отработанные часы'), max_digits=5, decimal_places=2)

    class Meta:
        verbose_name = _('Контракт с ведущим (почасовой)')
        verbose_name_plural = _('Контракты с ведущими (почасовые)')
        indexes = [
            models.Index(name='presenter_role_idx', fields=['presenter', 'role']),
        ]
        

    def __str__(self):
        return f"Контракт {self.contract.contract_id} - {self.presenter.name}"


class AuthorContract(models.Model):
    contract = models.OneToOneField(
        BaseContract,
        on_delete=models.CASCADE,
        primary_key=True,
        verbose_name=_('Контракт'))
    content = models.ForeignKey(
        'AuthorContent',
        on_delete=models.CASCADE,
        verbose_name=_('Авторский материал'))
    author = models.ForeignKey(
        Contractor,
        on_delete=models.CASCADE,
        verbose_name=_('Автор'))

    class Meta:
        verbose_name = _('Контракт с автором')
        verbose_name_plural = _('Контракты с авторами')

    def __str__(self):
        return f"Авторский контракт #{self.contract.contract_id}"


class AuthorContent(models.Model):
    CONTENT_FORMATS = (
        ('presentation', 'Презентация'),
        ('video', 'Видеоматериал'),
        ('article', 'Статья'),
    )
    
    title = models.CharField(_('Название'), max_length=255)
    description = models.TextField(_('Описание'))
    content_format = models.CharField(
        _('Формат'), max_length=20, 
        choices=CONTENT_FORMATS)
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)

    class Meta:
        verbose_name = _('Авторский материал')
        verbose_name_plural = _('Авторские материалы')

    def __str__(self):
        return self.title
