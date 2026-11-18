"""Тесты пятого этапа: DOT и отрисовка картинки."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.dot import build_dot, quote_name, render_image

GRAPH = {"A": ["B"], "B": []}


class QuoteNameTest(unittest.TestCase):
    """Проверяем кавычки в именах."""

    def test_name_is_quoted(self) -> None:
        self.assertEqual(quote_name("requests"), '"requests"')

    def test_quotes_are_escaped(self) -> None:
        self.assertEqual(quote_name('a"b'), '"a\\"b"')


class BuildDotTest(unittest.TestCase):
    """Проверяем текст DOT."""

    def test_graph_is_a_digraph(self) -> None:
        source = build_dot(GRAPH)
        self.assertTrue(source.startswith("digraph dependencies"))
        self.assertTrue(source.endswith("}"))

    def test_isolated_node_is_present(self) -> None:
        self.assertIn('"B";', build_dot(GRAPH))

    def test_edge_is_present(self) -> None:
        self.assertIn('"A" -> "B";', build_dot(GRAPH))


class RenderImageTest(unittest.TestCase):
    """Проверяем вызов Graphviz."""

    def test_command_is_called(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory, "graph.png"))
            with patch("src.dot.subprocess.run") as run:
                run.return_value.returncode = 0
                error = render_image("digraph {}", path)
        self.assertIsNone(error)
        command = run.call_args.args[0]
        self.assertEqual(command[0], "dot")
        self.assertIn(path, command)

    def test_failure_is_reported(self) -> None:
        with patch("src.dot.subprocess.run") as run:
            run.return_value.returncode = 1
            run.return_value.stderr = "bad graph"
            error = render_image("digraph {}")
        self.assertIn("bad graph", error)

    def test_missing_program_is_reported(self) -> None:
        with patch("src.dot.subprocess.run", side_effect=OSError(2, "no")):
            error = render_image("digraph {}")
        self.assertIn("cannot run", error)
