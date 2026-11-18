"""Тесты источников данных и разбора тестового репозитория."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.repository import (
    FileRepository,
    RealRepository,
    load_test_repository,
    parse_test_repository,
)

BASE = "https://pypi.org/pypi"


class ParseTestRepositoryTest(unittest.TestCase):
    """Проверяем разбор файла."""

    def test_packages_are_parsed(self) -> None:
        packages, error = parse_test_repository("A: B C\nB: D\nD:\n")
        self.assertIsNone(error)
        self.assertEqual(
            packages, {"A": ["B", "C"], "B": ["D"], "D": []}
        )

    def test_comments_and_blank_lines_are_skipped(self) -> None:
        packages, error = parse_test_repository("# demo\n\nA: B\n")
        self.assertIsNone(error)
        self.assertEqual(packages, {"A": ["B"]})

    def test_comma_is_a_separator(self) -> None:
        packages, error = parse_test_repository("A: B, C\n")
        self.assertIsNone(error)
        self.assertEqual(packages["A"], ["B", "C"])

    def test_line_without_colon_is_rejected(self) -> None:
        packages, error = parse_test_repository("A B\n")
        self.assertIsNone(packages)
        self.assertIn("line 1", error)

    def test_empty_name_is_rejected(self) -> None:
        packages, error = parse_test_repository(": B\n")
        self.assertIsNone(packages)
        self.assertIn("line 1", error)

    def test_repeated_package_is_rejected(self) -> None:
        packages, error = parse_test_repository("A: B\nA: C\n")
        self.assertIsNone(packages)
        self.assertIn("twice", error)


class LoadTestRepositoryTest(unittest.TestCase):
    """Проверяем чтение файла с диска."""

    def test_existing_file_is_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "graph.txt")
            path.write_text("A: B\n", encoding="utf-8")
            packages, error = load_test_repository(str(path))
        self.assertIsNone(error)
        self.assertEqual(packages, {"A": ["B"]})

    def test_missing_file_is_reported(self) -> None:
        packages, error = load_test_repository("no-such-file.txt")
        self.assertIsNone(packages)
        self.assertIn("cannot read", error)


class FileRepositoryTest(unittest.TestCase):
    """Проверяем источник на словаре."""

    def test_dependencies_are_returned(self) -> None:
        repository = FileRepository({"A": ["B"]})
        data, error = repository.release("A", "1.0")
        self.assertIsNone(error)
        self.assertEqual(data["requires"], ["B"])

    def test_missing_package_is_reported(self) -> None:
        repository = FileRepository({})
        data, error = repository.release("A", "1.0")
        self.assertIsNone(data)
        self.assertIn("missing", error)


class RealRepositoryTest(unittest.TestCase):
    """Проверяем выбор между версией и последним релизом."""

    def test_version_uses_release(self) -> None:
        with patch("src.repository.fetch_release") as release:
            release.return_value = ({"name": "A"}, None)
            RealRepository(BASE).release("A", "1.0")
        release.assert_called_once_with(BASE, "A", "1.0")

    def test_empty_version_uses_latest(self) -> None:
        with patch("src.repository.fetch_latest") as latest:
            latest.return_value = ({"name": "A"}, None)
            RealRepository(BASE).release("A", "")
        latest.assert_called_once_with(BASE, "A")
