"""Тесты четвертого этапа: порядок загрузки зависимостей."""

import unittest

from src.order import load_order

DEPENDENCIES = {
    "A": ["B", "C"],
    "B": ["D"],
    "C": ["D"],
    "D": [],
}

CHAIN = {"A": ["B"], "B": ["C"], "C": []}

CYCLE = {"A": ["B"], "B": ["C"], "C": ["A"]}


class LoadOrderTest(unittest.TestCase):
    """Проверяем порядок загрузки."""

    def test_dependencies_come_first(self) -> None:
        self.assertEqual(load_order(CHAIN, "A"), ["C", "B", "A"])

    def test_diamond_is_linearized(self) -> None:
        order = load_order(DEPENDENCIES, "A")
        self.assertEqual(order, ["D", "B", "C", "A"])

    def test_every_dependency_goes_first(self) -> None:
        order = load_order(DEPENDENCIES, "A")
        position = {name: index for index, name in enumerate(order)}
        for name, dependencies in DEPENDENCIES.items():
            for dependency in dependencies:
                self.assertLess(position[dependency], position[name])

    def test_cycle_terminates(self) -> None:
        order = load_order(CYCLE, "A")
        self.assertEqual(len(order), 3)
        self.assertEqual(sorted(order), ["A", "B", "C"])

    def test_unknown_package_is_alone(self) -> None:
        self.assertEqual(load_order({}, "X"), ["X"])
