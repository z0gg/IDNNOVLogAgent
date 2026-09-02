import json
import tarfile
import unittest
from pathlib import Path


class PackageTests(unittest.TestCase):
    def test_required_dsm_metadata_and_ui(self):
        spk = Path("artifacts/IDNNOVLogAgent-1.0.1-1002-x86_64.spk")
        self.assertTrue(spk.is_file())
        with tarfile.open(spk) as outer:
            info = outer.extractfile("INFO").read().decode()
            self.assertIn('version="1.0.1-1002"', info)
            self.assertIn('os_min_ver="7.2-72806"', info)
            for arch in ("r1000", "r1000nk", "v1000", "v1000nk", "geminilake", "apollolake", "epyc7002"):
                self.assertIn(arch, info)
            self.assertIn('dsmuidir="ui"', info)
            self.assertIn('dsmappname="SYNO.SDS.App.IDNNOVLogAgent.Instance"', info)

