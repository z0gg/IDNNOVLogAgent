import json
import tarfile
import unittest
from pathlib import Path


class PackageTests(unittest.TestCase):
    SPK = Path("artifacts/IDNNOVLogAgent-1.0.3-1004-x86_64.spk")

    def test_info_declares_conf_folder_support_and_package_checksum(self):
        import hashlib, tarfile
        with tarfile.open(self.SPK) as tf:
            info = tf.extractfile("INFO").read().decode()
            pkg = tf.extractfile("package.tgz").read()
        self.assertIn('support_conf_folder="yes"', info)
        md5 = hashlib.md5(pkg).hexdigest()
        self.assertIn(f'checksum="{md5}"', info)

    def test_no_pycache_in_payload(self):
        import tarfile
        with tarfile.open(self.SPK) as tf:
            with tarfile.open(fileobj=tf.extractfile("package.tgz"), mode="r:gz") as pt:
                names = pt.getnames()
        offenders = [n for n in names if "__pycache__" in n or n.endswith(".pyc")]
        self.assertEqual(offenders, [])

    def test_required_dsm_metadata_and_ui(self):
        self.assertTrue(self.SPK.is_file())
        with tarfile.open(self.SPK) as outer:
            info = outer.extractfile("INFO").read().decode()
            self.assertIn('version="1.0.3-1004"', info)
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
