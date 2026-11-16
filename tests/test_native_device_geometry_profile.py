"""Inactive pure config for one future normal IPA, not device acceptance."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class NativeDeviceGeometryProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory(prefix="ng2-device-profile-")
        cls.binary=Path(cls.directory.name)/"fixture"
        subprocess.run(["cc","-std=c99","-O2","-fno-fast-math","-ffp-contract=off",
                        "-Wall","-Wextra","-Werror","-I",str(ROOT/"patches/loopctrl"),
                        str(ROOT/"patches/loopctrl/device_geometry/NG2DeviceGeometryProfile.c"),
                        str(ROOT/"patches/loopctrl/ngg2_device_geometry_tests.c"),"-o",str(cls.binary)],check=True)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def run_fixture(self,name):
        result=subprocess.run([str(self.binary),name],capture_output=True,text=True)
        self.assertEqual(0,result.returncode,result.stderr)
        self.assertEqual("PASS pure runtime profile fixture",result.stdout.strip())

    def test_unknown_or_mixed_identity_rejects_before_profile_use(self):
        self.run_fixture("identity")

    def test_legacy_values_preserve_existing_c_coordinates(self):
        self.run_fixture("legacy")

    def test_known_spare_cannot_borrow_legacy_panel_geometry(self):
        self.run_fixture("mixed")

    def test_spare_profile_keeps_half_points_and_all_qualification_gaps(self):
        self.run_fixture("spare")

    def test_observed_hub_directions_and_pause_qr_are_candidates_only(self):
        self.run_fixture("observed-facts")

    def test_measured_floor_resume_retains_fractional_point_and_gaps(self):
        self.run_fixture("floor-resume")
