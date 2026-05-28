from django.core.management.base import BaseCommand
from django.utils import timezone
from datapull_service.models.pricem_models import TaskSchedule
from datapull_service.pricem_upl import process_pricem

class Command(BaseCommand):
    def handle(self, *args, **options):
        print("=" * 50)
        print("ЗАПУСК КОМАНДЫ pricem_run")
        print("=" * 50)
        
        now = timezone.now()
        print(f"Текущее локальное время: {now.hour:02d}:{now.minute:02d}")
        print(f"День недели: {now.weekday()} (0=Пн, 6=Вс)")
        print(f"Дата: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n" + "-" * 30)
        print("ВСЕ ЗАПИСИ В ТАБЛИЦЕ:")
        all_tasks = TaskSchedule.objects.all()
        print(f"Всего записей: {all_tasks.count()}")
        for t in all_tasks:
            print(f"  id={t.id} | {t.time_hour:02d}:{t.time_minute:02d} | active={t.is_active}")
        
        print("\n" + "-" * 30)
        print("ПОИСК ЗАДАЧ:")
        print(f"Ищем: hour={now.hour}, minute={now.minute}, is_active=True")
        
        tasks = TaskSchedule.objects.filter(
            is_active=True,
            time_hour=now.hour,
            time_minute=now.minute
        )
        
        print(f"Найдено задач: {tasks.count()}")
        
        if tasks.count() == 0:
            print("\nПочему не найдено? Проверяем:")
            # Проверка только по часу
            hour_tasks = TaskSchedule.objects.filter(is_active=True, time_hour=now.hour)
            print(f"  Задач с таким же часом ({now.hour}): {hour_tasks.count()}")
            for t in hour_tasks:
                print(f"    id={t.id} | {t.time_hour:02d}:{t.time_minute:02d} (нужно {now.hour:02d}:{now.minute:02d})")
            
            # Проверка только по минуте
            minute_tasks = TaskSchedule.objects.filter(is_active=True, time_minute=now.minute)
            print(f"  Задач с такой же минутой ({now.minute}): {minute_tasks.count()}")
            
            # Проверка неактивных
            inactive = TaskSchedule.objects.filter(is_active=False, time_hour=now.hour, time_minute=now.minute)
            print(f"  Неактивных задач на это время: {inactive.count()}")
        
        print("\n" + "-" * 30)
        print("ВЫПОЛНЕНИЕ:")
        
        for i, task in enumerate(tasks, 1):
            print(f"\n{i}. Выполняю задачу id={task.id}")
            print(f"   Время: {task.time_hour:02d}:{task.time_minute:02d}")
            print(f"   Вызываю функцию pricem_function()...")
            
            try:
                process_pricem()  # замени на название своей функции
                print(f"   ✓ Функция выполнена успешно")
            except Exception as e:
                print(f"   ✗ Ошибка при выполнении: {e}")
        
        print("\n" + "=" * 50)
        print("ЗАВЕРШЕНИЕ КОМАНДЫ")
        print("=" * 50)