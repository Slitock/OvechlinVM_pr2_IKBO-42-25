"""Тесты первого этапа."""

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from src.main import (
    check_filter,
    check_package,
    check_repository,
    check_version,
    main,
    read_options,
)

URL = "https://pypi.org/pypi"


class ReadOptionsTest(unittest.TestCase):
    """Проверяем чтение параметров из аргументов."""

    def test_all_options_are_read(self) -> None:
        options, error = read_options(
            ["-p", "requests", "-r", URL, "-m", "real", "-V", "2.31.0"]
        )
        self.assertIsNone(error)
        self.assertEqual(options["package"], "requests")
        self.assertEqual(options["repository"], URL)
        self.assertEqual(options["mode"], "real")
        self.assertEqual(options["version"], "2.31.0")

    def test_long_names_are_read(self) -> None:
        options, error = read_options(
            ["--package", "flask", "--repository", URL, "--version", "3.0.0"]
        )
        self.assertIsNone(error)
        self.assertEqual(options["package"], "flask")

    def test_defaults_are_used(self) -> None:
        options, error = read_options(["-p", "click", "-r", URL, "-V", "8.1"])
        self.assertIsNone(error)
        self.assertEqual(options["mode"], "real")
        self.assertEqual(options["filter"], "")

    def test_spaces_are_removed(self) -> None:
        options, error = read_options(["-p", " click ", "-V", " 8.1 "])
        self.assertIsNone(error)
        self.assertEqual(options["package"], "click")
        self.assertEqual(options["version"], "8.1")

    def test_unknown_flag_gives_error(self) -> None:
        options, error = read_options(["--colour", "red"])
        self.assertIn("unknown option", error)

    def test_missing_value_gives_error(self) -> None:
        options, error = read_options(["-p"])
        self.assertIn("missing value", error)


class CheckPackageTest(unittest.TestCase):
    """Проверяем правила для имени пакета."""

    def test_good_names_pass(self) -> None:
        for name in ("A", "requests", "zope.interface", "a-b", "x_y2"):
            self.assertIsNone(check_package(name))

    def test_empty_name_is_rejected(self) -> None:
        self.assertIn("empty", check_package(""))

    def test_separator_on_the_edge_is_rejected(self) -> None:
        for name in ("A_", "-A", "A.", ".A"):
            self.assertIn("invalid", check_package(name))

    def test_too_long_name_is_rejected(self) -> None:
        self.assertIn("longer", check_package("a" * 129))


class CheckVersionTest(unittest.TestCase):
    """Проверяем правила для версии."""

    def test_good_versions_pass(self) -> None:
        for version in ("1", "2.31.0", "8.1"):
            self.assertIsNone(check_version(version))

    def test_text_is_rejected(self) -> None:
        self.assertIn("invalid", check_version("latest"))

    def test_empty_version_is_rejected(self) -> None:
        self.assertIn("empty", check_version(""))

    def test_double_dot_is_rejected(self) -> None:
        self.assertIn("invalid", check_version("1..0"))


class CheckFilterTest(unittest.TestCase):
    """Проверяем правила для фильтра."""

    def test_plain_substring_passes(self) -> None:
        self.assertIsNone(check_filter("test"))
        self.assertIsNone(check_filter(""))

    def test_space_is_rejected(self) -> None:
        self.assertIn("whitespace", check_filter("two words"))

    def test_comma_is_rejected(self) -> None:
        self.assertIn("whitespace", check_filter("a,b"))


class CheckRepositoryTest(unittest.TestCase):
    """Проверяем, что режим задаёт смысл пути."""

    def test_url_passes_in_real_mode(self) -> None:
        self.assertIsNone(check_repository(URL, "real"))

    def test_file_path_is_rejected_in_real_mode(self) -> None:
        self.assertIn("http or https", check_repository("graph.txt", "real"))

    def test_url_without_host_is_rejected(self) -> None:
        self.assertIn("no host", check_repository("https://", "real"))

    def test_existing_file_passes_in_test_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "graph.txt")
            path.write_text("A: B\n", encoding="utf-8")
            self.assertIsNone(check_repository(str(path), "test"))

    def test_missing_file_is_rejected_in_test_mode(self) -> None:
        self.assertIn("not found", check_repository("no.txt", "test"))


class MainTest(unittest.TestCase):
    """Проверяем вывод и коды возврата."""

    def run_main(self, argv: list[str]) -> tuple[int, str, str]:
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_options_are_printed(self) -> None:
        code, output, _ = self.run_main(
            ["-p", "requests", "-r", URL, "-V", "2.31.0"]
        )
        self.assertEqual(code, 0)
        lines = output.strip().splitlines()
        self.assertTrue(lines[0].startswith("package:"))
        self.assertTrue(lines[0].endswith("requests"))
        self.assertTrue(lines[-1].startswith("filter:"))
        self.assertTrue(lines[-1].endswith("(none)"))

    def test_bad_option_gives_code_two(self) -> None:
        code, _, error = self.run_main(
            ["-p", "bad name", "-r", URL, "-V", "1.0"]
        )
        self.assertEqual(code, 2)
        self.assertIn("error:", error)

    def test_test_mode_without_file_gives_code_two(self) -> None:
        code, _, error = self.run_main(
            ["-p", "A", "-r", "no.txt", "-m", "test", "-V", "1.0"]
        )
        self.assertEqual(code, 2)
        self.assertIn("not found", error)
