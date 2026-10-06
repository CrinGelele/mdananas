"""One scheduling check; the persistent loop lives in pricem_worker."""
from datapull_service.pricem.runner import run_tick


def tick():
    return run_tick()
