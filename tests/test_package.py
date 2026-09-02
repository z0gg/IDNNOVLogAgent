import json
import tarfile
import unittest
from pathlib import Path


class PackageTests(unittest.TestCase):
    def test_required_dsm_metadata_and_ui(self):
        spk = Path("artifacts/IDNNOVLogAgent-1.0.0-1001-geminilake.spk")
        self.assertTrue(spk.is_file())
        with tarfile.open(spk) as outer:
            info = outer.extractfile("INFO").read().decode()
            self.assertIn('arch="geminilake"', info)
            self.assertIn('dsmuidir="ui"', info)
            self.assertIn('dsmappname="SYNO.SDS.App.IDNNOVLogAgent.Instance"', info)

