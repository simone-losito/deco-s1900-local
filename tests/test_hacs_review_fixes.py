"""Regression tests for HACS review fixes."""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "deco_s1900_local"


def load_helpers():
    spec = importlib.util.spec_from_file_location(
        "deco_s1900_local_helpers",
        INTEGRATION / "helpers.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class HacsReviewFixesTest(unittest.TestCase):
    def test_topology_text_uses_real_newlines(self) -> None:
        helpers = load_helpers()
        data = {
            "device_list": {
                "result": {
                    "device_list": [
                        {
                            "role": "master",
                            "device_id": "master",
                            "custom_nickname": "main deco",
                            "ip": "192.0.2.1",
                        },
                        {
                            "role": "slave",
                            "device_id": "satellite",
                            "parent_device_id": "master",
                            "custom_nickname": "office deco",
                            "ip": "192.0.2.2",
                            "connection_type": ["wired"],
                        },
                    ]
                }
            },
            "clients": {"result": {"client_list": []}},
        }

        topology = helpers.topology_text(data)

        self.assertIn("\n", topology)
        self.assertNotIn("\\n", topology)

    def test_versions_are_consistent(self) -> None:
        manifest = json.loads((INTEGRATION / "manifest.json").read_text())
        const = (INTEGRATION / "const.py").read_text()
        changelog = (ROOT / "CHANGELOG.md").read_text()

        self.assertEqual(manifest["version"], "1.0.1")
        self.assertRegex(const, r'VERSION = "1\.0\.1"')
        self.assertIn("## 1.0.1", changelog)
        self.assertNotIn(".".join(["11", "0", "0"]), manifest["version"])
        self.assertNotIn(".".join(["11", "0", "0"]), const)

    def test_manifest_order_matches_hassfest(self) -> None:
        manifest = json.loads((INTEGRATION / "manifest.json").read_text())
        keys = list(manifest)

        self.assertEqual(keys[:2], ["domain", "name"])
        self.assertEqual(keys[2:], sorted(keys[2:]))

    def test_config_flow_passwords_are_masked_and_host_has_no_private_default(self) -> None:
        config_flow = (INTEGRATION / "config_flow.py").read_text()

        self.assertIn("TextSelector", config_flow)
        self.assertIn("TextSelectorConfig", config_flow)
        self.assertIn("TextSelectorType.PASSWORD", config_flow)
        self.assertEqual(
            config_flow.count("vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR"),
            3,
        )
        self.assertNotIn(".".join(["192", "168", "178", "68"]), config_flow)

    def test_readme_support_link_is_publishable(self) -> None:
        readme = (ROOT / "README.md").read_text()
        internal_note = " ".join(["before", "publishing"])

        self.assertIn("slug=simone.losito", readme)
        self.assertIn("https://buymeacoffee.com/simone.losito", readme)
        self.assertNotIn(internal_note, readme.lower())

    def test_sensor_attributes_do_not_include_detailed_client_lists(self) -> None:
        sensor = (INTEGRATION / "sensor.py").read_text()

        self.assertNotIn("client_summary", sensor)
        self.assertNotIn("clients_for_node_summary", sensor)
        self.assertNotIn('attrs["clients"]', sensor)
        self.assertNotIn('"wireless_preview"', sensor)
        self.assertRegex(sensor, r"def clients_attributes\(.*online_only")
        self.assertIn('"by_node"', sensor)

    def test_no_review_blockers_remain_in_project_files(self) -> None:
        private_ip = ".".join(["192", "168", "178", "68"])
        old_version = ".".join(["11", "0", "0"])
        internal_note = " ".join(["before", "publishing"])
        checked_suffixes = {".md", ".json", ".py", ".yml", ".yaml"}

        for path in ROOT.rglob("*"):
            if ".git" in path.parts or not path.is_file():
                continue
            if path.suffix.lower() not in checked_suffixes:
                continue
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(private_ip, text, path)
            self.assertNotIn(old_version, text, path)
            self.assertNotIn(internal_note, text.lower(), path)


if __name__ == "__main__":
    unittest.main()
