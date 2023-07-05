from __future__ import annotations

from dagster import AutoMaterializePolicy, DailyPartitionsDefinition, asset, repository


### Non partitioned ##
@asset(auto_materialize_policy=AutoMaterializePolicy.eager())
def eager_upstream():
    return 3


@asset(auto_materialize_policy=AutoMaterializePolicy.eager())
def eager_downstream_1(eager_upstream):
    return eager_upstream + 1


@asset(auto_materialize_policy=AutoMaterializePolicy.lazy())
def lazy_upstream():
    return 1


@asset(auto_materialize_policy=AutoMaterializePolicy.lazy())
def lazy_downstream_1(lazy_upstream):
    return lazy_upstream + 1


### Partitioned ##


daily_partitions_def = DailyPartitionsDefinition(start_date="2023-02-01")


@asset(auto_materialize_policy=AutoMaterializePolicy.eager(), partitions_def=daily_partitions_def)
def eager_upstream_partitioned():
    return 3


@asset(auto_materialize_policy=AutoMaterializePolicy.eager(), partitions_def=daily_partitions_def)
def eager_downstream_1_partitioned(eager_upstream_partitioned):
    return eager_upstream_partitioned + 1


@asset(auto_materialize_policy=AutoMaterializePolicy.lazy(), partitions_def=daily_partitions_def)
def lazy_upstream_partitioned():
    return 1


@asset(auto_materialize_policy=AutoMaterializePolicy.lazy(), partitions_def=daily_partitions_def)
def lazy_downstream_1_partitioned(lazy_upstream_partitioned):
    return lazy_upstream_partitioned + 1


@repository
def auto_materialize_repo_1():
    return [
        eager_upstream,
        eager_downstream_1,
        lazy_upstream,
        lazy_downstream_1,
        eager_upstream_partitioned,
        eager_downstream_1_partitioned,
        lazy_upstream_partitioned,
        lazy_downstream_1_partitioned,
    ]
