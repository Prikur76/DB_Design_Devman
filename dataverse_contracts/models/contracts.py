from django.utils import timezone
from django.db import models
from django.db.models import Q, F, Sum, Count, Case, When, Value, Exists, OuterRef, CharField
from django.db.models.functions import Now
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

from dataverse_contracts.models.accruals import Accrual


class BaseContractQuerySet(models.QuerySet):
    def annotate_status(self):
        """Добавляет аннотацию 'status' для контрактов на основе текущих дат и связей."""
        return self.annotate(
            status=Case(
                # Замененный договор
                When(replaced_contract__isnull=False, then=Value('replaced')),
                
                # Проект договора (не подписан)
                When(signed_at__isnull=True, then=Value('draft')),
                
                # Отложенный старт (подписан, но дата начала в будущем)
                When(
                    Q(issue_at__isnull=False) & 
                    Q(issue_at__gt=Now().cast('date')),
                    then=Value('suspended')
                ),
                
                # Выполненный договор (истек срок действия)
                When(
                    Q(expire_at__isnull=False) & 
                    Q(expire_at__lt=Now().cast('date')),
                    then=Value('completed')
                ),
                
                # Частично выполненный (пример: истек срок, но есть активные связи)
                When(
                    Q(expire_at__isnull=False) & 
                    Q(expire_at__lt=Now().cast('date')) & 
                    Q(presenterhourlycontract__hours_worked__gt=0),
                    then=Value('partially_completed')
                ),
                
                # Досрочно завершенный (например, есть дата досрочного завершения)
                When(
                    Q(terminated_at__isnull=False),
                    then=Value('early_completed')
                ),
                
                # Действующий договор
                default=Value('active'),
                output_field=CharField()
            )
        )

    def annotate_total_hours(self):
        """Общее количество отработанных часов по контрактам с ведущими."""
        return self.annotate(
            total_hours=models.Sum('presenterhourlycontract__hours_worked')
        )

    def annotate_content_count(self):
        """Количество авторских материалов по контрактам."""
        return self.annotate(
            content_count=models.Count('authorcontract__authorcontent')
        )

    def annotate_payment_details(self):
        """Аннотация деталей оплаты (например, график, валюта)."""
        return self.annotate(
            payment_schedule=models.F('presenterhourlycontract__payment_schedule'),
            currency=models.F('currency')
        )

    def active(self):
        return self.filter(status='active')

    def draft(self):
        return self.filter(status='draft')

    def suspended(self):
        return self.filter(status='suspended')

    def completed(self):
        return self.filter(status='completed')

    def partially_completed(self):
        return self.filter(status='partially_completed')

    def early_completed(self):
        return self.filter(status='early_completed')
    
    def replaced(self):
        return self.filter(status='replaced')

    def upcoming(self):
        """Контракты с датой начала в будущем."""
        return self.filter(issue_at__gt=models.functions.Now().cast('date'))

    def current(self):
        """Действующие контракты (дата начала <= сегодня < дата окончания)."""
        return self.filter(
            issue_at__lte=models.functions.Now().cast('date'),
            expire_at__gt=models.functions.Now().cast('date')
        )

    def expired(self):
        """Завершённые контракты."""
        return self.filter(expire_at__lt=models.functions.Now().cast('date'))
    
    def expired_soon(self, days=7):
        """Контракты, истекающие в ближайшие N дней"""
        now = timezone.now().date()
        end_date = now + timezone.timedelta(days=days)
        return self.filter(
            expire_at__range=(now, end_date),
            issue_at__lte=Now().cast('date')
        )    
    
    def with_presenters(self):
        """Контракты с ведущими."""
        return self.select_related('presenterhourlycontract__presenter')

    def with_authors(self):
        """Контракты с авторами."""
        return self.select_related('authorcontract__author')
        
    def with_unpaid_accruals(self):
        """Контракты с непогашенными начислениями"""
        from dataverse_contracts.models.accruals import Accrual  # Импорт внутри метода для избежания циклической зависимости
        return self.filter(
            Exists(Accrual.objects.filter(contract=OuterRef('pk'), paid_at__isnull=True))
        )

    def with_confirmed_accruals(self):
        """Контракты с подтвержденными начислениями"""
        from dataverse_contracts.models.accruals import Accrual
        return self.filter(
            Exists(Accrual.objects.filter(contract=OuterRef('pk'), confirmed_at__isnull=False))
        )
    
    def by_template(self, is_template=True):
        """Фильтр по шаблону"""
        return self.filter(is_template=is_template)
    
    def by_period(self, start_date, end_date):
        """Контракты, пересекающиеся с заданным периодом."""
        return self.filter(issue_at__lte=end_date, expire_at__gte=start_date)

    def by_contractor(self, contractor_id):
        """Контракты по контрагенту с оптимизацией выборки"""
        return self.filter(
            Q(authorcontract__author_id=contractor_id) | 
            Q(presenterhourlycontract__presenter_id=contractor_id)
        ).distinct().select_related(
            'presenterhourlycontract__presenter',
            'authorcontract__author'
        )

    def order_by_signed_date(self, ascending=True):
        order = 'signed_at' if ascending else '-signed_at'
        return self.order_by(order)

    def order_by_expiry_date(self, ascending=True):
        order = 'expire_at' if ascending else '-expire_at'
        return self.order_by(order)

    def order_by_status(self):
        """Сортировка по приоритету статусов."""
        status_order = {
            'draft': 0,
            'suspended': 1,
            'active': 2,
            'partially_completed': 3,
            'early_completed': 4,
            'completed': 5,
            'replaced': 6            
        }
        return self.annotate(
            status_order=models.Case(
                *[models.When(status=k, then=Value(v)) for k, v in status_order.items()],
                output_field=models.IntegerField()
            )
        ).order_by('status_order')
        

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
    elba_id = models.CharField(_('ID (Контур-Эльба)'), max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)

    class Meta:
        verbose_name = _('Контрагент')
        verbose_name_plural = _('Контрагенты')

    def __str__(self):
        return f"{self.name} ({self.get_contractor_type_display()})"
    

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
    currency = models.CharField(_('Валюта расчета'), max_length=3, choices=CURRENCIES)
    comment = models.TextField(_('Комментарий'))
    is_template = models.BooleanField(_('Шаблон'), default=False)
    formula_parameters = models.JSONField(_('Параметры для начислений'), null=True, blank=True)
    non_financial_terms = models.JSONField(_('Нефинансовые условия'), null=True, blank=True)
    signed_at = models.DateField(_('Дата подписания'), blank=True, null=True)
    issue_at = models.DateField(_('Дата начала действия'), blank=True, null=True)
    expire_at = models.DateField(_('Дата окончания действия'), blank=True, null=True)
    terminated_at = models.DateField(_('Дата досрочного завершения'), blank=True, null=True)
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)

    objects = BaseContractQuerySet.as_manager()
    
    class Meta:
        verbose_name = _('Контракт')
        verbose_name_plural = _('Контракты')
        indexes = [
            models.Index(name='signed_expired_idx', fields=['signed_at', 'expire_at']),
            models.Index(name='issued_expired_idx', fields=['issue_at', 'expire_at']),
            models.Index(name='replaced_contract_idx', fields=['replaced_contract'])
        ]

    def __str__(self):
        return f"{self.contract_id} ({self.get_currency_display()})"
    

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
    
    contract = models.ForeignKey(
        AuthorContract,
        on_delete=models.DO_NOTHING,
        verbose_name=_('Авторский контракт'), blank=True)
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
