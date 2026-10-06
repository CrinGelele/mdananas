import logging
from datetime import datetime
import pytz

from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone

from datapull_service.models.pricem_models import TaskSchedule, PricemLOG
from datapull_service.views.pricem_views import process_priceva_data

logger = logging.getLogger(__name__)

# Без jobstore — задачи живут в памяти процесса.
# Нам это и нужно: расписание читается из БД каждую минуту.
scheduler = BackgroundScheduler(timezone=str(timezone.get_current_timezone()))
MSK_TZ = pytz.timezone('Europe/Moscow')

def _log(schedule, status, when):
    PricemLOG.objects.create(
        date_time=when,
        schedule=schedule,
        status=status,
    )


def tick():
    now = timezone.now().astimezone(MSK_TZ)

    print('tick', now)

    due = TaskSchedule.objects.filter(
        is_active=True,
        time_hour=now.hour,
        time_minute=now.minute,
    )

    print(due)

    if not due.exists():
        return

    for sched in due:
        # Защита от повторного запуска в ту же минуту
        already = PricemLOG.objects.filter(
            schedule=sched,
            date_time__year=now.year,
            date_time__month=now.month,
            date_time__day=now.day,
            date_time__hour=now.hour,
            date_time__minute=now.minute,
        ).exclude(status__startswith="skipped").exists()
        # ^ исключаем «skipped», если вдруг вы решите их тоже писать

        if already:
            logger.info("Schedule %s already ran this minute, skipping", sched.id)
            continue

        try:
            process_priceva_data()
        except Exception as e:
            logger.exception("Schedule %s failed", sched.id)
            _log(sched, f"error: {e}", now)
            continue

        _log(sched, "success", now)
        logger.info("Schedule %s executed OK", sched.id)


scheduler.add_job(
    tick,
    trigger="cron",
    minute="*",
    id="schedule_tick",
    replace_existing=True,
    max_instances=1,
    coalesce=True,
    misfire_grace_time=30,
)