from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('director', 'Директор'),
        ('chief_accountant', 'Главный бухгалтер'),
        ('manager', 'Администратор обучения'),
        ('presenter', 'Ведущий курса'),
    ]
    
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES,
        verbose_name='роль')
    department = models.ForeignKey(
        'Department', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='managers',
        verbose_name='подразделение'
    )
    phone = models.CharField(max_length=20, null=True, blank=True)
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'


class Department(models.Model):
    name = models.CharField(max_length=100)
    director = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='department_director',
        verbose_name='директор'
    )
    
    class Meta:
        verbose_name = 'подразделение'
        verbose_name_plural = 'подразделения'
        
    
class Course(models.Model):
    
    FORMAT_CHOICES = [
        ('bootcamp', 'Bootcamp'),
        ('workshop', 'Workshop'),
        ('offline', 'Offline'),
        ('online', 'Online'),
    ]
    
    title = models.CharField(max_length=255, verbose_name='название')
    description = models.TextField(verbose_name='описание')
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES, verbose_name='формат курса')
    prefix = models.CharField(max_length=10, verbose_name='префикс')
    schedule = models.JSONField(null=True, blank=True, verbose_name='расписание')

    class Meta:
        verbose_name = 'курс'
        verbose_name_plural = 'курсы'


class EducationThread(models.Model):
    article = models.CharField(max_length=50, unique=True, verbose_name='артикул')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='threads', verbose_name='курс')
    start_date = models.DateField(null=True, blank=True, verbose_name='дата начала')
    end_date = models.DateField(null=True, blank=True, verbose_name='дата окончания')
    is_open_start = models.BooleanField(default=False, verbose_name='с открытой датой начала')
    is_open_end = models.BooleanField(default=False, verbose_name='с открытой датой окончания')
    is_auto_generated = models.BooleanField(default=False, verbose_name='автогенерация')

    class Meta:
        verbose_name = 'образовательный поток'
        verbose_name = 'образовательные потоки'
        
    def __str__(self):
        return self.article
    
    

    
