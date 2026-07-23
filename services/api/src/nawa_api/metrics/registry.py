"""Prometheus registry: default process metrics + exactly two custom histograms.

Registration is guarded against double-import (e.g. test reloads, or the
module being imported twice under different paths) by checking the default
registry for an existing collector with the same name before creating one.
"""

from prometheus_client import REGISTRY, Counter, Histogram


def get_or_create_histogram(name: str, documentation: str, labelnames: list[str]) -> Histogram:
    existing = REGISTRY._names_to_collectors.get(name)
    if existing is not None:
        return existing
    return Histogram(name, documentation, labelnames)


def get_or_create_counter(name: str, documentation: str, labelnames: list[str]) -> Counter:
    # Counter("x_total", ...) registers under both "x_total" and "x_created".
    existing = REGISTRY._names_to_collectors.get(name)
    if existing is not None:
        return existing
    return Counter(name, documentation, labelnames)


http_request_duration_seconds = get_or_create_histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["ip", "method", "route", "status_code"],
)

database_request_duration_seconds = get_or_create_histogram(
    "database_request_duration_seconds",
    "Database operation duration in seconds",
    ["operation", "table", "method", "success"],
)
