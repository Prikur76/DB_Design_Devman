from django.utils import timezone
from django.db import models
from django.db.models import Q,  Case, When, Value
from django.db.models.functions import Now
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from dataverse_contracts.models.contracts import AuthorContent, BaseContract


class EducationThreadQuerySet(models.QuerySet):
    def annotate_status(self):
        """Добавляет аннотацию статуса потока: active, upcoming, expired, open_start, open_end."""
        now = Now().cast('date')  # Приведение к типу DATE для корректного сравнения
        return self.annotate(
            status=Case(
                # Статус "open" — обе даты открыты
                When(Q(is_open_start=True) & Q(is_open_end=True), then=Value('open')),
                
                # Статус "open_start" — только начало открыто
                When(Q(is_open_start=True) & Q(is_open_end=False), then=Value('open_start')),
                
                # Статус "open_end" — только конец открыт
                When(Q(is_open_start=False) & Q(is_open_end=True), then=Value('open_end')),
                
                # Статус "active" — даты заданы и поток активен
                When(
                    Q(is_open_start=False) &
                    Q(is_open_end=False) &
                    Q(start_date__lte=now) &
                    Q(end_date__gte=now),
                    then=Value('active')
                ),
                
                # Статус "upcoming" — дата начала в будущем
                When(
                    Q(is_open_start=False) &
                    Q(start_date__gt=now),
                    then=Value('upcoming')
                ),
                
                # Статус "expired" — дата окончания в прошлом
                When(
                    Q(is_open_end=False) &
                    Q(end_date__lt=now),
                    then=Value('expired')
                ),
                
                # Резервный статус на случай непредвиденных условий
                default=Value('unknown'),
                output_field=models.CharField()
            )
        )
        
    def active(self):
        return self.filter(status='active')

    def upcoming(self):
        return self.filter(status='upcoming')

    def expired(self):
        return self.filter(status='expired')

    def open(self):
        return self.filter(status='open')

    def open_start(self):
        return self.filter(status='open_start')

    def open_end(self):
        return self.filter(status='open_end')
    
    def annotate_contract_count(self):
        """Количество связанных контрактов"""
        return self.annotate(
            contract_count=models.Count(
                'threadcontractassignment',
                filter=Q(threadcontractassignment__isnull=False),
                distinct=True
            )
        )

    def annotate_duration_days(self):
        """Аннотация длительности потока в днях"""
        return self.annotate(
            duration_days=models.Case(
                When(
                    is_open_start=False,
                    is_open_end=False,
                    then=models.F('end_date') - models.F('start_date')
                ),
                default=Value(None),
                output_field=models.IntegerField()
            )
        )
        
    def order_by_status_priority(self):
        """Сортировка по приоритету статусов"""
        status_order = {
            'active': 0,
            'upcoming': 1,
            'open': 2,
            'open_start': 3,
            'open_end': 4,
            'expired': 5
        }
        return self.annotate(
            status_order=models.Case(
                *[models.When(status=k, then=Value(v)) for k, v in status_order.items()],
                output_field=models.IntegerField()
            )
        ).order_by('status_order')

    def order_by_start_date(self, ascending=True):
        """Сортировка по дате начала"""
        order = 'start_date' if ascending else '-start_date'
        return self.order_by(order)

    def order_by_duration(self, ascending=True):
        """Сортировка по длительности потока"""
        order = 'duration_days' if ascending else '-duration_days'
        return self.annotate_duration_days().order_by(order)

    def search_by_article(self, query):
        """Поиск потоков по артикулу"""
        return self.filter(article__icontains=query)

    def by_format(self, format_type):
        """Потоки по формату (bootcamp, workshop и т.д.)"""
        return self.filter(article__icontains=format_type).select_related('author_content')
    
    def by_schedule_key(self, key):
        """Потоки с определенным ключом в расписании"""
        return self.filter(schedule__contains={key: True})
    
    def recently_created(self, days=7):
        """Потоки, созданные за последние N дней"""
        return self.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=days)
        )

    def auto_generated(self):
        """Потоки с автоматической генерацией расписания"""
        return self.filter(is_auto_generated=True).prefetch_related('schedule')


class EducationThread(models.Model):
    article = models.CharField(_('Артикул потока'), max_length=50, unique=True)
    author_content = models.ForeignKey(
        AuthorContent, 
        on_delete=models.CASCADE, 
        verbose_name=_('Авторский материал'))
    start_date = models.DateField(_('Дата начала'))
    end_date = models.DateField(_('Дата окончания'))
    is_open_start = models.BooleanField(_('Открытая дата начала'), default=False)
    is_open_end = models.BooleanField(_('Открытая дата окончания'), default=False)
    is_auto_generated = models.BooleanField(_('Автогенерация'), default=False)
    schedule = models.JSONField(
        _('Расписание'),
        help_text=_('JSON-формат расписания на полгода'))
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    
    objects = EducationThreadQuerySet.as_manager()

    class Meta:
        verbose_name = _('Образовательный поток')
        verbose_name_plural = _('Образовательные потоки')

    def __str__(self):
        return self.article
    
    def clean(self):
        if not self.is_open_start and not self.start_date:
            raise ValidationError(
                {
                    'start_date': 'Дата начала обязательна, если не установлен флаг "Открытая дата начала"'
                }
            )

        if not self.is_open_end and not self.end_date:
            raise ValidationError(
                {
                    'end_date': 'Дата окончания обязательна, если не установлен флаг "Открытая дата окончания"'
                }
            )
        

class ThreadContractAssignment(models.Model):
    thread = models.ForeignKey(
        EducationThread,
        on_delete=models.CASCADE,
        verbose_name=_('Поток'))
    contract = models.ForeignKey(
        BaseContract, 
        on_delete=models.CASCADE, 
        verbose_name=_('Контракт'))
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)

    class Meta:
        verbose_name = _('контракт')
        verbose_name_plural = _('контракты потока')
        unique_together = ('thread', 'contract')

    def __str__(self):
        return f"Поток {self.thread.article} - Контракт {self.contract.contract_id}"
