import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('selection', ROOT / 'scripts/run_workflow_checks.py')
selection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selection)


class CheckSelectionTests(unittest.TestCase):
    def test_records_only_use_document_validation(self):
        result = selection.select_checks(['requirements/REQ-0001.md', 'logs/project-checks/run/result.json',
                                          'releases/App-1.0.0-1.md'])
        self.assertEqual([selection.DOCUMENTS], result)

    def test_teamflow_tool_selects_related_tests(self):
        result = selection.select_checks([selection.SKILL + 'scripts/teamflow.py'])
        self.assertIn('test_teamflow', result)
        self.assertIn('test_consumer_release', result)

    def test_template_selects_consumers_and_unknown_is_full(self):
        result = selection.select_checks([selection.SKILL + 'references/templates/feature.md'])
        self.assertIn(selection.TEMPLATE, result)
        self.assertIn('test_consumer_release', result)
        self.assertIsNone(selection.select_checks(['unknown.bin']))


if __name__ == '__main__':
    unittest.main()
