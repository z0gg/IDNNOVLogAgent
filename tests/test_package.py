import json
import tarfile
import unittest
from pathlib import Path


class PackageTests(unittest.TestCase):
    SPK = Path("artifacts/IDNNOVLogAgent-1.1.1-1014-x86_64.spk")

    def test_info_declares_conf_folder_support_and_package_checksum(self):
        import hashlib, tarfile
        with tarfile.open(self.SPK) as tf:
            info = tf.extractfile("INFO").read().decode()
            pkg = tf.extractfile("package.tgz").read()
        md5 = hashlib.md5(pkg).hexdigest()
        self.assertIn(f'checksum="{md5}"', info)

    def test_privilege_matches_proven_synocommunity_shape(self):
        import json, tarfile
        with tarfile.open(self.SPK) as tf:
            priv = json.loads(tf.extractfile("conf/privilege").read().decode())
        self.assertEqual(priv["defaults"]["run-as"], "package")
        self.assertNotIn("ctrl-script", priv)
        self.assertIn("username", priv)
        self.assertIn("groupname", priv)

    def test_info_uses_unreserved_app_namespace_and_no_adminport(self):
        import tarfile
        with tarfile.open(self.SPK) as tf:
            info = tf.extractfile("INFO").read().decode()
        self.assertNotIn("SYNO.SDS.", info)
        self.assertNotIn("adminport=", info)
        self.assertNotIn("adminprotocol=", info)
        self.assertNotIn("adminurl=", info)
        self.assertIn('dsmappname="com.idnnov.packages.IDNNOVLogAgent"', info)

    def test_no_pycache_in_payload(self):
        import tarfile
        with tarfile.open(self.SPK) as tf:
            with tarfile.open(fileobj=tf.extractfile("package.tgz"), mode="r:gz") as pt:
                names = pt.getnames()
        offenders = [n for n in names if "__pycache__" in n or n.endswith(".pyc")]
        self.assertEqual(offenders, [])

    def test_no_python_dependency_check(self):
        import tarfile
        with tarfile.open(self.SPK) as tf:
            info = tf.extractfile("INFO").read().decode()
        self.assertNotIn("install_dep_packages", info)

    def test_python_finder_shipped_and_forwards_arguments(self):
        import subprocess, tarfile, tempfile
        with tarfile.open(self.SPK) as tf:
            with tarfile.open(fileobj=tf.extractfile("package.tgz"), mode="r:gz") as pt:
                members = {m.name: m for m in pt.getmembers()}
                script = pt.extractfile("bin/py").read()
        self.assertIn("bin/py", members)
        self.assertEqual(oct(members["bin/py"].mode)[-3:], "755")
        with tempfile.NamedTemporaryFile() as f:
            f.write(script); f.flush()
            result = subprocess.run(["sh", f.name, "-c", "print('PY-FINDER-OK')"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "PY-FINDER-OK")

    def test_python_callers_invoke_finder_directly(self):
        import tarfile
        with tarfile.open(self.SPK) as tf:
            postinst = tf.extractfile("scripts/postinst").read().decode()
            with tarfile.open(fileobj=tf.extractfile("package.tgz"), mode="r:gz") as pt:
                api = pt.extractfile("bin/api.cgi").read().decode()
        for script in (postinst, api):
            self.assertNotIn('PY="$(' , script)
            self.assertIn('/bin/py" -m idnnov_agent.', script)

    def test_parser_config_and_persistent_service_log_are_shipped(self):
        import tarfile
        with tarfile.open(self.SPK) as tf:
            service = tf.extractfile("scripts/service-setup").read().decode()
            with tarfile.open(fileobj=tf.extractfile("package.tgz"), mode="r:gz") as pt:
                parser = pt.extractfile("etc/parsers.conf").read().decode()
        self.assertIn("Name        syslog-rfc5424", parser)
        self.assertIn("Time_Strict Off", parser)
        self.assertIn('fluent-bit.log', service)
        self.assertNotIn('>/dev/null 2>&1', service)

    def test_required_dsm_metadata_and_ui(self):
        self.assertTrue(self.SPK.is_file())
        with tarfile.open(self.SPK) as outer:
            info = outer.extractfile("INFO").read().decode()
            self.assertIn('version="1.1.1-1014"', info)
            self.assertIn('os_min_ver="7.2-72806"', info)
            for arch in ("r1000", "r1000nk", "v1000", "v1000nk", "geminilake", "apollolake", "epyc7002"):
                self.assertIn(arch, info)
            self.assertIn('dsmuidir="ui"', info)
            self.assertIn('dsmappname="com.idnnov.packages.IDNNOVLogAgent"', info)

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

    def test_package_icons_are_real_transparent_pngs_at_dsm_sizes(self):
        import struct
        with tarfile.open(self.SPK) as outer:
            for name, expected in (("PACKAGE_ICON.PNG", 64), ("PACKAGE_ICON_256.PNG", 256)):
                data = outer.extractfile(name).read()
                self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
                width, height, depth, color_type = struct.unpack(">IIBB", data[16:26])
                self.assertEqual((width, height), (expected, expected))
                self.assertEqual(depth, 8)
                self.assertEqual(color_type, 6, "icon must retain RGBA transparency")

    def test_package_never_requests_root(self):
        with tarfile.open(self.SPK) as outer:
            privilege = json.load(outer.extractfile("conf/privilege"))
        self.assertEqual(privilege["defaults"]["run-as"], "package")
        self.assertNotIn("ctrl-script", privilege)

    def test_no_resource_declarations_shipped(self):
        # Regression for the GRLAROCHE-SRV start_failed: a string-form
        # usr-local-linker resource ("lib": "lib") fails DSM resource
        # acquisition at prepare_start ("Failed to acquire startup worker").
        # The binary links only against base glibc, so no resource is needed.
        with tarfile.open(self.SPK) as outer:
            names = outer.getnames()
        self.assertNotIn("conf/resource", names)

    def test_generated_input_uses_dsm_rfc6587_octet_counting(self):
        from idnnov_agent.config import render_fluent_bit
        rendered = render_fluent_bit(
            {"collector_url": "https://logs.idnnov.com", "organization": "3IpSzrDn5K5UpPiprhpEXsmj3bR", "company_name": "Laroche",
             "stream": "synology_logs", "nas_name": "test-nas", "device_id": "test-device", "ingest_user": ""},
            None, "/tmp/storage", "/tmp/parsers.conf")
        self.assertIn("Mode tcp", rendered)
        self.assertIn("Format octet_counting", rendered)
        self.assertIn("Parser syslog-rfc5424", rendered)
