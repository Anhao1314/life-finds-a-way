"""Validate the shipped files and portable installation, not model behavior."""

from pathlib import Path
import re
import shutil
import tempfile
import unittest

import yaml
from skills_ref import validate


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "life-finds-a-way"


class SkillPackageTests(unittest.TestCase):
    def test_official_reference_validator(self):
        self.assertEqual(validate(SKILL), [])

    def test_standard_yaml_types(self):
        # Check real YAML types too: skills-ref's parser coerces scalars to strings.
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        _, frontmatter, body = text.split("---", 2)
        data = yaml.safe_load(frontmatter)
        for key in ("name", "description"):
            self.assertIsInstance(data[key], str)
            self.assertTrue(data[key].strip())
        self.assertRegex(data["name"], r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        for key, value in data.get("metadata", {}).items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, str)
        self.assertTrue(body.strip())

    def test_entrypoint_stays_small(self):
        # Local maintenance budget, deliberately below the spec's 500-line advice.
        self.assertLessEqual(len((SKILL / "SKILL.md").read_text().splitlines()), 100)

    def test_charter_is_an_exact_copy(self):
        self.assertEqual(
            (SKILL / "references" / "CHARTER.md").read_bytes(),
            (ROOT / "CHARTER.md").read_bytes(),
        )

    def test_standalone_installations(self):
        # Copy only the distributable directory; no checkout or global install needed.
        for host in (".agents", ".claude"):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / host / "skills" / SKILL.name
                shutil.copytree(SKILL, target)
                self.assertEqual(validate(target), [])
                source_files = {p.relative_to(SKILL) for p in SKILL.rglob("*") if p.is_file()}
                installed_files = {p.relative_to(target) for p in target.rglob("*") if p.is_file()}
                self.assertEqual(source_files, installed_files)
                for relative in source_files:
                    self.assertEqual((SKILL / relative).read_bytes(), (target / relative).read_bytes())
                # The entrypoint uses simple inline Markdown links to bundled references.
                links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", (target / "SKILL.md").read_text())
                self.assertTrue(links, "The bundled charter must be discoverable")
                for link in links:
                    resolved = (target / link).resolve()
                    self.assertTrue(resolved.is_relative_to(target.resolve()), link)
                    self.assertTrue(resolved.is_file(), link)


if __name__ == "__main__":
    unittest.main()
