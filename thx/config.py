# Copyright 2021 John Reese
# Licensed under the MIT License

from pathlib import Path
from typing import Optional, Any, List, Dict, Sequence, Mapping

import tomli
from trailrunner.core import project_root

from .types import Job, Config, ConfigError


def ensure_dict(value: Any, key: str) -> Dict[str, Any]:
    result: Dict[str, Any]

    if value is None:
        result = {}
    elif isinstance(value, Mapping):
        result = {k: v for k, v in value.items()}
    else:
        raise ConfigError(f"Option {key!r} must be a dictionary; {value!r} given")

    return result


def ensure_listish(value: Any, key: str) -> List[str]:
    result: List[str]

    if value is None:
        result = []
    elif isinstance(value, str):
        result = [value]
    elif isinstance(value, Sequence):
        result = list(value)
    else:
        raise ConfigError(
            f"Option {key!r} must be a string or list of strings; {value!r} given"
        )

    for elem in result:
        if not isinstance(elem, str):
            raise ConfigError(
                f"Option {key!r} must be a string or list of strings; {value!r} given"
            )

    return result


def parse_job(name: str, data: Dict[str, Any]) -> Job:
    run: List[str]
    requires: List[str]

    if isinstance(data, str):
        run = [data]
        requires = ()
    elif isinstance(data, list):
        run = ensure_listish(data, f"tool.thx.jobs.{name}")
        requires = ()
    elif isinstance(data, dict):
        run = ensure_listish(data.pop("run", None), f"tool.thx.jobs.{name}.run")
        requires = ensure_listish(
            data.pop("requires", None), f"tool.thx.jobs.{name}.requires"
        )
    else:
        raise ConfigError(
            f"Job {name!r} must be string, list of strings, or dictionary; "
            f"{data!r} given"
        )

    return Job(name=name, run=run, requires=requires)


def parse_jobs(data: Any) -> List[Job]:
    job_data = ensure_dict(data, "tool.thx.jobs")

    jobs: List[Job] = []
    for name, value in job_data.items():
        name = name.casefold()
        jobs.append(parse_job(name, value))

    return jobs


def validate_config(config: Config) -> Config:
    for name in config.default:
        if name not in config.jobs:
            raise ConfigError(f"Option tool.thx.default: undefined job {name!r}")

    for name, job in config.jobs.items():
        assert name == job.name
        for require in job.requires:
            if require not in config.jobs:
                raise ConfigError(
                    f"Option tool.thx.jobs.{name}.requires: "
                    f"undefined job {require!r}"
                )

    return config


def load_config(path: Optional[Path] = None) -> Config:
    if path is None:
        path = Path.cwd()

    root = project_root(path)
    pyproject = root / "pyproject.toml"

    if not pyproject.is_file():
        return Config()

    content = pyproject.read_text()
    data = tomli.loads(content).get("tool", {}).get("thx", {})

    default: List[str] = ensure_listish(data.pop("default", None), "tool.thx.default")
    jobs: List[Job] = parse_jobs(data.pop("jobs", {}))

    return validate_config(
        Config(default=default, jobs={cmd.name: cmd for cmd in jobs}, values=data)
    )