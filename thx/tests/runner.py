# Copyright 2021 John Reese
# Licensed under the MIT License

import asyncio
from functools import wraps
from typing import Callable, Any, TypeVar
from unittest import TestCase
from unittest.mock import patch, Mock

from .. import runner
from ..types import Result, Job, Config

T = TypeVar("T")


def async_test(fn: Callable[..., T]) -> Callable[..., T]:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            loop = asyncio.new_event_loop()
            return loop.run_until_complete(fn(*args, **kwargs))  # type: ignore
        finally:
            loop.stop()
            loop.close()

    return wrapper


class RunnerTest(TestCase):
    @patch("thx.runner.shutil.which")
    def test_which(self, which_mock: Mock) -> None:
        with self.subTest("found"):
            which_mock.side_effect = lambda b: f"/usr/bin/{b}"
            self.assertEqual("/usr/bin/frobfrob", runner.which("frobfrob", Config()))

        with self.subTest("not found"):
            which_mock.side_effect = None
            which_mock.return_value = None
            self.assertEqual("frobfrob", runner.which("frobfrob", Config()))

    @patch("thx.runner.which")
    def test_render_command(self, which_mock: Mock) -> None:
        which_mock.return_value = "/opt/bin/frobfrob"
        config = Config(values={"module": "alpha"})
        result = runner.render_command("frobfrob check {module}.tests", config)
        self.assertEqual(["/opt/bin/frobfrob", "check", "alpha.tests"], result)

    @patch("thx.runner.shutil.which", return_value=None)
    def test_prepare_command(self, which_mock: Mock) -> None:
        config = Config(values={"module": "beta"})
        run = [
            "echo 'hello world'",
            "flake8 {module}",
            "python -m {module}.tests",
        ]
        job = Job(name="foo", run=run)

        expected = [
            runner.Step(cmd=["echo", "hello world"], config=config),
            runner.Step(cmd=["flake8", "beta"], config=config),
            runner.Step(cmd=["python", "-m", "beta.tests"], config=config),
        ]
        result = list(runner.prepare_job(job, config))
        self.assertListEqual(expected, result)

    @async_test
    async def test_job_echo(self) -> None:
        job = runner.Step(
            ["echo", "hello world"],
            Config(),
        )
        result = await job
        self.assertIsInstance(result, Result)
        self.assertEqual(
            Result(
                command=["echo", "hello world"],
                exit_code=0,
                stdout="hello world\n",
                stderr="",
            ),
            result,
        )
        self.assertTrue(result.success)