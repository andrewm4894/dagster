from __future__ import annotations

import pytest


@pytest.fixture
def databricks_run_config() -> dict:
    return {
        "run_name": "dagster-databricks-test",
        "cluster": {"existing": "foo"},
        "task": {
            "spark_jar_task": {"main_class_name": "my-class", "parameters": ["first", "second"]}
        },
    }
