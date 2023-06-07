from __future__ import annotations

from dagster._core.libraries import DagsterLibraryRegistry

from .executor import k8s_job_executor as k8s_job_executor
from .job import (
    DagsterK8sJobConfig as DagsterK8sJobConfig,
    construct_dagster_k8s_job as construct_dagster_k8s_job,
)
from .launcher import K8sRunLauncher as K8sRunLauncher
from .ops import (
    execute_k8s_job as execute_k8s_job,
    k8s_job_op as k8s_job_op,
)
from .version import __version__ as __version__

DagsterLibraryRegistry.register("dagster-k8s", __version__)
