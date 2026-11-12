"""Тесты второго этапа: запрос к PyPI и разбор зависимостей."""

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from src.main import main
from src.pypi import (
    fetch_release,
    print_dependencies,
    release_url,
    split_requirement,
)

BASE = "https://pypi.org/pypi"
URL = "https://pypi.org/pypi/requests/2.31.0/json"


class FakeResponse:
    """Ответ сервера с заранее заданным телом."""

    def __init__(self, body: bytes) -> None:
        self.body = body

    def read(self) -> bytes:
        """Возвращает тело ответа."""
        return self.body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> bool:
        return False


def payload(requires: list[str]) -> bytes:
    """Собирает ответ PyPI с заданными зависимостями."""
    data = {
        "info": {
            "name": "requests",
            "version": "2.31.0",
            "requires_dist": requires,
        }
    }
    return json.dumps(data).encode("utf-8")


def open_with(body: bytes):
    """Подменяет urlopen так, чтобы он вернул заданное тело."""
    return patch(
        "src.pypi.urllib.request.urlopen",
        return_value=FakeResponse(body),
    )


class ReleaseUrlTest(unittest.TestCase):
    """Проверяем сборку адреса."""

    def test_url_is_built(self) -> None:
        self.assertEqual(release_url(BASE, "requests", "2.31.0"), URL)

    def test_trailing_slash_is_removed(self) -> None:
        self.assertEqual(release_url(BASE + "/", "requests", "2.31.0"), URL)


class FetchReleaseTest(unittest.TestCase):
    """Проверяем загрузку данных о релизе."""

    def test_requires_are_returned(self) -> None:
        body = payload(["idna (<4,>=2.5)"])
        with open_with(body):
            data, error = fetch_release(BASE, "requests", "2.31.0")
        self.assertIsNone(error)
        self.assertEqual(data["name"], "requests")
        self.assertEqual(data["requires"], ["idna (<4,>=2.5)"])

    def test_missing_requires_gives_empty_list(self) -> None:
        body = json.dumps({"info": {"name": "click"}}).encode("utf-8")
        with open_with(body):
            data, error = fetch_release(BASE, "click", "8.1.7")
        self.assertIsNone(error)
        self.assertEqual(data["requires"], [])

    def test_http_error_is_reported(self) -> None:
        error = HTTPError(URL, 404, "Not Found", {}, None)
        with patch("src.pypi.urllib.request.urlopen", side_effect=error):
            data, message = fetch_release(BASE, "ghost", "1.0")
        self.assertIsNone(data)
        self.assertIn("404", message)

    def test_network_error_is_reported(self) -> None:
        with patch(
            "src.pypi.urllib.request.urlopen",
            side_effect=URLError("boom"),
        ):
            data, message = fetch_release(BASE, "requests", "2.31.0")
        self.assertIsNone(data)
        self.assertIn("cannot reach", message)

    def test_broken_json_is_reported(self) -> None:
        with open_with(b"<html>"):
            data, message = fetch_release(BASE, "requests", "2.31.0")
        self.assertIsNone(data)
        self.assertIn("broken JSON", message)

    def test_empty_info_is_reported(self) -> None:
        body = json.dumps({"info": {}}).encode("utf-8")
        with open_with(body):
            data, message = fetch_release(BASE, "requests", "2.31.0")
        self.assertIsNone(data)
        self.assertIn("no package information", message)


class SplitRequirementTest(unittest.TestCase):
    """Проверяем разбор строк requires_dist."""

    def test_name_without_condition(self) -> None:
        self.assertEqual(split_requirement("certifi"), ("certifi", "", ""))

    def test_name_with_condition(self) -> None:
        self.assertEqual(
            split_requirement("idna (<4,>=2.5)"),
            ("idna", "<4,>=2.5", ""),
        )

    def test_name_without_parentheses(self) -> None:
        self.assertEqual(
            split_requirement("Werkzeug>=2.3.7"),
            ("Werkzeug", ">=2.3.7", ""),
        )

    def test_name_with_marker(self) -> None:
        text = 'PySocks (!=1.5.7,>=1.5.6) ; extra == "socks"'
        name, condition, marker = split_requirement(text)
        self.assertEqual(name, "PySocks")
        self.assertEqual(condition, "!=1.5.7,>=1.5.6")
        self.assertEqual(marker, 'extra == "socks"')


class PrintDependenciesTest(unittest.TestCase):
    """Проверяем печать прямых зависимостей."""

    def test_lines_are_printed(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            print_dependencies(
                "requests", "2.31.0", ["idna (<4,>=2.5)", "certifi"]
            )
        text = out.getvalue()
        self.assertIn("direct dependencies (2)", text)
        self.assertIn("  - idna <4,>=2.5", text)
        self.assertIn("  - certifi", text)


class MainStageTwoTest(unittest.TestCase):
    """Проверяем связку main с репозиторием."""

    def test_dependencies_are_printed(self) -> None:
        out = io.StringIO()
        with open_with(payload(["idna (<4,>=2.5)"])):
            with redirect_stdout(out):
                code = main(["-p", "requests", "-r", BASE, "-V", "2.31.0"])
        self.assertEqual(code, 0)
        self.assertIn("idna <4,>=2.5", out.getvalue())

    def test_network_error_gives_code_one(self) -> None:
        err = io.StringIO()
        with patch(
            "src.pypi.urllib.request.urlopen",
            side_effect=URLError("boom"),
        ):
            with redirect_stdout(io.StringIO()):
                with redirect_stderr(err):
                    code = main(
                        ["-p", "requests", "-r", BASE, "-V", "2.31.0"]
                    )
        self.assertEqual(code, 1)
        self.assertIn("error:", err.getvalue())
