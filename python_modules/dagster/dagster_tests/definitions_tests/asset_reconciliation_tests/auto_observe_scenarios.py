import datetime

import pendulum
from dagster import DataVersion, observable_source_asset

from .asset_reconciliation_scenario import (
    AssetReconciliationScenario,
    run_request,
)


@observable_source_asset(auto_observe_interval_minutes=30)
def asset1():
    return DataVersion("5")


@observable_source_asset(auto_observe_interval_minutes=30)
def asset2():
    return DataVersion("5")


auto_observe_scenarios = {
    "auto_observe_single_asset": AssetReconciliationScenario(
        [],
        [asset1],
        expected_run_requests=[run_request(asset_keys=["asset1"])],
    ),
    "auto_observe_dont_reobserve_immediately": AssetReconciliationScenario(
        [],
        [asset1],
        cursor_from=AssetReconciliationScenario(
            [], [asset1], expected_run_requests=[run_request(asset_keys=["asset1"])]
        ),
        expected_run_requests=[],
    ),
    "auto_observe_reobserve_after_time_passes": AssetReconciliationScenario(
        [],
        [asset1],
        cursor_from=AssetReconciliationScenario(
            [],
            [asset1],
            expected_run_requests=[run_request(asset_keys=["asset1"])],
            current_time=pendulum.parse("2020-01-01 00:00"),
        ),
        expected_run_requests=[run_request(asset_keys=["asset1"])],
        current_time=pendulum.parse("2020-01-01 00:00") + datetime.timedelta(minutes=35),
    ),
    "auto_observe_two_assets": AssetReconciliationScenario(
        [],
        [asset1, asset2],
        expected_run_requests=[run_request(asset_keys=["asset1", "asset2"])],
    ),
    "auto_observe_two_assets_different_code_locations": AssetReconciliationScenario(
        unevaluated_runs=[],
        assets=None,
        code_locations={"location-1": [asset1], "location-2": [asset2]},
        expected_run_requests=[
            run_request(asset_keys=["asset1"]),
            run_request(asset_keys=["asset2"]),
        ],
    ),
}
