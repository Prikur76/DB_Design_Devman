from django.utils import timezone
from django.db import models
from django.db.models import Q, Exists, OuterRef
from django.db.models.functions import Now
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from dataverse_contracts.models.contracts import AuthorContent, BaseContract


class EducationThreadManager(models.Manager):
    def active(self):
        """Потоки, которые сейчас активны (на основе дат и флагов open)"""
        now = Now()
        return self.filter(
            Q(
                is_open_start=True,
                is_open_end=True
            ) | Q(
                is_open_start=True,
                end_date__gte=now
            ) | Q(
                is_open_end=True,
                start_date__lte=now
            ) | Q(
                is_open_start=False,
                is_open_end=False,
                start_date__lte=now,
                end_date__gte=now
            )
        )

    def upcoming(self):
        """Ближайшие потоки (будущие или с открытой датой начала)"""
        now = Now()
        return self.filter(
            Q(is_open_start=True) | Q(start_date__gte=now)
        ).select_related('author_content')

    def by_format(self, format_type):
        """Потоки по формату (bootcamp, workshop и т.д.)"""
        return self.filter(article__icontains=format_type).select_related('article')

    def by_content(self, content_id):
        """Потоки по конкретному курсу/материалу"""
        return self.filter(author_content_id=content_id).select_related('author_content')

    def auto_generated(self):
        """Потоки с автоматической генерацией расписания"""
        return self.filter(is_auto_generated=True).prefetch_related('schedule')

    def with_contracts(self):
        """Потоки с хотя бы одним связанным контрактом"""
        return self.filter(
            Exists(ThreadContractAssignment.objects.filter(thread=OuterRef('pk')))
        )

    def open_dates(self):
        """Потоки с открытыми датами начала или окончания"""
        return self.filter(
            Q(is_open_start=True) | Q(is_open_end=True)
        )

    def by_date_range(self, start_date, end_date):
        """Потоки в заданном диапазоне дат"""
        return self.filter(
            Q(
                start_date__range=(start_date, end_date),
                is_open_start=False
            ) | Q(
                is_open_start=True,
                end_date__gte=start_date
            )
        ).select_related('author_content')

    def recent(self, days=7):
        """Потоки, созданные за последние N дней"""
        return self.filter(
            created_at__gte=Now() - models.DurationField(default=f'{days} days')
        )

    def schedule_contains(self, key):
        """Потоки с определенным ключом в расписании"""
        return self.filter(schedule__has_key=key)


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
    
    objects = EducationThreadManager()

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
        
    @property
    def is_active(self):
        now = timezone.now().date()
        
        # Проверяем условия активности
        if self.is_open_start and self.is_open_end:
            return True
        
        if self.is_open_start:
            return self.end_date >= now if self.end_date else True
        
        if self.is_open_end:
            return self.start_date <= now if self.start_date else True
        
        return (self.start_date and self.end_date and 
                self.start_date <= now <= self.end_date)


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
        verbose_name = _('прикрепление контракта к потоку')
        unique_together = ('thread', 'contract')

    def __str__(self):
        return f"Поток {self.thread.article} - Контракт {self.contract.contract_id}"
