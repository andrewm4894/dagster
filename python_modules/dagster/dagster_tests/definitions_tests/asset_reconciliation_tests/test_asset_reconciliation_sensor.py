import json
from typing import Sequence

import pendulum
import pytest
from dagster import (
    AssetMaterialization,
    AssetSelection,
    DagsterInstance,
    StaticPartitionsDefinition,
    asset,
    build_asset_reconciliation_sensor,
    build_sensor_context,
    job,
    op,
    repository,
)
from dagster._check import CheckError
from dagster._core.definitions.asset_graph import (
    AssetGraph,
)
from dagster._core.definitions.asset_reconciliation_sensor import (
    AutoMaterializeAssetEvaluation,
    build_auto_materialize_asset_evaluations,
)
from dagster._core.definitions.events import AssetKey, AssetKeyPartitionKey
from dagster._core.definitions.time_window_partitions import (
    HourlyPartitionsDefinition,
)

from .asset_reconciliation_scenario import (
    AssetReconciliationCursor,
    AssetReconciliationScenario,
    asset_def,
)
from .scenarios import ASSET_RECONCILIATION_SCENARIOS


@pytest.mark.parametrize(
    "scenario",
    list(ASSET_RECONCILIATION_SCENARIOS.values()),
    ids=list(ASSET_RECONCILIATION_SCENARIOS.keys()),
)
def test_reconciliation(scenario):
    instance = DagsterInstance.ephemeral()
    run_requests, _, evaluations = scenario.do_sensor_scenario(instance)

    def _sorted_evaluations(
        evaluations: Sequence[AutoMaterializeAssetEvaluation],
    ) -> Sequence[AutoMaterializeAssetEvaluation]:
        """Allows a stable ordering for comparison."""
        return sorted(
            [
                evaluation._replace(
                    partition_subsets_by_condition=sorted(
                        evaluation.partition_subsets_by_condition, key=repr
                    )
                )
                for evaluation in evaluations
            ],
            key=repr,
        )

    if scenario.expected_conditions is not None:
        reasons = {
            (
                AssetKeyPartitionKey(AssetKey.from_coercible(key[0]), key[1])
                if isinstance(key, tuple)
                else AssetKeyPartitionKey(AssetKey.from_coercible(key))
            ): rs
            for key, rs in (scenario.expected_conditions or {}).items()
        }
        assert _sorted_evaluations(
            build_auto_materialize_asset_evaluations(
                AssetGraph.from_assets(scenario.assets), reasons, dynamic_partitions_store=instance
            )
        ) == _sorted_evaluations(evaluations)

    assert len(run_requests) == len(scenario.expected_run_requests), evaluations

    def sort_run_request_key_fn(run_request):
        return (min(run_request.asset_selection), run_request.partition_key)

    sorted_run_requests = sorted(run_requests, key=sort_run_request_key_fn)
    sorted_expected_run_requests = sorted(
        scenario.expected_run_requests, key=sort_run_request_key_fn
    )

    for run_request, expected_run_request in zip(sorted_run_requests, sorted_expected_run_requests):
        assert set(run_request.asset_selection) == set(expected_run_request.asset_selection)
        assert run_request.partition_key == expected_run_request.partition_key


@pytest.mark.parametrize(
    "scenario",
    [
        ASSET_RECONCILIATION_SCENARIOS["freshness_complex_subsettable"],
    ],
)
def test_reconciliation_no_tags(scenario):
    # simulates an environment where asset_event_tags cannot be added
    instance = DagsterInstance.ephemeral()

    run_requests, _, _ = scenario.do_sensor_scenario(instance)

    assert len(run_requests) == len(scenario.expected_run_requests)

    def sort_run_request_key_fn(run_request):
        return (min(run_request.asset_selection), run_request.partition_key)

    sorted_run_requests = sorted(run_requests, key=sort_run_request_key_fn)
    sorted_expected_run_requests = sorted(
        scenario.expected_run_requests, key=sort_run_request_key_fn
    )

    for run_request, expected_run_request in zip(sorted_run_requests, sorted_expected_run_requests):
        assert set(run_request.asset_selection) == set(expected_run_request.asset_selection)
        assert run_request.partition_key == expected_run_request.partition_key


@pytest.mark.parametrize(
    "scenario",
    [
        ASSET_RECONCILIATION_SCENARIOS["diamond_never_materialized"],
        ASSET_RECONCILIATION_SCENARIOS["one_asset_daily_partitions_never_materialized"],
    ],
)
def test_sensor(scenario):
    assert scenario.cursor_from is None

    @repository
    def repo():
        return scenario.assets

    reconciliation_sensor = build_asset_reconciliation_sensor(AssetSelection.all())
    instance = DagsterInstance.ephemeral()

    with pendulum.test(scenario.current_time):
        context = build_sensor_context(instance=instance, repository_def=repo)
        result = reconciliation_sensor(context)
        assert len(list(result)) == len(scenario.expected_run_requests)

        context2 = build_sensor_context(
            cursor=context.cursor, instance=instance, repository_def=repo
        )
        result2 = reconciliation_sensor(context2)
        assert len(list(result2)) == 0


def test_bad_partition_key():
    hourly_partitions_def = HourlyPartitionsDefinition("2013-01-05-00:00")
    assets = [
        asset_def("hourly1", partitions_def=hourly_partitions_def),
        asset_def("hourly2", ["hourly1"], partitions_def=hourly_partitions_def),
    ]

    instance = DagsterInstance.ephemeral()

    @op
    def materialization_op(context):
        context.log_event(AssetMaterialization("hourly1", partition="bad partition key"))

    @job
    def materialization_job():
        materialization_op()

    materialization_job.execute_in_process(instance=instance)

    scenario = AssetReconciliationScenario(
        assets=assets, unevaluated_runs=[], asset_selection=AssetSelection.keys("hourly2")
    )
    run_requests, _, _ = scenario.do_sensor_scenario(instance)
    assert len(run_requests) == 0


def test_sensor_fails_on_auto_materialize_policy():
    scenario = ASSET_RECONCILIATION_SCENARIOS[
        "auto_materialize_policy_eager_with_freshness_policies"
    ]

    @repository
    def repo():
        return scenario.assets

    reconciliation_sensor = build_asset_reconciliation_sensor(AssetSelection.all())
    instance = DagsterInstance.ephemeral()

    context = build_sensor_context(instance=instance, repository_def=repo)

    with pytest.raises(
        CheckError,
        match=r"build_asset_reconciliation_sensor: Asset '.*' has an AutoMaterializePolicy set",
    ):
        reconciliation_sensor(context)


def test_deserialize_asset_reconciliation_cursor_backcompat():
    partitions_def = StaticPartitionsDefinition(["a", "b", "c"])

    @asset(partitions_def=partitions_def)
    def asset1():
        ...

    @asset
    def asset2():
        ...

    materialized_or_requested_root_partitions_by_asset_key = {
        asset1.key: partitions_def.subset_with_partition_keys(["a", "b"])
    }
    materialized_or_requested_root_asset_keys = {asset2.key}
    serialized = json.dumps(
        (
            25,
            [key.to_user_string() for key in materialized_or_requested_root_asset_keys],
            {
                key.to_user_string(): subset.serialize()
                for key, subset in materialized_or_requested_root_partitions_by_asset_key.items()
            },
        )
    )

    cursor = AssetReconciliationCursor.from_serialized(
        serialized, asset_graph=AssetGraph.from_assets([asset1, asset2])
    )
    assert cursor.latest_storage_id == 25
    assert (
        cursor.materialized_or_requested_root_asset_keys
        == materialized_or_requested_root_asset_keys
    )
    assert (
        cursor.materialized_or_requested_root_partitions_by_asset_key
        == materialized_or_requested_root_partitions_by_asset_key
    )
