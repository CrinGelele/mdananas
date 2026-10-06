"""Compatibility entry point using the same scheduler and importer as the worker."""
from datapull_service.pricem.runner import run_tick


def process_pricem():
    return run_tick()
