import json
import tarfile
import unittest
from pathlib import Path


class PackageTests(unittest.TestCase):
    SPK = Path("artifacts/IDNNOVLogAgent-1.0.2-1003-x86_64.spk")

    def test_required_dsm_metadata_and_ui(self):
        self.assertTrue(self.SPK.is_file())
        with tarfile.open(self.SPK) as outer:
            info = outer.extractfile("INFO").read().decode()
            self.assertIn('version="1.0.2-1003"', info)
            self.assertIn('os_min_ver="7.2-72806"', info)
            for arch in ("r1000", "r1000nk", "v1000", "v1000nk", "geminilake", "apollolake", "epyc7002"):
                self.assertIn(arch, info)
            self.assertIn('dsmuidir="ui"', info)
            self.assertIn('dsmappname="SYNO.SDS.App.IDNNOVLogAgent.Instance"', info)

    def test_dsm7_required_outer_files_exist(self):
        with tarfile.open(self.SPK) as outer:
            names = set(outer.getnames())
        for required in (
            "conf/privilege",
            "scripts/preinst",
            "scripts/start-stop-status",
            "PACKAGE_ICON.PNG",
            "PACKAGE_ICON_256.PNG",
        ):
            self.assertIn(required, names)

    def test_package_never_requests_root(self):
        with tarfile.open(self.SPK) as outer:
            privilege = json.load(outer.extractfile("conf/privilege"))
        self.assertEqual(privilege["defaults"]["run-as"], "package")
        for item in privilege.get("ctrl-script", []):
            self.assertEqual(item["run-as"], "package")
