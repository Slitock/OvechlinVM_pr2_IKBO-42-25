"""Тесты третьего этапа: обход графа зависимостей."""

import unittest

from src.graph import build_graph, find_node, is_filtered

DEPENDENCIES = {
    "A": ["B", "C"],
    "B": ["D"],
    "C": ["D"],
    "D": [],
}

CYCLE = {
    "A": ["B"],
    "B": ["C"],
    "C": ["A"],
}


class FakeRepository:
    """Источник зависимостей на словаре."""

    def __init__(self, packages: dict[str, list[str]]) -> None:
        self.packages = packages

    def release(
        self, name: str, version: str
    ) -> tuple[dict | None, str | None]:
        """Возвращает описание релиза из словаря."""
        if name not in self.packages:
            return None, f"missing package {name}"
        requires = [f"{item} (>=1.0)" for item in self.packages[name]]
        return {
            "name": name,
            "version": version or "1.0",
            "requires": requires,
        }, None


class BrokenRepository:
    """Источник, который всегда отвечает ошибкой."""

    def release(
        self, name: str, version: str
    ) -> tuple[dict | None, str | None]:
        """Возвращает ошибку связи."""
        return None, "cannot reach repository"


class MarkerRepository:
    """Источник, у которого все зависимости с маркером."""

    def release(
        self, name: str, version: str
    ) -> tuple[dict | None, str | None]:
        """Возвращает зависимость с маркером extra."""
        requires = ['PySocks (>=1.5) ; extra == "socks"']
        return {
            "name": name,
            "version": version,
            "requires": requires,
        }, None


def build(
    name: str = "A",
    filter_text: str = "",
    packages: dict[str, list[str]] | None = None,
) -> tuple[dict[str, list[str]] | None, str | None]:
    """Строит граф на подменённом источнике."""
    if packages is None:
        packages = DEPENDENCIES
    repository = FakeRepository(packages)
    return build_graph(repository, name, "1.0", filter_text)


class BuildGraphTest(unittest.TestCase):
    """Проверяем обход графа."""

    def test_all_packages_are_found(self) -> None:
        graph, error = build()
        self.assertIsNone(error)
        self.assertEqual(sorted(graph), ["A", "B", "C", "D"])

    def test_edges_are_recorded(self) -> None:
        graph, error = build()
        self.assertIsNone(error)
        self.assertEqual(graph["A"], ["B", "C"])
        self.assertEqual(graph["B"], ["D"])

    def test_shared_package_is_not_repeated(self) -> None:
        graph, error = build()
        self.assertIsNone(error)
        self.assertEqual(graph["B"], ["D"])
        self.assertEqual(graph["C"], ["D"])
        self.assertEqual(len(graph["D"]), 0)

    def test_name_case_is_ignored(self) -> None:
        graph = {"markupsafe": []}
        self.assertEqual(find_node(graph, "MarkupSafe"), "markupsafe")

    def test_edges_count_is_correct(self) -> None:
        graph, error = build()
        edges = 0
        for dependencies in graph.values():
            edges += len(dependencies)
        self.assertEqual(edges, 4)


class CycleTest(unittest.TestCase):
    """Проверяем, что цикл не зацикливает обход."""

    def test_cycle_is_closed(self) -> None:
        graph, error = build(packages=CYCLE)
        self.assertIsNone(error)
        self.assertEqual(sorted(graph), ["A", "B", "C"])
        self.assertEqual(graph["C"], ["A"])

    def test_all_cycle_edges_are_recorded(self) -> None:
        graph, error = build(packages=CYCLE)
        self.assertIsNone(error)
        self.assertEqual(graph["A"], ["B"])
        self.assertEqual(graph["B"], ["C"])


class FilterTest(unittest.TestCase):
    """Проверяем фильтр по подстроке."""

    def test_matching_package_is_skipped(self) -> None:
        graph, error = build(filter_text="B")
        self.assertIsNone(error)
        self.assertNotIn("B", graph)

    def test_empty_filter_keeps_everything(self) -> None:
        graph, error = build(filter_text="")
        self.assertIsNone(error)
        self.assertEqual(len(graph), 4)

    def test_case_is_ignored(self) -> None:
        self.assertTrue(is_filtered("MarkupSafe", "markup"))
        self.assertFalse(is_filtered("MarkupSafe", "zzz"))


class MarkerTest(unittest.TestCase):
    """Проверяем, что зависимости с условиями в граф не попадают."""

    def test_marked_dependency_is_skipped(self) -> None:
        graph, error = build_graph(MarkerRepository(), "A", "1.0")
        self.assertIsNone(error)
        self.assertEqual(sorted(graph), ["A"])


class ErrorTest(unittest.TestCase):
    """Проверяем передачу ошибки источника."""

    def test_root_error_is_returned(self) -> None:
        graph, error = build_graph(BrokenRepository(), "A", "1.0")
        self.assertIsNone(graph)
        self.assertIn("cannot reach", error)
