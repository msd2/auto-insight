"""Procrastinate worker app. No jobs are defined yet.

Run with: uv run procrastinate --app=autoinsight.worker.app worker
"""

import procrastinate

from autoinsight.config import get_settings

app = procrastinate.App(
    connector=procrastinate.PsycopgConnector(conninfo=get_settings().procrastinate_dsn)
)
