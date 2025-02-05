#  Copyright 2022 The Neursafe FL Authors. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# pylint:disable=broad-except, too-many-arguments
"""subcommmand of get job.
"""
from io import BytesIO
import json
import sys

from absl import logging
import click

from neursafe_fl.python.cli.core.context import PASS_CONTEXT, LOG_FILE
from neursafe_fl.python.cli.core.data_client import DataClient
from neursafe_fl.python.cli.core.job import Job
from neursafe_fl.python.cli.core.util import parse_job_id
from neursafe_fl.python.cli.core.model import Model

METRICS_FILE = "/metrics.json"


@click.group("get", short_help="Get job, model or config.")
def cli():
    """Get job, model command, or get config."""


@cli.command("jobs", short_help="Get jobs.")
@click.argument("namespace")
@click.argument("job_id", required=False, default=None)
@click.option("-f", "--job-config", required=False, default=None,
              type=click.Path(exists=True, readable=True),
              help=("The config path for job, a json config."))
@click.option("-w", "--workspace", required=False, default=None,
              type=click.Path(exists=True, readable=True),
              help=("The workspace for job, "
                    "there must config.json in workspace."))
@click.option("-o", "--output", default=None,
              type=click.Choice(['yaml', 'json'], case_sensitive=False),
              help="Show all item in yaml or json config.")
@PASS_CONTEXT
def get_jobs(ctx, namespace, output, job_id=None, job_config=None,
             workspace=None):
    """Get jobs.
    """
    try:
        _id = parse_job_id(job_id, job_config, workspace)
        if _id:
            __show_job(ctx, namespace, _id, output)
        else:
            __show_jobs(ctx, namespace)
    except Exception as err:
        logging.exception(str(err))
        click.echo("Error message: %s, the detail see %s" % (
            str(err), LOG_FILE))
        sys.exit(1)


@cli.command("job", short_help="Get job.")
@click.argument("namespace")
@click.argument("job_id", required=False, default=None)
@click.option("-f", "--job-config", required=False, default=None,
              type=click.Path(exists=True, readable=True),
              help=("The config path for job, a json config."))
@click.option("-w", "--workspace", required=False, default=None,
              type=click.Path(exists=True, readable=True),
              help=("The workspace for job, "
                    "there must config.json in workspace."))
@click.option("-o", "--output", default=None,
              type=click.Choice(['yaml', 'json'], case_sensitive=False),
              help="Show all item in yaml or json config.")
@PASS_CONTEXT
def get_job(ctx, namespace, output, job_id=None, job_config=None,
            workspace=None):
    """Get job.
    """
    try:
        _id = parse_job_id(job_id, job_config, workspace)
        if _id:
            __show_job(ctx, namespace, _id, output)
        else:
            __show_jobs(ctx, namespace)
    except Exception as err:
        logging.exception(str(err))
        click.echo("Error message: %s, the detail see %s" % (
            str(err), LOG_FILE))
        sys.exit(1)


@cli.command("namespace", short_help="Get user's namespace.")
@PASS_CONTEXT
def get_namespace(ctx):
    """List namespaces.
    """
    try:
        data_client = DataClient(ctx.get_data_server(), ctx.get_user(),
                                 ctx.get_password(),
                                 ctx.get_certificate_path())
        namespaces = data_client.list_namespaces()
        click.echo("user support namespaces: %s" % namespaces)
    except Exception as err:
        logging.exception(str(err))
        click.echo("Error message: %s, the detail see %s" % (
            str(err), LOG_FILE))
        sys.exit(1)


@cli.command("config", short_help="Get config and show.")
@PASS_CONTEXT
def get_config(ctx):
    """Get job.
    """
    try:
        cmd_config = ctx.get_config()
        keys = ["api_server", "data_server", "certificate", "user", "password"]
        for key in keys:
            if key in cmd_config:
                click.echo("%s: %s" % (key, cmd_config[key]))
            else:
                click.echo("%s: none" % key)
    except Exception as err:
        logging.exception(str(err))
        click.echo("Error message: %s, the detail see %s" % (
            str(err), LOG_FILE))
        sys.exit(1)


def __show_jobs(ctx, namespace):
    fl_job = Job(ctx.get_api_server())
    job_configs = fl_job.get_jobs(namespace)
    __pretty_show_jobs(job_configs["jobs"])


def __show_job(ctx, namespace, job_id, output):
    fl_job = Job(ctx.get_api_server())
    job_config = fl_job.get_job(namespace, job_id)
    if output:
        metrics = __get_last_metrics(ctx, namespace, job_id, job_config)
        __pretty_show_job(job_config, output, metrics)
    else:
        __pretty_show_jobs([job_config])


def __pretty_show_job(job_config, output, metrics):
    job_config["metrics"] = metrics

    if output == "yaml":
        keys = ["id", "namespace", "description", "model_id", "model_path",
                "runtime", "resource", "task_entry", "scripts", "clients",
                "selector_address", "ssl", "port", "datasets", "parameters",
                "hyper_parameters", "secure_algorithm", "extenders", "output",
                "create_time", "start_time", "status", "metrics",
                "checkpoints"]

        for key in keys:
            if job_config.get(key, None):
                if isinstance(job_config.get(key), dict):
                    __show_dict(key, job_config.get(key), 4)
                else:
                    click.echo("%s: %s" % (key, job_config.get(key)))
    else:
        obj_json = json.dumps(job_config, indent=4)
        click.echo(obj_json)


def __show_dict(key, value, space_num):
    click.echo(" " * (space_num - 4) + key + ":")

    for sub_key, sub_value in value.items():
        if isinstance(sub_value, dict):
            __show_dict(sub_key, sub_value, space_num + 4)
        else:
            show_format = "{0: <%s}{1}: {2}" % space_num
            click.echo(show_format.format(" ", sub_key, sub_value))


def __pretty_show_jobs(job_configs):
    """Show job configs."""
    if job_configs:
        show_interval, new_configs = __get_show_info(job_configs)
        show_format = "{0: <%s}{1: <12}{2: <12}{3: <15}" % show_interval
        click.echo(show_format.format("id", "status",
                                      "progress", "create time"))
        for item in new_configs:
            click.echo(
                show_format.format(
                    item["id"], item["status"],
                    item["progress"], item["create_time"]))


def __get_show_info(job_configs):
    """get show information."""
    output_list = []
    max_len = 0
    for job_config in job_configs:
        _id = job_config["id"]
        output_list.append({"id": _id,
                            "status": job_config["status"]["state"],
                            "progress": job_config["status"]["progress"],
                            "create_time": job_config["create_time"]})
        max_len = max(max_len, len(_id))
    if max_len <= 4:
        show_interval = 7
    else:
        show_interval = max_len + 3
    return show_interval, output_list


def __get_last_metrics(ctx, namespace, job_id, job_config):
    if not (job_config.get("output", None)
            and job_config["status"]["state"] == "FINISHED"):
        return None

    data_client = DataClient(ctx.get_data_server(), ctx.get_user(),
                             ctx.get_password(),
                             ctx.get_certificate_path())
    objs = __get_last_output(data_client, namespace, job_id, job_config)

    return __parse_metrics(data_client, namespace, objs)


def __get_last_output(data_client, namespace, job_id, job_config):
    remote_dir = "%s/fl_%s_output_V" % (job_config.get("output"), job_id)
    objs = data_client.list_objects(namespace, remote_dir)

    if "Contents" not in objs:
        return []
    objs["Contents"].sort(key=lambda obj: obj["LastModified"], reverse=True)
    return objs["Contents"][:3]


def __parse_metrics(data_client, namespace, objs):
    for obj in objs:
        if obj["Key"].endswith(METRICS_FILE):
            metrics = __load_metrics(data_client, namespace, obj)
            for key, value in metrics.items():
                if isinstance(value, list):
                    # get last metrics fi has multiply round.
                    metrics[key] = value[-1]
            return metrics
    return None


def __load_metrics(data_client, namespace, obj):
    _file = BytesIO()
    data_client.download_file(namespace, obj["Key"], _file)
    _file.seek(0)
    return json.load(_file)


@cli.command("models", short_help="Get models.")
@click.argument("namespace")
@click.argument("name", required=False, default=None)
@click.argument("version", required=False, default=None)
@click.option("-id", "--model_id", default=None, required=False,
              help="The unique id of model.")
@click.option("-o", "--output", default=None,
              type=click.Choice(['yaml', 'json'], case_sensitive=False),
              help="Show all item in yaml or json config.")
@PASS_CONTEXT
def get_models(ctx, namespace, output, name=None, version=None,
               model_id=None):
    """Get models.
    """
    try:
        fl_model = Model(ctx.get_api_server())
        if model_id:
            model = fl_model.get_model_by_id(model_id)
            _show_model_detail(model, output)
        else:
            if not name:
                # get all the model in namespace
                models = fl_model.get_models(namespace)
                _show_models(namespace, models, output)
            else:
                models = fl_model.get_model(namespace, name, version)
                if not version:  # show all the version of model
                    _show_model_versions(namespace, name, models[name])
                else:
                    _show_model_detail(models[name], output)

    except Exception as err:
        logging.exception(str(err))
        click.echo("Error message: %s, the detail see %s" % (
            str(err), LOG_FILE))
        sys.exit(1)


def _show_models(namespace, models, output):
    """Show all the model in the namespace.
    """
    del output
    click.echo("--------------------------Model List--------------------------")
    click.echo("Namespace: %s  " % namespace)
    click.echo("--------------------------------------------------------------")
    if models:
        show_format = "{0: <12}{1: <15}{2: <12}"
        click.echo(show_format.format("No.", "name", "versions_num"))
        serial = 1
        for name, model in models.items():
            click.echo(show_format.format(serial, name, len(model)))
            serial += 1
    else:
        click.echo("No models")


def _show_model_versions(namespace, name, model_versions):
    click.echo("--------------------------Model Info--------------------------")
    click.echo("namespace: %s    name: %s " % (namespace, name))
    click.echo("---------------------------Versions---------------------------")
    if model_versions:
        show_interval, simplified_info = __simplify_model_info(model_versions)
        show_format = "{0: <%s}{1: <12}{2: <12}{3: <12}{4: <15}" % show_interval
        click.echo(show_format.format("id", "version", "runtime",
                                      "state", "create_time"))
        for item in simplified_info:
            click.echo(show_format.format(item["id"], item["version"],
                                          item["runtime"], item["state"],
                                          item["create_time"]))
    else:
        click.echo("No versions of model")


def __simplify_model_info(models_info):
    output_list = []
    max_len = 0
    for model_info in models_info:
        _id = model_info["id"]
        output_list.append({"id": _id,
                            "runtime": model_info["runtime"],
                            "version": model_info["version_info"]["version"],
                            "state": model_info["state"],
                            "create_time": model_info["version_info"]["time"]})
        max_len = max(max_len, len(_id))
    if max_len <= 4:
        show_interval = 7
    else:
        show_interval = max_len + 3
    return show_interval, output_list


def _show_model_detail(model_info, output):
    """Show the model with detail information.
    """
    if not model_info:
        click.echo("Not found.")
        return

    if isinstance(model_info, list):
        model_info = model_info[0]

    show_keys = ["namespace", "name", "runtime", "id", "state", "version_info",
                 "model_path", "error_msg"]

    if output == "yaml":
        for key in show_keys:
            if model_info.get(key, None):
                if isinstance(model_info.get(key), dict):
                    __show_dict(key, model_info.get(key), 4)
                else:
                    click.echo("%s: %s" % (key, model_info.get(key)))
    else:
        for key in list(model_info.keys()):
            if key not in show_keys:
                del model_info[key]

        obj_json = json.dumps(model_info, indent=4)
        click.echo(obj_json)


@cli.command("model", short_help="Get models, same as 'get models'.")
@click.argument("namespace")
@click.argument("name", required=False, default=None)
@click.argument("version", required=False, default=None)
@click.option("-id", "--model_id", default=None, required=False,
              help="The unique id of model.")
@click.option("-o", "--output", default=None,
              type=click.Choice(['yaml', 'json'], case_sensitive=False),
              help="Show all item in yaml or json config.")
@PASS_CONTEXT
def get_model(ctx, namespace, output, name=None, version=None,
              model_id=None):
    """Get model.
    """
    try:
        fl_model = Model(ctx.get_api_server())
        if model_id:
            model = fl_model.get_model_by_id(model_id)
            _show_model_detail(model, output)
        else:
            if not name:
                # get all the model in namespace
                models = fl_model.get_models(namespace)
                _show_models(namespace, models, output)
            else:
                models = fl_model.get_model(namespace, name, version)
                if not version:  # show all the version of model
                    _show_model_versions(namespace, name, models[name])
                else:
                    _show_model_detail(models[name], output)

    except Exception as err:
        logging.exception(str(err))
        click.echo("Error message: %s, the detail see %s" % (
            str(err), LOG_FILE))
        sys.exit(1)
