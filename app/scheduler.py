import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings as env
from app.services.poller import poll_once, poll_enabled
from app.services.escalation_service import run_escalation_cycle
from app.services import settings_service

logger = logging.getLogger("alertbot.scheduler")

scheduler = BackgroundScheduler(timezone="UTC")

POLL_JOB_ID = "email_poll"
ESCALATION_JOB_ID = "escalation"


def _poll_job():
    if not poll_enabled():
        return
    summary = poll_once()
    if summary.get("error"):
        logger.warning("Poll error: %s", summary["error"])
    elif summary["fetched"]:
        logger.info(
            "Poll: fetched=%s critical=%s incidents_touched=%s",
            summary["fetched"], summary["critical"], summary["incidents_touched"],
        )


def _escalation_job():
    summary = run_escalation_cycle()
    if summary["repeated"] or summary["escalated"]:
        logger.info(
            "Escalation: repeated=%s escalated=%s (checked %s)",
            summary["repeated"], summary["escalated"], summary["checked"],
        )


def poll_interval() -> int:
    try:
        return max(10, int(settings_service.get("poll.interval_seconds") or env.CHECK_INTERVAL))
    except (TypeError, ValueError):
        return env.CHECK_INTERVAL


def start_scheduler():
    if scheduler.running:
        return

    scheduler.add_job(
        _poll_job, "interval", seconds=poll_interval(),
        id=POLL_JOB_ID, max_instances=1, coalesce=True,
    )
    scheduler.add_job(
        _escalation_job, "interval", seconds=max(10, env.ESCALATION_TICK_SECONDS),
        id=ESCALATION_JOB_ID, max_instances=1, coalesce=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started — polling every %ss, escalation tick every %ss",
        poll_interval(), env.ESCALATION_TICK_SECONDS,
    )


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)


def reschedule_poll(seconds: int | None = None) -> int:
    """Apply a new polling interval without restarting the app."""
    interval = max(10, int(seconds or poll_interval()))
    if scheduler.running:
        scheduler.reschedule_job(POLL_JOB_ID, trigger="interval", seconds=interval)
        logger.info("Poll interval changed to %ss", interval)
    return interval


def job_status() -> list[dict]:
    if not scheduler.running:
        return []
    return [
        {
            "id": job.id,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        }
        for job in scheduler.get_jobs()
    ]
