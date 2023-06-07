from __future__ import annotations

from dagster._core.libraries import DagsterLibraryRegistry

from .snowflake_pyspark_type_handler import (
    SnowflakePySparkIOManager as SnowflakePySparkIOManager,
    SnowflakePySparkTypeHandler as SnowflakePySparkTypeHandler,
    snowflake_pyspark_io_manager as snowflake_pyspark_io_manager,
)
from .version import __version__ as __version__

DagsterLibraryRegistry.register("dagster-snowflake-pyspark", __version__)
