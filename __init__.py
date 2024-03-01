"""MLflow Experiment Tracking plugin.

| Copyright 2017-2023, Voxel51, Inc.
| `voxel51.com <https://voxel51.com/>`_
|
"""

import fiftyone.operators as foo
import fiftyone.operators.types as types

import mlflow


def _format_run_name(run_name):
    return run_name.replace("-", "_")


def _initialize_fiftyone_run_for_mlflow_experiment(
    dataset, experiment_name, tracking_uri=None
):
    """
    Initialize a new FiftyOne custom run given an MLflow experiment.

    Args:
    - dataset: The FiftyOne `Dataset` used for the experiment
    - experiment_name: The name of the MLflow experiment to create the run for
    """
    experiment = mlflow.get_experiment_by_name(experiment_name)
    tracking_uri = tracking_uri or "http://localhost:8080"

    config = dataset.init_run()

    config.method = "mlflow_experiment"
    config.artifact_location = experiment.artifact_location
    config.created_at = experiment.creation_time
    config.experiment_name = experiment_name
    config.experiment_id = experiment.experiment_id
    config.tracking_uri = tracking_uri
    config.tags = experiment.tags
    config.runs = []
    dataset.register_run(experiment_name, config)


def _fiftyone_experiment_run_exists(dataset, experiment_name):
    return experiment_name in dataset.list_runs()


def _add_fiftyone_run_for_mlflow_run(dataset, experiment_name, run_id):
    """
    Add an MLflow run to a FiftyOne custom run.

    Args:
    - dataset: The FiftyOne `Dataset` used for the experiment
    - run_id: The MLflow run_id to add
    """
    run = mlflow.get_run(run_id)
    run_name = run.data.tags["mlflow.runName"]

    config = dataset.init_run()
    config.method = "mlflow_run"
    config.run_name = run_name
    config.run_id = run_id
    config.run_uuid = run.info.run_uuid
    config.experiment_id = run.info.experiment_id
    config.artifact_uri = run.info.artifact_uri
    config.metrics = run.data.metrics
    config.tags = run.data.tags

    dataset.register_run(_format_run_name(run_name), config)

    ## add run to experiment
    experiment_run_info = dataset.get_run_info(experiment_name)
    experiment_run_info.config.runs.append(run_name)
    dataset.update_run_config(experiment_name, experiment_run_info.config)


def log_mlflow_run_to_fiftyone_dataset(
    sample_collection, experiment_name, run_id=None
):
    """
    Log an MLflow run to a FiftyOne custom run.

    Args:
    - sample_collection: The FiftyOne `Dataset` or `DatasetView` used for the experiment
    - experiment_name: The name of the MLflow experiment to create the run for
    - run_id: The MLflow run_id to add
    """
    dataset = sample_collection._dataset

    if not _fiftyone_experiment_run_exists(dataset, experiment_name):
        _initialize_fiftyone_run_for_mlflow_experiment(
            dataset, experiment_name
        )
    if run_id:
        _add_fiftyone_run_for_mlflow_run(dataset, experiment_name, run_id)


def get_candidate_experiments(dataset):
    urls = []
    name = dataset.name
    mlflow_experiment_runs = [
        dataset.get_run_info(r)
        for r in dataset.list_runs()
        if dataset.get_run_info(r).config.method == "mlflow_experiment"
    ]

    for mer in mlflow_experiment_runs:
        cfg = mer.config
        name = cfg.experiment_name
        try:
            uri = cfg.tracking_uri
        except:
            uri = "http://localhost:8080"
        id = cfg.experiment_id
        urls.append({"url": f"{uri}/#/experiments/{id}", "name": name})

    return {"urls": urls}


class OpenMLFlowPanel(foo.Operator):
    @property
    def config(self):
        _config = foo.OperatorConfig(
            name="open_mlflow_panel",
            label="Open MLFlow Panel",
            unlisted=False,
        )
        _config.icon = "/assets/mlflow.svg"
        return _config

    def resolve_placement(self, ctx):
        return types.Placement(
            types.Places.SAMPLES_GRID_SECONDARY_ACTIONS,
            types.Button(
                label="Open MLFlow Panel",
                prompt=False,
                icon="/assets/mlflow.svg",
            ),
        )

    def execute(self, ctx):
        ctx.trigger(
            "open_panel",
            params=dict(
                name="MLFlowPanel", isActive=True, layout="horizontal"
            ),
        )


class GetExperimentURLs(foo.Operator):
    @property
    def config(self):
        return foo.OperatorConfig(
            name="get_mlflow_experiment_urls",
            label="MLFlow: Get experiment URLs",
            unlisted=True,
        )

    def execute(self, ctx):
        return get_candidate_experiments(ctx.dataset)


def register(p):
    p.register(OpenMLFlowPanel)
    p.register(GetExperimentURLs)
