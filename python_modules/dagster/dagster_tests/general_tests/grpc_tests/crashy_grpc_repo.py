from __future__ import annotations

import sys

from dagster import repository


@repository
def crashy_repo():
    sys.exit(123)
