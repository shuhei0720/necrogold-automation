"""TEST098 mask-zero motion diagnostics remain read-only and API-bound."""
from copy import deepcopy
import unittest

from necroprobe import native_walk as native
from necroprobe.validation import ProbeError


class NativeCycleDiagnostic098Tests(unittest.TestCase):
    @staticmethod
    def report():
        return dict(schema='ngg2-native-v1', clock_id='a' * 32, device_now_ns=100,
            input_state=0, scene_changes=[dict(command_id=14, source_capture_id=234,
                observed_capture_id=240, change_mask=0, changed_tiles=0, changed_protected=0,
                state_before=2, state_after=2, goods_before=1, goods_after=1,
                replan_count=0, replan_allowed=False, target_ns=80, deadline_ns=90)],
            scene_change_details=[dict(command_id=14, source_capture_id=234,
                observed_capture_id=240, validation=11, continuous_count=0, chain_count=0,
                cell_count=0, omitted_cells=0, cells=[])])

    def test_current_api_preserves_motion_only_comparison_but_legacy_rejects_it(self):
        value = self.report()
        try:
            parsed = native._report(value, api_version=native.API_VERSION)
        except ProbeError as error:
            self.fail('current authenticated API rejected a valid read-only motion comparison: ' + str(error))
        self.assertEqual(value, parsed,
                         'a denied zero-static-change motion comparison must retain both actual capture IDs')
        for version in ('1.98.14-ngg2', '1.98.15-ngg2'):
            with self.subTest(version=version), self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
                native._report(value, api_version=version)
        with self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
            native._report(value)
        with self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
            native._report(value, depth=1, api_version=native.API_VERSION)

    def test_zero_mask_requires_matching_motion_denial_and_all_static_permission_counts_zero(self):
        variants = []
        for key, value in (('changed_tiles', 1), ('changed_protected', 1), ('state_after', 1),
                           ('goods_after', 0), ('replan_count', 1), ('replan_allowed', True)):
            item = self.report(); item['scene_changes'][0][key] = value; variants.append((key, item))
        for key, value in (('command_id', 15), ('source_capture_id', 235), ('observed_capture_id', 241),
                           ('validation', 10), ('continuous_count', 1), ('chain_count', 1),
                           ('omitted_cells', 1)):
            item = self.report(); item['scene_change_details'][0][key] = value; variants.append((key, item))
        item = self.report(); item.pop('scene_change_details'); variants.append(('missing_details', item))
        item = self.report(); item['scene_change_details'] = []; variants.append(('empty_details', item))
        item = self.report(); item['scene_change_details'][0].update(cell_count=1,
            cells=[dict(x=0, y=0, tile_before=1, tile_after=1, protected_before=0, protected_after=0)])
        variants.append(('cell_count', item))
        item = self.report(); item['scene_changes'][0]['replan_allowed'] = 0
        variants.append(('integer_permission', item))
        for key, value in variants:
            with self.subTest(fault=key), self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
                native._report(value, api_version=native.API_VERSION)
        unchanged = deepcopy(self.report())
        ordinary = unchanged['scene_changes'][0]
        ordinary.update(change_mask=4, changed_tiles=1, replan_count=1, replan_allowed=True)
        unchanged['scene_change_details'][0].update(validation=2, continuous_count=1, chain_count=1,
            cell_count=1, cells=[dict(x=5, y=4, tile_before=1, tile_after=3,
                                    protected_before=0, protected_after=0)])
        self.assertEqual(unchanged, native._report(unchanged, api_version=native.API_VERSION),
                         'normal nonzero diagnostics keep their existing schema')


if __name__ == '__main__':
    unittest.main()
