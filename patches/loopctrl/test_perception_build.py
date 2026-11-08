"""Host contracts for strict Perception project and compiler evidence.

These synthetic PBX/argv fixtures exercise the evidence reader.  They are not
the primary TEST049 Red, which requires the real generated TEST048 project.
"""
import ast
import copy
import hashlib
import importlib.util
import io
import json
import os
import sys
from pathlib import Path
import shlex
import tempfile
import types
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    'perception_build_checker', HERE / 'check_perception_build.py')
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def generated_project(flags=None):
    """A real-like PBX graph; the source path depends on group ancestry."""
    if flags is None:
        flags = '-O2 -fno-fast-math -ffp-contract=off'
    return {'archiveVersion': '1', 'objectVersion': '56', 'rootObject': 'PROJECT',
            'objects': {
        'PROJECT': {'isa': 'PBXProject', 'mainGroup': 'MAIN',
                    'targets': ['UITEST_TARGET', 'APP_TARGET']},
        'MAIN': {'isa': 'PBXGroup', 'children': ['UITEST_GROUP', 'APP_GROUP'],
                 'sourceTree': 'SOURCE_ROOT', 'path': ''},
        'UITEST_GROUP': {'isa': 'PBXGroup', 'path': 'LoopCtrlUITests',
                         'children': ['PERCEPTION_REF', 'NAVIGATION_REF', 'OTHER_C_REF', 'SWIFT_REF'],
                         'sourceTree': '<group>'},
        'APP_GROUP': {'isa': 'PBXGroup', 'path': 'LoopCtrl',
                      'children': ['APP_REF'], 'sourceTree': '<group>'},
        'PERCEPTION_REF': {'isa': 'PBXFileReference', 'path': 'NG2Perception.c',
                           'sourceTree': '<group>', 'lastKnownFileType': 'sourcecode.c.c'},
        'NAVIGATION_REF': {'isa': 'PBXFileReference', 'path': 'NG2Navigation.c',
                           'sourceTree': '<group>'},
        'OTHER_C_REF': {'isa': 'PBXFileReference', 'path': 'NG2Beat.c',
                        'sourceTree': '<group>'},
        'SWIFT_REF': {'isa': 'PBXFileReference', 'path': 'NG2Runtime.swift',
                      'sourceTree': '<group>'},
        'APP_REF': {'isa': 'PBXFileReference', 'path': 'App.swift',
                    'sourceTree': '<group>'},
        'PERCEPTION_BUILD': {'isa': 'PBXBuildFile', 'fileRef': 'PERCEPTION_REF',
                             'settings': {'COMPILER_FLAGS': flags}},
        'NAVIGATION_BUILD': {'isa': 'PBXBuildFile', 'fileRef': 'NAVIGATION_REF',
                             'settings': {'COMPILER_FLAGS': '-O2 -fno-fast-math -ffp-contract=off'}},
        'OTHER_C_BUILD': {'isa': 'PBXBuildFile', 'fileRef': 'OTHER_C_REF'},
        'SWIFT_BUILD': {'isa': 'PBXBuildFile', 'fileRef': 'SWIFT_REF'},
        'APP_BUILD': {'isa': 'PBXBuildFile', 'fileRef': 'APP_REF'},
        'UITEST_SOURCES': {'isa': 'PBXSourcesBuildPhase',
                           'files': ['OTHER_C_BUILD', 'PERCEPTION_BUILD', 'NAVIGATION_BUILD', 'SWIFT_BUILD']},
        'APP_SOURCES': {'isa': 'PBXSourcesBuildPhase', 'files': ['APP_BUILD']},
        'FRAMEWORKS': {'isa': 'PBXFrameworksBuildPhase', 'files': []},
        'UITEST_TARGET': {'isa': 'PBXNativeTarget', 'name': 'LoopCtrlUITests',
                          'buildPhases': ['FRAMEWORKS', 'UITEST_SOURCES']},
        'APP_TARGET': {'isa': 'PBXNativeTarget', 'name': 'LoopCtrl',
                       'buildPhases': ['APP_SOURCES']},
    }}


class NavigationProjectContractTests(unittest.TestCase):
    def test_new_project_contains_both_independent_strict_sources(self):
        profile = checker.project_contract(generated_project())
        self.assertEqual(profile['format_version'], 2)
        self.assertEqual(set(profile['sources']), set(checker.STRICT_SOURCES))
        for name, row in profile['sources'].items():
            self.assertEqual(row['source'], name)
            self.assertEqual(row['source_count'], 1)
            self.assertEqual(row['compiler_flags'], checker.FLAGS)

    def test_old049_perception_valid_navigation_missing_flags_reaches_named_assertion(self):
        project = generated_project()
        del project['objects']['NAVIGATION_BUILD']['settings']
        with self.assertRaisesRegex(checker.ProfileError,
                '^NG2Navigation_strict_O2_is_applied_once$'):
            checker.project_contract(project)

    def test_navigation_duplicate_build_is_rejected_independently(self):
        project = generated_project()
        project['objects']['UITEST_SOURCES']['files'].append('NAVIGATION_BUILD')
        with self.assertRaisesRegex(checker.ProfileError, '^navigation_project_source_count$'):
            checker.project_contract(project)

    def test_navigation_post_o0_and_fast_math_are_rejected(self):
        for suffix in (' -O0', ' -ffast-math'):
            project = generated_project()
            project['objects']['NAVIGATION_BUILD']['settings']['COMPILER_FLAGS'] += suffix
            with self.subTest(suffix=suffix), self.assertRaisesRegex(checker.ProfileError,
                    '^NG2Navigation_strict_O2_is_applied_once$'):
                checker.project_contract(project)

    def test_navigation_wrong_source_and_extra_target_are_rejected(self):
        for elsewhere in (False, True):
            project = generated_project()
            if elsewhere:
                project['objects']['NAVIGATION_REF']['path'] = 'elsewhere/NG2Navigation.c'
            else:
                project['objects']['APP_SOURCES']['files'].append('NAVIGATION_BUILD')
            with self.subTest(elsewhere=elsewhere), self.assertRaisesRegex(
                    checker.ProfileError, '^navigation_project_(wrong_source|extra_target)$'):
                checker.project_contract(project)


class PerceptionProjectContractTests(unittest.TestCase):
    def contract(self, project):
        return checker.project_contract(project, profile_version=1)

    def reject(self, project, reason):
        with self.assertRaises(checker.ProfileError) as raised:
            self.contract(project)
        self.assertEqual(str(raised.exception), reason)

    def test_generated_target_phase_groups_and_exact_flags_are_accepted(self):
        project = generated_project()
        before = copy.deepcopy(project)
        self.assertEqual(self.contract(project), {
            'format_version': 1, 'target': 'LoopCtrlUITests',
            'source': 'NG2Perception.c', 'source_count': 1,
            'compiler_flags': ['-O2', '-fno-fast-math', '-ffp-contract=off'],
        })
        self.assertEqual(project, before)

    def test_flag_list_is_accepted(self):
        self.contract(generated_project(list(checker.FLAGS)))

    def test_missing_flags_reaches_named_primary_contract_assertion(self):
        project = generated_project()
        del project['objects']['PERCEPTION_BUILD']['settings']
        self.reject(project, 'NG2Perception_strict_O2_is_applied_once')

    def test_flags_must_be_exactly_once_and_in_the_prescribed_order(self):
        cases = ['', '-O2', '-O2 -ffp-contract=off',
                 '-O2 -fno-fast-math',
                 '-O2 -fno-fast-math -ffp-contract=off -O0',
                 '-O2 -O2 -fno-fast-math -ffp-contract=off',
                 '-O2 -fno-fast-math -ffp-contract=off -ffast-math',
                 '-O2 -fno-fast-math -ffp-contract=fast',
                 '-fno-fast-math -O2 -ffp-contract=off']
        for flags in cases:
            with self.subTest(flags=flags):
                self.reject(generated_project(flags),
                            'NG2Perception_strict_O2_is_applied_once')

    def test_non_string_flag_values_are_rejected_distinctly(self):
        for flags in (False, 2, None, ['-O2', 3]):
            project = generated_project()
            project['objects']['PERCEPTION_BUILD']['settings']['COMPILER_FLAGS'] = flags
            with self.subTest(flags=flags):
                self.reject(project, 'perception_project_compiler_flags_type')

    def test_missing_object_dictionary_is_not_the_flags_assertion(self):
        self.reject({}, 'perception_project_objects')

    def test_missing_and_duplicate_named_targets_are_rejected(self):
        for duplicate in (False, True):
            project = generated_project()
            if duplicate:
                project['objects']['DUPLICATE_TARGET'] = copy.deepcopy(
                    project['objects']['UITEST_TARGET'])
            else:
                project['objects']['UITEST_TARGET']['name'] = 'DifferentUITests'
            with self.subTest(duplicate=duplicate):
                self.reject(project, 'perception_project_target')

    def test_missing_and_duplicate_sources_phases_are_rejected(self):
        for phases in (['FRAMEWORKS'], ['UITEST_SOURCES', 'UITEST_SOURCES']):
            project = generated_project()
            project['objects']['UITEST_TARGET']['buildPhases'] = phases
            with self.subTest(phases=phases):
                self.reject(project, 'perception_project_sources_phase')

    def test_missing_source_is_not_the_flags_assertion(self):
        project = generated_project()
        project['objects']['UITEST_SOURCES']['files'].remove('PERCEPTION_BUILD')
        self.reject(project, 'perception_project_source_count')

    def test_repeated_build_entry_is_rejected(self):
        project = generated_project()
        project['objects']['UITEST_SOURCES']['files'].append('PERCEPTION_BUILD')
        self.reject(project, 'perception_project_source_count')

    def test_second_build_file_for_same_reference_is_rejected(self):
        project = generated_project()
        project['objects']['PERCEPTION_BUILD_2'] = copy.deepcopy(
            project['objects']['PERCEPTION_BUILD'])
        project['objects']['UITEST_SOURCES']['files'].append('PERCEPTION_BUILD_2')
        self.reject(project, 'perception_project_source_count')

    def test_source_in_another_target_is_rejected(self):
        project = generated_project()
        project['objects']['APP_SOURCES']['files'].append('PERCEPTION_BUILD')
        self.reject(project, 'perception_project_extra_target')

    def test_build_entry_must_refer_to_an_actual_build_file(self):
        for value in (None, {'isa': 'PBXFileReference'}):
            project = generated_project()
            project['objects']['PERCEPTION_BUILD'] = value
            with self.subTest(value=value):
                self.reject(project, 'perception_project_build_file')

    def test_build_file_must_refer_to_an_actual_file_reference(self):
        for reference in ('MISSING', 'UITEST_GROUP'):
            project = generated_project()
            project['objects']['PERCEPTION_BUILD']['fileRef'] = reference
            with self.subTest(reference=reference):
                self.reject(project, 'perception_project_file_reference')

    def test_wrong_resolved_source_directory_is_rejected(self):
        project = generated_project()
        project['objects']['UITEST_GROUP']['path'] = 'Elsewhere'
        self.reject(project, 'perception_project_wrong_source')

    def test_correct_basename_in_a_nested_wrong_directory_is_rejected(self):
        project = generated_project()
        project['objects']['PERCEPTION_REF']['path'] = 'nested/NG2Perception.c'
        self.reject(project, 'perception_project_wrong_source')

    def test_renamed_source_does_not_satisfy_the_contract(self):
        project = generated_project()
        project['objects']['PERCEPTION_REF']['path'] = 'SomethingElse.c'
        self.reject(project, 'perception_project_source_count')

    def test_absolute_and_parent_relative_source_paths_are_rejected(self):
        for path in ('/LoopCtrlUITests/NG2Perception.c',
                     '../LoopCtrlUITests/NG2Perception.c'):
            project = generated_project()
            project['objects']['PERCEPTION_REF']['path'] = path
            with self.subTest(path=path):
                self.reject(project, 'perception_project_file_path')

    def test_unknown_source_tree_is_rejected(self):
        project = generated_project()
        project['objects']['PERCEPTION_REF']['sourceTree'] = '<absolute>'
        self.reject(project, 'perception_project_source_tree')

    def test_reference_with_multiple_groups_is_rejected(self):
        project = generated_project()
        project['objects']['APP_GROUP']['children'].append('PERCEPTION_REF')
        self.reject(project, 'perception_project_multiple_parents')

    def test_group_cycle_reachable_from_source_is_rejected(self):
        project = generated_project()
        project['objects']['MAIN']['sourceTree'] = '<group>'
        project['objects']['UITEST_GROUP']['children'].append('MAIN')
        self.reject(project, 'perception_project_reference_cycle')

    def test_source_root_relative_reference_is_accepted(self):
        project = generated_project()
        ref = project['objects']['PERCEPTION_REF']
        ref['sourceTree'] = 'SOURCE_ROOT'
        ref['path'] = 'LoopCtrlUITests/NG2Perception.c'
        self.contract(project)

    def test_unrelated_sources_groups_and_disconnected_cycle_are_ignored(self):
        project = generated_project()
        project['objects'].update({
            'UNUSED_A': {'isa': 'PBXGroup', 'children': ['UNUSED_B'],
                         'sourceTree': '<group>', 'path': 'unused'},
            'UNUSED_B': {'isa': 'PBXGroup', 'children': ['UNUSED_A'],
                         'sourceTree': '<group>', 'path': 'unused'},
            'UNUSED_PERCEPTION': {'isa': 'PBXFileReference',
                                  'path': 'NG2Perception.c', 'sourceTree': '<group>'},
        })
        self.contract(project)


class PerceptionEffectiveFlagsTests(unittest.TestCase):
    def test_last_optimization_is_effective_and_strict_fp_is_recorded(self):
        args = ['-DDEBUG=1', '-O0', '-O2', '-fno-fast-math', '-ffp-contract=off']
        self.assertEqual(checker.effective_flags(args), {
            'optimization': '-O2', 'fast_math': False, 'fp_contract': 'off'})

    def test_missing_strict_switches_are_rejected(self):
        for args in ([], ['-O2'], ['-O2', '-fno-fast-math'],
                     ['-O2', '-ffp-contract=off']):
            with self.subTest(args=args), self.assertRaises(checker.ProfileError):
                checker.effective_flags(args)

    def test_later_non_o2_optimization_is_rejected(self):
        for optimization in ('-O0', '-O1', '-O3', '-Os', '-Oz', '-Og', '-Ofast'):
            args = list(checker.FLAGS) + [optimization]
            with self.subTest(optimization=optimization), \
                    self.assertRaises(checker.ProfileError):
                checker.effective_flags(args)

    def test_each_unsafe_fp_switch_is_rejected_even_when_followed_by_reset(self):
        unsafe = ('-ffast-math', '-Ofast', '-funsafe-math-optimizations',
                  '-fassociative-math', '-freciprocal-math', '-ffinite-math-only',
                  '-fno-signed-zeros', '-fno-trapping-math', '-fapprox-func',
                  '-ffp-model=fast', '-ffp-model=aggressive',
                  '-ffp-model=precise', '-ffp-model=strict')
        for flag in unsafe:
            for forwarded in (False, True):
                args = (['-Xclang', flag] if forwarded else [flag]) + list(checker.FLAGS)
                with self.subTest(flag=flag, forwarded=forwarded), \
                        self.assertRaises(checker.ProfileError):
                    checker.effective_flags(args)

    def test_last_fp_contract_enabling_switch_is_rejected(self):
        for flag in ('-ffp-contract=on', '-ffp-contract=fast'):
            for forwarded in (False, True):
                args = list(checker.FLAGS) + (['-Xclang', flag] if forwarded else [flag])
                with self.subTest(flag=flag, forwarded=forwarded), \
                        self.assertRaises(checker.ProfileError):
                    checker.effective_flags(args)

    def test_later_fp_contract_off_overrides_an_earlier_enabling_switch(self):
        for flag in ('-ffp-contract=on', '-ffp-contract=fast'):
            args = [flag] + list(checker.FLAGS)
            with self.subTest(flag=flag):
                self.assertEqual(checker.effective_flags(args)['fp_contract'], 'off')

    def test_forwarded_safe_fp_switches_cannot_hide_last_effective_optimization(self):
        with self.assertRaises(checker.ProfileError):
            checker.effective_flags(list(checker.FLAGS) + ['-Xclang', '-O0'])

    def test_forwarded_strict_flags_are_rejected(self):
        with self.assertRaises(checker.ProfileError):
            checker.effective_flags([
                '-O2', '-Xclang', '-fno-fast-math', '-Xclang', '-ffp-contract=off'])

    def test_frontend_forwarding_forms_are_rejected_even_with_safe_arguments(self):
        for forwarded in (['-Xclang', '-ffp-contract=off'],
                          ['-Xclang=-ffp-contract=off'],
                          ['-Xclang', '-fno-fast-math']):
            with self.subTest(forwarded=forwarded), self.assertRaises(checker.ProfileError):
                checker.effective_flags(forwarded + list(checker.FLAGS))

    def test_independent_fp_option_families_and_aliases_are_rejected(self):
        options = [['-ffp-math=fast'], ['-ffp-model', 'fast'], ['-mdaz-ftz'],
                   ['-fdenormal-fp-math', 'positive-zero'],
                   ['-fdenormal-fp-math=positive-zero'],
                   ['-fdenormal-fp-math-f32=preserve-sign'],
                   ['-ffp-exception-behavior=ignore'],
                   ['-menable-unsafe-fp-math'], ['-fno-honor-infinities'],
                   ['-fno-honor-nans']]
        for option in options:
            with self.subTest(option=option), self.assertRaises(checker.ProfileError):
                checker.effective_flags(option + list(checker.FLAGS))

    def test_other_c_sources_keep_unmodified_o0_reference_profile(self):
        result = checker.effective_flags(['-DDEBUG=1', '-O0'], expected_optimization='-O0')
        self.assertEqual(result['optimization'], '-O0')

    def test_other_c_profile_rejects_optimization_and_unsafe_fp_changes(self):
        for args in (['-O0', '-O2'], ['-O0', '-ffast-math'],
                     ['-O0', '-Xclang', '-freciprocal-math']):
            with self.subTest(args=args), self.assertRaises(checker.ProfileError):
                checker.effective_flags(args, expected_optimization='-O0')


class PerceptionResponseFileTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        # macOS temp roots commonly alias /private/var through /var. Match
        # the production reader's canonical command cwd in every fixture.
        self.base = Path(temp.name).resolve()
        self.upstream = self.base / 'source'
        self.build = self.upstream / 'build'
        self.build.mkdir(parents=True)
        self.proof = self.base / 'proof'

    def response(self, name, contents):
        path = self.build / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents.encode() if isinstance(contents, str) else contents)
        return path

    def expand(self, args):
        return checker.expand_response_args(args, self.upstream, self.proof)

    def test_plain_argv_is_preserved_without_response_evidence(self):
        args = ['-O2', '-DNAME=two words', '-fno-fast-math', '-ffp-contract=off']
        expanded, evidence = self.expand(args)
        self.assertEqual(expanded, args)
        self.assertEqual(evidence, [])

    def test_direct_linker_loader_literals_are_data_not_response_paths(self):
        for prefix in ('@rpath', '@executable_path', '@loader_path'):
            args = ['/usr/bin/swiftc', '-Xlinker', prefix + '/LoopCtrlBroadcast.debug.dylib']
            with self.subTest(prefix=prefix):
                try:
                    expanded, evidence = self.expand(args)
                except checker.ProfileError as error:
                    self.fail('valid direct linker loader literal was rejected: ' + str(error))
                self.assertEqual(expanded, args)
                self.assertEqual(evidence, [])

    def test_loader_literal_context_tracks_flattened_nested_response_arguments(self):
        self.response('linker.rsp', '-Xlinker')
        self.response('literal.rsp', '@loader_path/Frameworks')
        self.response('nested.rsp', '-Xlinker @executable_path/Frameworks')
        for args, expected in (
                (['/usr/bin/swiftc', '@build/linker.rsp', '@rpath/library.dylib'],
                 ['/usr/bin/swiftc', '-Xlinker', '@rpath/library.dylib']),
                (['/usr/bin/swiftc', '-Xlinker', '@build/literal.rsp'],
                 ['/usr/bin/swiftc', '-Xlinker', '@loader_path/Frameworks']),
                (['/usr/bin/swiftc', '@build/nested.rsp'],
                 ['/usr/bin/swiftc', '-Xlinker', '@executable_path/Frameworks'])):
            with self.subTest(args=args):
                expanded, evidence = self.expand(args)
                self.assertEqual(expanded, expected)
                self.assertTrue(evidence)

    def test_loader_prefixes_outside_direct_linker_payload_remain_rejected(self):
        for prefix in ('@rpath', '@executable_path', '@loader_path'):
            for before in ([], ['-rpath'], ['-Xlinker', '-rpath'], ['-Xlinker', 'other']):
                with self.subTest(prefix=prefix, before=before), self.assertRaises(checker.ProfileError):
                    self.expand(['/usr/bin/swiftc', *before, prefix + '/outside'])
        for token in ('@rpathish/outside', '@rpathfile', '@unknown/outside', '@/outside'):
            with self.subTest(token=token), self.assertRaises(checker.ProfileError):
                self.expand(['/usr/bin/swiftc', '-Xlinker', token])

    def test_clang_and_unknown_compiler_loader_tokens_remain_strict_responses(self):
        outside = self.upstream / 'rpath/hidden.rsp'
        outside.parent.mkdir()
        outside.write_text('-ffast-math')
        for compiler in ([], ['/usr/bin/clang'], ['/usr/bin/not-swiftc']):
            with self.subTest(compiler=compiler), self.assertRaises(checker.ProfileError):
                self.expand([*compiler, '-Xlinker', '@rpath/hidden.rsp'])

    def test_builtin_swift_wrapper_allows_only_its_real_swiftc_payload(self):
        args = ['builtin-SwiftDriver', '--', '/usr/bin/swiftc', '-Xlinker', '@rpath/debug.dylib']
        self.assertEqual(self.expand(args), (args, []))
        for compiler in ('/usr/bin/clang', '/usr/bin/not-swiftc'):
            with self.subTest(compiler=compiler), self.assertRaises(checker.ProfileError):
                self.expand(['builtin-SwiftDriver', '--', compiler, '-Xlinker', '@rpath/debug.dylib'])

    def test_linker_payload_exception_does_not_suppress_later_response_audits(self):
        self.response('ordinary.rsp', '-DRESPONSE=1')
        args, evidence = self.expand(['/usr/bin/swiftc', '-Xlinker', '@rpath/library.dylib', '@build/ordinary.rsp'])
        self.assertEqual(args, ['/usr/bin/swiftc', '-Xlinker', '@rpath/library.dylib', '-DRESPONSE=1'])
        self.assertEqual(len(evidence), 1)
        with self.assertRaises(checker.ProfileError):
            self.expand(['/usr/bin/swiftc', '-Xlinker', '@rpath/library.dylib', '@loader_path/outside'])

    def test_nested_quoted_response_arguments_and_hashes_are_recorded(self):
        inner = self.response('nested/inner.rsp', '-fno-fast-math -ffp-contract=off')
        outer = self.response('outer.rsp', '-O2 -DNAME="two words" @build/nested/inner.rsp')
        expanded, evidence = self.expand(['-DDEBUG', '@build/outer.rsp', '-c', 'file.c'])
        self.assertEqual(expanded, ['-DDEBUG', '-O2', '-DNAME=two words',
                                    '-fno-fast-math', '-ffp-contract=off', '-c', 'file.c'])
        self.assertEqual(len(evidence), 2)
        self.assertEqual({record['sha256'] for record in evidence},
                         {hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in (outer, inner)})
        self.assertEqual({record['path'] for record in evidence},
                         {'build/outer.rsp', 'build/nested/inner.rsp'})
        for record in evidence:
            self.assertEqual(set(record), {'path', 'sha256', 'bytes', 'saved_as'})
            self.assertEqual(record['saved_as'], 'response-' + record['sha256'] + '.rsp')
            self.assertEqual((self.proof / record['saved_as']).read_bytes(),
                             (self.upstream / record['path']).read_bytes())

    def test_absolute_response_inside_build_is_accepted(self):
        path = self.response('inside.rsp', '-O2')
        expanded, evidence = self.expand(['@' + str(path)])
        self.assertEqual(expanded, ['-O2'])
        self.assertEqual(len(evidence), 1)

    def test_nested_unsafe_switch_reaches_flag_validation(self):
        self.response('inner.rsp', '-Xclang -funsafe-math-optimizations')
        self.response('outer.rsp', '@build/inner.rsp ' + shlex.join(checker.FLAGS))
        args, _ = self.expand(['@build/outer.rsp'])
        with self.assertRaises(checker.ProfileError):
            checker.effective_flags(args)

    def test_nested_aggregate_fp_model_is_rejected(self):
        for forwarded in (False, True):
            flags = ['-Xclang', '-ffp-model=precise'] if forwarded else ['-ffp-model=precise']
            self.response('inner.rsp', shlex.join(flags))
            self.response('outer.rsp', '@build/inner.rsp ' + shlex.join(checker.FLAGS))
            args, _ = self.expand(['@build/outer.rsp'])
            with self.subTest(forwarded=forwarded), self.assertRaises(checker.ProfileError):
                checker.effective_flags(args)

    def test_missing_response_is_rejected(self):
        with self.assertRaises(checker.ProfileError):
            self.expand(['@build/missing.rsp'])

    def test_outside_build_and_parent_relative_paths_are_rejected(self):
        outside = self.base / 'outside.rsp'
        outside.write_text('-O2')
        inside = self.response('inside.rsp', '-O2')
        for arg in ('@' + str(outside), '@../outside.rsp',
                    '@build/../build/inside.rsp', '@' + str(self.upstream / 'outside.rsp')):
            with self.subTest(arg=arg), self.assertRaises(checker.ProfileError):
                self.expand([arg])
        self.assertTrue(inside.is_file())

    def test_symlink_file_and_symlink_directory_are_rejected(self):
        real = self.response('real/inside.rsp', '-O2')
        (self.build / 'link.rsp').symlink_to(real)
        (self.build / 'linked-dir').symlink_to(real.parent, target_is_directory=True)
        for arg in ('@build/link.rsp', '@build/linked-dir/inside.rsp'):
            with self.subTest(arg=arg), self.assertRaises(checker.ProfileError):
                self.expand([arg])

    def test_response_replaced_by_symlink_after_initial_check_is_rejected(self):
        path = self.response('changed.rsp', '-DINSIDE=1')
        outside = self.base / 'outside.rsp'
        outside.write_text('-DOUTSIDE=1')
        original_is_file = Path.is_file
        replaced = False

        def replace_after_check(checked_path):
            nonlocal replaced
            result = original_is_file(checked_path)
            if checked_path == path and result and not replaced:
                checked_path.unlink()
                checked_path.symlink_to(outside)
                replaced = True
            return result

        with patch.object(Path, 'is_file', replace_after_check), \
                self.assertRaises(checker.ProfileError):
            self.expand(['@build/changed.rsp'])
        self.assertTrue(replaced, 'fixture did not reach its mutation point')

    def test_response_replaced_by_fifo_after_initial_check_is_rejected_before_open(self):
        path = self.response('changed.rsp', '-DINSIDE=1')
        original_is_file = Path.is_file
        replaced = False

        def replace_after_check(checked_path):
            nonlocal replaced
            result = original_is_file(checked_path)
            if checked_path == path and result and not replaced:
                checked_path.unlink()
                os.mkfifo(checked_path)
                replaced = True
            return result

        with patch.object(Path, 'is_file', replace_after_check):
            self.assert_rejected_before_open(['@build/changed.rsp'], path)
        self.assertTrue(replaced, 'fixture did not reach its mutation point')

    def test_symlink_replacement_at_final_open_is_rejected(self):
        path = self.response('changed.rsp', '-DINSIDE=1')
        outside = self.base / 'outside.rsp'
        outside.write_text('-DOUTSIDE=1')
        original_open = os.open
        replaced = False

        def replace_at_open(open_path, flags, *args, **kwargs):
            nonlocal replaced
            if os.fspath(open_path) == path.name and not replaced:
                path.unlink()
                path.symlink_to(outside)
                replaced = True
            return original_open(open_path, flags, *args, **kwargs)

        with patch.object(os, 'open', replace_at_open), self.assertRaises(checker.ProfileError):
            self.expand(['@build/changed.rsp'])
        self.assertTrue(replaced)

    def test_fifo_replacement_at_final_open_cannot_block(self):
        path = self.response('changed.rsp', '-DINSIDE=1')
        original_open = os.open
        replaced = False

        def replace_at_open(open_path, flags, *args, **kwargs):
            nonlocal replaced
            if os.fspath(open_path) == path.name and not replaced:
                self.assertTrue(flags & os.O_NONBLOCK, 'FIFO replacement could block the reader')
                path.unlink()
                os.mkfifo(path)
                replaced = True
            return original_open(open_path, flags, *args, **kwargs)

        with patch.object(os, 'open', replace_at_open), self.assertRaises(checker.ProfileError):
            self.expand(['@build/changed.rsp'])
        self.assertTrue(replaced)

    def test_parent_directory_replaced_at_open_cannot_escape_build(self):
        self.response('nested/inside.rsp', '-DINSIDE=1')
        outside = self.base / 'outside'
        outside.mkdir()
        (outside / 'inside.rsp').write_text('-DOUTSIDE=1')
        directory = self.build / 'nested'
        original_open = os.open
        replaced = False

        def replace_at_open(open_path, flags, *args, **kwargs):
            nonlocal replaced
            if os.fspath(open_path) == 'nested' and not replaced:
                directory.rename(self.build / 'old-nested')
                directory.symlink_to(outside, target_is_directory=True)
                replaced = True
            return original_open(open_path, flags, *args, **kwargs)

        with patch.object(os, 'open', replace_at_open), self.assertRaises(checker.ProfileError):
            self.expand(['@build/nested/inside.rsp'])
        self.assertTrue(replaced)

    def test_directory_and_file_descriptors_are_closed_on_success_and_rejection(self):
        self.response('inside.rsp', '-O2')
        original_open = os.open
        descriptors = []

        def record_open(*args, **kwargs):
            if reject and os.fspath(args[0]) == 'inside.rsp':
                raise OSError('injected final-open failure')
            descriptor = original_open(*args, **kwargs)
            descriptors.append(descriptor)
            return descriptor

        for reject in (False, True):
            descriptors.clear()
            with patch.object(os, 'open', record_open):
                if reject:
                    with self.assertRaises(checker.ProfileError):
                        self.expand(['@build/inside.rsp'])
                else:
                    self.expand(['@build/inside.rsp'])
            self.assertTrue(descriptors, 'fixture did not open the containing directories')
            for descriptor in descriptors:
                with self.subTest(reject=reject, descriptor=descriptor), self.assertRaises(OSError):
                    os.fstat(descriptor)

    def test_directory_is_rejected_without_attempting_to_open_it(self):
        directory = self.build / 'directory.rsp'
        directory.mkdir()
        self.assert_rejected_before_open(['@build/directory.rsp'], directory)

    def test_nonregular_fifo_is_rejected_without_attempting_to_open_it(self):
        fifo = self.build / 'pipe.rsp'
        os.mkfifo(fifo)
        self.assert_rejected_before_open(['@build/pipe.rsp'], fifo)

    def test_response_cycles_are_rejected(self):
        self.response('a.rsp', '@build/b.rsp')
        self.response('b.rsp', '@build/a.rsp')
        with self.assertRaises(checker.ProfileError):
            self.expand(['@build/a.rsp'])

    def test_more_than_eight_response_levels_are_rejected(self):
        for index in range(9):
            self.response(f'depth-{index}.rsp',
                          f'@build/depth-{index + 1}.rsp' if index < 8 else '-O2')
        with self.assertRaises(checker.ProfileError):
            self.expand(['@build/depth-0.rsp'])

    def test_eight_response_levels_are_accepted(self):
        for index in range(8):
            self.response(f'depth-{index}.rsp',
                          f'@build/depth-{index + 1}.rsp' if index < 7 else '-O2')
        args, evidence = self.expand(['@build/depth-0.rsp'])
        self.assertEqual(args, ['-O2'])
        self.assertEqual(len(evidence), 8)

    def test_more_than_32_response_files_are_rejected(self):
        for index in range(33):
            self.response(f'file-{index}.rsp', '-DDEBUG')
        with self.assertRaises(checker.ProfileError):
            self.expand([f'@build/file-{index}.rsp' for index in range(33)])

    def test_32_response_files_are_accepted(self):
        for index in range(32):
            self.response(f'file-{index}.rsp', '-DDEBUG')
        args, evidence = self.expand([f'@build/file-{index}.rsp' for index in range(32)])
        self.assertEqual(args, ['-DDEBUG'] * 32)
        self.assertEqual(len(evidence), 32)

    def assert_rejected_before_open(self, args, forbidden):
        original_open = Path.open
        original_os_open = os.open

        def guarded_open(path, *open_args, **kwargs):
            if path == forbidden:
                self.fail('response reader opened a rejected or over-budget path')
            return original_open(path, *open_args, **kwargs)

        def guarded_os_open(path, *open_args, **kwargs):
            if os.fspath(path) in (os.fspath(forbidden), forbidden.name):
                self.fail('response reader opened a rejected or over-budget path')
            return original_os_open(path, *open_args, **kwargs)

        with patch.object(Path, 'open', guarded_open), \
                patch.object(os, 'open', guarded_os_open), self.assertRaises(checker.ProfileError):
            self.expand(args)

    def test_individual_size_is_checked_before_open_and_allocation(self):
        path = self.build / 'oversized.rsp'
        with path.open('wb') as stream:
            stream.truncate(1024 * 1024 + 1)
        self.assert_rejected_before_open(['@build/oversized.rsp'], path)

    def test_total_size_is_checked_before_opening_overbudget_file(self):
        for index in range(3):
            self.response(f'large-{index}.rsp', '-DDEBUG ' + ' ' * (750 * 1024 - 8))
        self.assert_rejected_before_open(
            [f'@build/large-{index}.rsp' for index in range(3)], self.build / 'large-2.rsp')

    def test_exact_individual_and_total_byte_limits_are_accepted(self):
        contents = '-O2 ' + ' ' * (1024 * 1024 - 4)
        self.response('limit-a.rsp', contents)
        self.response('limit-b.rsp', contents)
        args, evidence = self.expand(['@build/limit-a.rsp', '@build/limit-b.rsp'])
        self.assertEqual(args, ['-O2', '-O2'])
        self.assertEqual([item['bytes'] for item in evidence], [1024 * 1024] * 2)

    def test_malformed_shell_quoting_and_invalid_utf8_are_rejected(self):
        self.response('quote.rsp', '-DNAME="unterminated')
        self.response('encoding.rsp', b'\xff-O2')
        for arg in ('@build/quote.rsp', '@build/encoding.rsp'):
            with self.subTest(arg=arg), self.assertRaises(checker.ProfileError):
                self.expand([arg])

    def test_response_token_limit_is_enforced(self):
        self.response('tokens.rsp', ' '.join(['-DDEBUG'] * 32769))
        with self.assertRaises(checker.ProfileError):
            self.expand(['@build/tokens.rsp'])

    def test_exact_token_limit_is_accepted(self):
        self.response('tokens.rsp', ' '.join(['-DDEBUG'] * 32768))
        args, _ = self.expand(['@build/tokens.rsp'])
        self.assertEqual(len(args), 32768)

    def test_response_token_limit_is_cumulative_across_files(self):
        for name in ('tokens-a.rsp', 'tokens-b.rsp'):
            self.response(name, ' '.join(['-DDEBUG'] * 20000))
        with self.assertRaises(checker.ProfileError):
            self.expand(['@build/tokens-a.rsp', '@build/tokens-b.rsp'])

    def test_file_reads_are_bounded_before_allocating_contents(self):
        self.response('bounded.rsp', '-O2')
        original_fdopen = os.fdopen
        observed_sizes = []
        testcase = self

        class BoundedRead:
            def __init__(self, stream):
                self.stream = stream

            def __enter__(self):
                self.stream.__enter__()
                return self

            def __exit__(self, *args):
                return self.stream.__exit__(*args)

            def fileno(self):
                return self.stream.fileno()

            def read(self, size=-1):
                testcase.assertGreater(size, 0, 'response contents read without a bound')
                testcase.assertLessEqual(size, 1024 * 1024 + 1)
                observed_sizes.append(size)
                return self.stream.read(size)

        def guarded_fdopen(descriptor, *args, **kwargs):
            return BoundedRead(original_fdopen(descriptor, *args, **kwargs))

        with patch.object(os, 'fdopen', guarded_fdopen):
            args, _ = self.expand(['@build/bounded.rsp'])
        self.assertEqual(args, ['-O2'])
        self.assertTrue(observed_sizes)

    def test_shell_text_in_a_response_is_only_data(self):
        marker = self.base / 'must-not-exist'
        value = '-DNAME=$(touch ' + str(marker) + ')'
        self.response('shell.rsp', shlex.join([value]))
        args, _ = self.expand(['@build/shell.rsp'])
        self.assertEqual(args, [value])
        self.assertFalse(marker.exists())


class PerceptionCompileLogTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='perception compiler ')
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.upstream = self.base / 'upstream'
        self.sources = self.upstream / 'LoopCtrlUITests'
        self.sources.mkdir(parents=True)
        self.proof = self.base / 'proof'
        self.log = self.base / 'xcodebuild.log'
        self.names = ['NG2Perception', 'NG2Beat', 'NG2Navigation', 'NG2Controller']
        for name in self.names:
            (self.sources / (name + '.c')).write_text('/* ' + name + ' fixture */\n')
        self.profile = checker.project_contract(generated_project())
        self.profile['source_sha256'] = {name: hashlib.sha256(
            (self.sources / name).read_bytes()).hexdigest() for name in checker.STRICT_SOURCES}
        self.profile['project_sha256'] = '0' * 64

    def c_command(self, name, flags=None, source=None, output=None, arch='arm64'):
        if flags is None:
            flags = list(checker.FLAGS) if name + '.c' in checker.STRICT_SOURCES else ['-O0']
        if source is None:
            source = self.sources / (name + '.c')
        if output is None:
            output = (self.upstream / 'build/LoopCtrl.build/Debug-iphoneos'
                      / 'LoopCtrlUITests.build/Objects-normal' / arch / (name + '.o'))
        return shlex.join(['/usr/bin/clang', '-target', arch + '-apple-ios16.0',
                           '-x', 'c', *flags, '-c', str(source), '-o', str(output)])

    def swift_command(self, flags=None, module='LoopCtrlUITests', driver=False):
        args = ['/usr/bin/swiftc', '-module-name', module,
                '-target', 'arm64-apple-ios16.0', *(flags or ['-Onone'])]
        if driver:
            args = ['builtin-SwiftDriver', '--', *args]
        return shlex.join(args)

    def commands(self):
        return [self.c_command(name) for name in self.names] + [
            self.swift_command(module=module) for module in sorted(checker.SWIFT_TARGETS - {checker.TARGET})
        ] + [self.swift_command()]

    def inspect(self, lines):
        self.log.write_text('\n'.join(lines) + '\n')
        with patch.object(checker, 'inspect_project', return_value=copy.deepcopy(self.profile)):
            return checker.inspect_compile_log(self.upstream, self.log, self.proof)

    def test_actual_command_shapes_record_strict_source_and_other_c_o0(self):
        result = self.inspect(['CompileC harmless build progress', *self.commands()])
        self.assertEqual(result['format_version'], 2)
        self.assertEqual(result['target'], 'LoopCtrlUITests')
        self.assertEqual(result['arch'], 'arm64')
        self.assertEqual(result['profile'], 'strict-O2-v2')
        self.assertEqual(result['source_sha256'], self.profile['source_sha256'])
        self.assertEqual(result['project_profile'], self.profile)
        self.assertEqual(len(result['perception_compiles']), 1)
        self.assertEqual(set(result['other_c_profiles']),
                         {'NG2Beat.c', 'NG2Controller.c'})
        self.assertEqual(result['swift_optimization'], '-Onone')
        self.assertEqual(result['response_files'], [])

    def test_builtin_swift_driver_shape_is_accepted(self):
        lines = self.commands()
        lines[-1] = self.swift_command(driver=True)
        self.inspect(lines)

    def test_real_swift_debug_dylib_linker_loader_arguments_are_preserved(self):
        lines = self.commands()
        flags = ['-Onone', '-Xlinker', '-install_name', '-Xlinker',
                 '@rpath/LoopCtrlBroadcast.debug.dylib', '-Xlinker', '-rpath',
                 '-Xlinker', '@executable_path/Frameworks']
        lines[-1] = self.swift_command(flags, driver=True)
        result = self.inspect(lines)
        row = next(row for row in result['swift_compiles'] if '@rpath/LoopCtrlBroadcast.debug.dylib' in row['arguments'])
        self.assertIn('@rpath/LoopCtrlBroadcast.debug.dylib', row['arguments'])
        self.assertEqual(result['swift_optimization'], '-Onone')
        self.assertEqual(result['response_files'], [])

    def test_swift_loader_literals_do_not_hide_a_later_response_optimization(self):
        response = self.upstream / 'build/hidden-after-loader.rsp'
        response.parent.mkdir(parents=True)
        response.write_text('-O')
        lines = self.commands()
        lines[-1] = self.swift_command(['-Onone', '-Xlinker', '@rpath/debug.dylib',
                                       '@build/hidden-after-loader.rsp'], driver=True)
        with self.assertRaises(checker.ProfileError):
            self.inspect(lines)

    def test_clang_linker_loader_named_response_cannot_hide_unsafe_math(self):
        hidden = self.upstream / 'rpath/hidden.rsp'
        hidden.parent.mkdir()
        hidden.write_text('-ffast-math')
        lines = self.commands()
        lines[0] = self.c_command('NG2Perception', [*checker.FLAGS, '-Xlinker', '@rpath/hidden.rsp'])
        with self.assertRaises(checker.ProfileError):
            self.inspect(lines)

    def test_actual_clang_link_only_install_names_are_not_compile_evidence(self):
        output = self.upstream / 'build/Build/Products/Debug-iphoneos/LoopCtrlLiveActivity.appex/__preview.dylib'
        link = shlex.join(['/usr/bin/clang', '-dynamiclib', '-target', 'arm64-apple-ios16.0',
            '-install_name', '@rpath/LoopCtrlLiveActivity.debug.dylib',
            '-Xlinker', '-rpath', '-Xlinker', '@executable_path/Frameworks',
            '-Xlinker', '-rpath', '-Xlinker', '@executable_path/../../Frameworks',
            '-Xlinker', '-rpath', '-Xlinker', '@loader_path/Frameworks', '-o', str(output)])
        try:
            result = self.inspect([*self.commands(), link])
        except checker.ProfileError as error:
            self.fail('actual link-only loader command was rejected: ' + str(error))
        self.assertEqual(len(result['perception_compiles']), 1)

    def test_clang_link_classification_expands_ordinary_link_response_files(self):
        response = self.upstream / 'build/link-args.rsp'
        response.parent.mkdir()
        response.write_text('-dynamiclib -install_name @rpath/LoopCtrlLiveActivity.debug.dylib')
        link = shlex.join(['/usr/bin/clang', '@build/link-args.rsp', '-o',
            str(self.upstream / 'build/Build/Products/Debug-iphoneos/libpreview.dylib')])
        result = self.inspect([*self.commands(), link])
        self.assertEqual(len(result['perception_compiles']), 1)

    def test_existing_loader_named_response_cannot_hide_the_only_compile_switch(self):
        hidden = self.upstream / 'rpath/hidden.rsp'
        hidden.parent.mkdir()
        hidden.write_text(shlex.join(shlex.split(self.c_command('NG2Perception', ['-O0']))[1:]))
        link_shape = shlex.join(['/usr/bin/clang', '-dynamiclib', '-install_name',
            '@rpath/hidden.rsp', '-o', str(self.upstream / 'build/fake.dylib')])
        with self.assertRaises(checker.ProfileError):
            self.inspect([*self.commands(), link_shape])

    def test_compile_switch_in_normal_response_restores_strict_clang_reader(self):
        response = self.upstream / 'build/hidden-compile.rsp'
        response.parent.mkdir()
        args = shlex.split(self.c_command('NG2Perception', [*checker.FLAGS,
            '-Xlinker', '@rpath/nonexistent-loader.dylib']))[1:]
        response.write_text(shlex.join(args))
        with self.assertRaises(checker.ProfileError):
            self.inspect([*self.commands(), '/usr/bin/clang @build/hidden-compile.rsp'])

    def test_clang_link_loader_parent_symlinks_fail_closed(self):
        outside = self.base / 'outside-loader'
        outside.mkdir()
        (self.upstream / 'rpath').symlink_to(outside, target_is_directory=True)
        link = '/usr/bin/clang -dynamiclib -install_name @rpath/nonexistent.dylib'
        with self.assertRaises(checker.ProfileError):
            self.inspect([*self.commands(), link])

    def test_clang_link_loader_existing_prefix_cannot_traverse_parent(self):
        (self.upstream / 'executable_path').mkdir()
        link = '/usr/bin/clang -dynamiclib -Xlinker @executable_path/../../Frameworks'
        with self.assertRaises(checker.ProfileError):
            self.inspect([*self.commands(), link])

    def test_missing_perception_or_any_other_c_compile_is_rejected(self):
        for missing in range(len(self.names)):
            lines = self.commands()
            del lines[missing]
            with self.subTest(source=self.names[missing]), self.assertRaises(checker.ProfileError):
                self.inspect(lines)

    def test_missing_target_swift_compile_is_rejected(self):
        with self.assertRaises(checker.ProfileError):
            self.inspect(self.commands()[:-1])

    def test_all_five_swift_modules_must_have_onone_evidence_in_v2(self):
        for missing in checker.SWIFT_TARGETS:
            lines = [line for line in self.commands() if
                     '-module-name ' + missing + ' ' not in line]
            with self.subTest(module=missing), self.assertRaises(checker.ProfileError):
                self.inspect(lines)

    def test_all_perception_compiles_must_have_the_strict_profile(self):
        lines = self.commands() + [self.c_command('NG2Perception', ['-O0'])]
        with self.assertRaises(checker.ProfileError):
            self.inspect(lines)

    def test_wrong_source_path_with_the_same_basename_is_rejected(self):
        lines = self.commands()
        lines[0] = self.c_command('NG2Perception',
                                  source=self.upstream / 'Other/NG2Perception.c')
        with self.assertRaises(checker.ProfileError):
            self.inspect(lines)

    def test_wrong_architecture_is_rejected(self):
        lines = self.commands()
        lines[0] = self.c_command('NG2Perception', arch='x86_64')
        with self.assertRaises(checker.ProfileError):
            self.inspect(lines)

    def test_perception_output_for_another_target_is_rejected(self):
        lines = self.commands()
        lines[0] = self.c_command('NG2Perception', output=(self.upstream
            / 'build/LoopCtrl.build/Debug-iphoneos/AnotherTarget.build'
            / 'Objects-normal/arm64/NG2Perception.o'))
        with self.assertRaises(checker.ProfileError):
            self.inspect(lines)

    def test_other_c_cannot_inherit_perception_optimization(self):
        for index, name in enumerate(self.names[1:], 1):
            if name == 'NG2Navigation':
                continue
            lines = self.commands()
            lines[index] = self.c_command(name, list(checker.FLAGS))
            with self.subTest(source=name), self.assertRaises(checker.ProfileError):
                self.inspect(lines)

    def test_navigation_compile_post_o0_is_rejected(self):
        lines = self.commands()
        lines[2] = self.c_command('NG2Navigation', list(checker.FLAGS) + ['-O0'])
        with self.assertRaises(checker.ProfileError):
            self.inspect(lines)

    def test_navigation_compile_unsafe_fp_switches_are_rejected(self):
        for option in ('-ffast-math', '-fassociative-math', '-ffp-contract=fast',
                       '-fno-honor-nans', '-Xclang'):
            lines = self.commands()
            lines[2] = self.c_command('NG2Navigation', list(checker.FLAGS) + [option])
            with self.subTest(option=option), self.assertRaises(checker.ProfileError):
                self.inspect(lines)

    def test_both_strict_sources_must_compile_exactly_once(self):
        for name in ('NG2Perception', 'NG2Navigation'):
            with self.subTest(source=name), self.assertRaisesRegex(
                    checker.ProfileError, '^perception_compile_strict_source_count$'):
                self.inspect(self.commands() + [self.c_command(name)])

    def test_navigation_wrong_source_and_target_are_rejected(self):
        for wrong_source in (False, True):
            lines = self.commands()
            if wrong_source:
                lines[2] = self.c_command('NG2Navigation',
                    source=self.upstream / 'Other/NG2Navigation.c')
            else:
                lines[2] = self.c_command('NG2Navigation', output=(self.upstream
                    / 'build/LoopCtrl.build/Debug-iphoneos/Other.build/NG2Navigation.o'))
            with self.subTest(wrong_source=wrong_source), self.assertRaises(checker.ProfileError):
                self.inspect(lines)

    def test_navigation_response_candidate_must_have_strict_profile(self):
        response = self.upstream / 'build/navigation.rsp'
        response.parent.mkdir()
        lines = self.commands()
        lines[2] = '/usr/bin/clang @build/navigation.rsp'
        for suffix in ([], ['-O0'], ['-ffast-math']):
            response.write_text(shlex.join(shlex.split(self.c_command(
                'NG2Navigation', list(checker.FLAGS) + suffix))[1:]))
            if suffix:
                with self.subTest(suffix=suffix), self.assertRaises(checker.ProfileError):
                    self.inspect(lines)
            else:
                result = self.inspect(lines)
                self.assertEqual(result['navigation_compiles'][0]['optimization'], '-O2')
                self.assertEqual(result['response_files'][0]['sha256'],
                                 hashlib.sha256(response.read_bytes()).hexdigest())

    def test_target_swift_optimization_must_remain_onone(self):
        for flags in (['-O'], ['-Onone', '-O'], ['-Osize']):
            lines = self.commands()
            lines[-1] = self.swift_command(flags)
            with self.subTest(flags=flags), self.assertRaises(checker.ProfileError):
                self.inspect(lines)

    def test_unrelated_swift_module_does_not_change_the_target_contract(self):
        self.inspect(self.commands() + [self.swift_command(['-O'], module='ExternalSDK')])

    def test_project_app_swift_module_cannot_change_optimization(self):
        with self.assertRaises(checker.ProfileError):
            self.inspect(self.commands() + [self.swift_command(['-O'], module='LoopCtrl')])

    def test_compile_response_flags_are_expanded_and_sealed(self):
        response = self.upstream / 'build/perception.rsp'
        response.parent.mkdir()
        response.write_text(shlex.join(checker.FLAGS))
        lines = self.commands()
        lines[0] = self.c_command('NG2Perception', ['@build/perception.rsp'])
        result = self.inspect(lines)
        self.assertEqual(len(result['response_files']), 1)
        record = result['response_files'][0]
        self.assertEqual(record['path'], 'build/perception.rsp')
        self.assertEqual(record['sha256'], hashlib.sha256(response.read_bytes()).hexdigest())
        self.assertEqual((self.proof / record['saved_as']).read_bytes(), response.read_bytes())

    def test_broken_response_in_a_real_compile_is_rejected(self):
        lines = self.commands()
        lines[0] = self.c_command('NG2Perception', ['@build/missing.rsp'])
        with self.assertRaises(checker.ProfileError):
            self.inspect(lines)

    def test_second_perception_compile_wholly_in_response_is_audited(self):
        response = self.upstream / 'build/hidden-all.rsp'
        response.parent.mkdir()
        response.write_text(shlex.join(shlex.split(self.c_command('NG2Perception', ['-O0']))[1:]))
        with self.assertRaises(checker.ProfileError):
            self.inspect(self.commands() + ['/usr/bin/clang @build/hidden-all.rsp'])

    def test_swift_response_optimization_is_audited_before_and_after_module_selection(self):
        build = self.upstream / 'build'
        build.mkdir()
        response = build / 'hidden-swift.rsp'
        for module_in_response in (False, True):
            if module_in_response:
                response.write_text('-module-name LoopCtrlUITests -O')
                command = '/usr/bin/swiftc -Onone @build/hidden-swift.rsp'
            else:
                response.write_text('-O')
                command = ('/usr/bin/swiftc -module-name LoopCtrlUITests'
                           ' -Onone @build/hidden-swift.rsp')
            with self.subTest(module_in_response=module_in_response), \
                    self.assertRaises(checker.ProfileError):
                self.inspect(self.commands() + [command])

    def test_overlong_actual_compile_line_cannot_hide_another_profile(self):
        hidden = self.c_command('NG2Perception', ['-O0']) + ' -DVALUE=' + 'x' * (2 * 1024 * 1024)
        with self.assertRaises(checker.ProfileError):
            self.inspect(self.commands() + [hidden])

    def test_malformed_actual_compile_quoting_cannot_hide_another_profile(self):
        hidden = self.c_command('NG2Perception', ['-O0']) + ' -DVALUE="unterminated'
        with self.assertRaises(checker.ProfileError):
            self.inspect(self.commands() + [hidden])

    def test_log_contents_are_never_executed(self):
        marker = self.base / 'must-not-exist'
        lines = ['touch ' + shlex.quote(str(marker)), *self.commands()]
        with patch.object(checker.subprocess, 'run', side_effect=AssertionError('executed log')):
            self.inspect(lines)
        self.assertFalse(marker.exists())


class PerceptionSavedProfileTests(unittest.TestCase):
    c_command = PerceptionCompileLogTests.c_command
    swift_command = PerceptionCompileLogTests.swift_command
    commands = PerceptionCompileLogTests.commands
    inspect = PerceptionCompileLogTests.inspect

    def setUp(self):
        PerceptionCompileLogTests.setUp(self)
        self.saved = self.inspect(self.commands())
        self.saved_path = self.upstream / 'release/native-perception-profile.json'
        self.saved_path.parent.mkdir()
        self.write_profile()

    def write_profile(self):
        self.saved_path.write_text(json.dumps(self.saved))

    def read_profile(self):
        with patch.object(checker, 'inspect_project', return_value=copy.deepcopy(self.profile)):
            return checker.read_compile_profile(self.upstream)

    def test_saved_actual_profile_roundtrip(self):
        self.assertEqual(self.read_profile(), self.saved)

    def test_saved_navigation_fields_and_duplicate_records_are_revalidated(self):
        original = copy.deepcopy(self.saved)
        for mutation in ('optimization', 'unsafe', 'source_hash', 'wrong_source',
                         'wrong_target', 'duplicate', 'missing'):
            self.saved = copy.deepcopy(original)
            row = self.saved['navigation_compiles'][0]
            if mutation == 'optimization':
                row['optimization'] = '-O0'
                for key in ('arguments', 'raw_arguments'):
                    row[key].append('-O0')
            elif mutation == 'unsafe':
                for key in ('arguments', 'raw_arguments'):
                    row[key].append('-ffast-math')
            elif mutation == 'source_hash':
                row['source_sha256'] = 'a' * 64
            elif mutation in ('wrong_source', 'wrong_target'):
                option = '-c' if mutation == 'wrong_source' else '-o'
                value = str(self.upstream / ('Elsewhere/NG2Navigation.c' if option == '-c'
                    else 'build/Debug-iphoneos/Elsewhere.build/NG2Navigation.o'))
                for key in ('arguments', 'raw_arguments'):
                    args = row[key]
                    args[args.index(option) + 1] = value
            elif mutation == 'duplicate':
                self.saved['navigation_compiles'].append(copy.deepcopy(row))
            else:
                del self.saved['navigation_compiles']
            self.write_profile()
            with self.subTest(mutation=mutation), self.assertRaises(checker.ProfileError):
                self.read_profile()

    def test_saved_navigation_response_is_reexpanded_and_rehashed(self):
        response = self.upstream / 'build/navigation.rsp'
        response.parent.mkdir()
        response.write_text(shlex.join(checker.FLAGS))
        lines = self.commands()
        lines[2] = self.c_command('NG2Navigation', ['@build/navigation.rsp'])
        self.saved = self.inspect(lines)
        self.write_profile()
        self.assertEqual(self.read_profile(), self.saved)
        response.write_text(shlex.join(checker.FLAGS) + ' -ffast-math')
        with self.assertRaises(checker.ProfileError):
            self.read_profile()

    def test_saved_profile_rejects_missing_swift_module_and_boolean_source_count(self):
        original = copy.deepcopy(self.saved)
        self.saved['swift_compiles'] = [row for row in self.saved['swift_compiles']
                                       if row['module'] != 'LoopCtrlBroadcast']
        del self.saved['swift_profiles']['LoopCtrlBroadcast']
        self.write_profile()
        with self.assertRaises(checker.ProfileError):
            self.read_profile()
        self.saved = original
        self.saved['project_profile']['sources'][checker.NAVIGATION]['source_count'] = True
        self.write_profile()
        with self.assertRaises(checker.ProfileError):
            self.read_profile()

    def test_saved_profile_revalidates_real_swift_loader_literals(self):
        lines = self.commands()
        lines[-1] = self.swift_command(['-Onone', '-Xlinker', '-install_name',
            '-Xlinker', '@rpath/LoopCtrlBroadcast.debug.dylib', '-Xlinker',
            '@loader_path/Frameworks'], driver=True)
        self.saved = self.inspect(lines)
        self.write_profile()
        self.assertEqual(self.read_profile(), self.saved)
        # Changing the source context back into an unadmitted @ token must not
        # inherit the valid loader exception from the earlier proof.
        raw = next(row['raw_arguments'] for row in self.saved['swift_compiles']
                   if '@rpath/LoopCtrlBroadcast.debug.dylib' in row['raw_arguments'])
        index = raw.index('@rpath/LoopCtrlBroadcast.debug.dylib')
        del raw[index - 1]
        self.write_profile()
        with self.assertRaises(checker.ProfileError):
            self.read_profile()

    def test_saved_clang_loader_named_response_does_not_inherit_swift_exception(self):
        hidden = self.upstream / 'rpath/hidden.rsp'
        hidden.parent.mkdir()
        hidden.write_text('-ffast-math')
        for key in ('raw_arguments', 'arguments'):
            self.saved['perception_compiles'][0][key] += ['-Xlinker', '@rpath/hidden.rsp']
        self.write_profile()
        with self.assertRaises(checker.ProfileError):
            self.read_profile()

    def test_missing_saved_proof_is_rejected(self):
        self.saved_path.unlink()
        with self.assertRaises(checker.ProfileError):
            self.read_profile()

    def test_tampered_effective_profile_and_expanded_arguments_are_rejected(self):
        original = copy.deepcopy(self.saved)
        for field, value in (('optimization', '-O0'), ('fast_math', True),
                             ('arguments', ['/usr/bin/clang', '-O0'])):
            self.saved = copy.deepcopy(original)
            self.saved['perception_compiles'][0][field] = value
            self.write_profile()
            with self.subTest(field=field), self.assertRaises(checker.ProfileError):
                self.read_profile()

    def test_nonboolean_fast_math_zero_cannot_masquerade_as_false(self):
        self.saved['perception_compiles'][0]['fast_math'] = 0
        self.write_profile()
        with self.assertRaises(checker.ProfileError):
            self.read_profile()

    def test_boolean_format_version_is_not_an_integer_version(self):
        self.saved['format_version'] = True
        self.write_profile()
        with self.assertRaises(checker.ProfileError):
            self.read_profile()

    def test_saved_source_and_project_hash_mismatches_are_rejected(self):
        original = copy.deepcopy(self.saved)
        for project in (False, True):
            self.saved = copy.deepcopy(original)
            if project:
                self.saved['project_profile']['project_sha256'] = 'f' * 64
            else:
                self.saved['source_sha256'] = 'f' * 64
            self.write_profile()
            with self.subTest(project=project), self.assertRaises(checker.ProfileError):
                self.read_profile()

    def test_current_native_source_bytes_are_rehashed(self):
        (self.sources / 'NG2Beat.c').write_text('/* changed after compilation */')
        with self.assertRaises(checker.ProfileError):
            self.read_profile()

    def test_missing_other_c_and_swift_records_are_rejected(self):
        original = copy.deepcopy(self.saved)
        for field in ('other_c_profiles', 'swift_compiles', 'perception_compiles'):
            self.saved = copy.deepcopy(original)
            self.saved[field] = {} if field == 'other_c_profiles' else []
            self.write_profile()
            with self.subTest(field=field), self.assertRaises(checker.ProfileError):
                self.read_profile()

    def test_missing_raw_argv_is_rejected(self):
        del self.saved['perception_compiles'][0]['raw_arguments']
        self.write_profile()
        with self.assertRaises(checker.ProfileError):
            self.read_profile()

    def test_saved_responses_are_reexpanded_and_rehashed(self):
        response = self.upstream / 'build/perception.rsp'
        response.parent.mkdir()
        response.write_text(shlex.join(checker.FLAGS))
        lines = self.commands()
        lines[0] = self.c_command('NG2Perception', ['@build/perception.rsp'])
        self.saved = self.inspect(lines)
        self.write_profile()
        self.assertEqual(self.read_profile(), self.saved)
        response.write_text(shlex.join(checker.FLAGS) + ' -DCHANGED=1')
        with self.assertRaises(checker.ProfileError):
            self.read_profile()
        response.unlink()
        with self.assertRaises(checker.ProfileError):
            self.read_profile()

    def test_build_and_c_swift_command_digests_require_present_hex_sha256(self):
        original = copy.deepcopy(self.saved)
        for location in ('build', 'c', 'swift'):
            for value in (None, 'bad', 'G' * 64, True):
                self.saved = copy.deepcopy(original)
                record, key = (self.saved, 'build_log_sha256') if location == 'build' else (
                    self.saved['perception_compiles' if location == 'c' else 'swift_compiles'][0],
                    'command_sha256')
                if value is None:
                    del record[key]
                else:
                    record[key] = value
                self.write_profile()
                with self.subTest(location=location, value=value), self.assertRaises(checker.ProfileError):
                    self.read_profile()

    def test_response_byte_count_true_cannot_masquerade_as_integer_one(self):
        response = self.upstream / 'build/empty.rsp'
        response.parent.mkdir()
        response.write_text(' ')
        lines = self.commands()
        lines[0] = self.c_command('NG2Perception', list(checker.FLAGS) + ['@build/empty.rsp'])
        self.saved = self.inspect(lines)
        self.write_profile()
        self.assertEqual(self.read_profile(), self.saved)
        self.saved['response_files'][0]['bytes'] = True
        self.write_profile()
        with self.assertRaises(checker.ProfileError):
            self.read_profile()


class PerceptionPackageCallsiteTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('perception_package_checker', HERE / 'verify_package.py')
        self.package = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.package)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.upstream = self.base / 'upstream'
        self.driver = self.base / 'driver'
        patch_dir = self.driver / 'patches/loopctrl'
        patch_dir.mkdir(parents=True)
        (patch_dir / 'fixture.patch').write_text('fixture')
        self.ipa = self.base / 'app.ipa'

    def run_package(self, capability, proof):
        with patch.dict(sys.modules, {'check_perception_build': checker}), \
                patch.object(sys, 'argv', ['verify_package.py', str(self.upstream), str(self.driver), str(self.ipa)]), \
                patch.object(self.package, 'inspect_ipa', return_value={'ipa_sha256': '1' * 64}), \
                patch.object(self.package, 'inspect_native_sources', return_value={'client_capability': capability}), \
                patch.object(self.package, 'command', return_value=checker.UPSTREAM), \
                patch.object(checker, 'read_compile_profile', proof), patch('builtins.print'):
            self.package.main()

    def test_native_v6_real_package_callsite_requires_profile(self):
        from unittest.mock import Mock
        proof = Mock(side_effect=checker.ProfileError('missing actual proof'))
        with self.assertRaisesRegex(checker.ProfileError, 'missing actual proof'):
            self.run_package('necrogold_native_v6', proof)
        proof.assert_called_once_with(self.upstream, required_version=1)
        self.assertFalse((self.base / 'build-manifest.json').exists())

    def test_native_v7_and_v8_real_package_callsites_require_profile_v2(self):
        from unittest.mock import Mock
        for version in (7, 8):
            with self.subTest(capability=version):
                proof = Mock(side_effect=checker.ProfileError('missing current profile v2'))
                with self.assertRaisesRegex(checker.ProfileError, 'missing current profile v2'):
                    self.run_package('necrogold_native_v'+str(version), proof)
                proof.assert_called_once_with(self.upstream, required_version=2)
                self.assertFalse((self.base / 'build-manifest.json').exists())

    def test_native_v8_profile_v2_is_included_in_actual_written_manifest(self):
        from unittest.mock import Mock
        profile = {'profile': 'strict-O2-v2', 'verified': True}
        proof = Mock(return_value=profile)
        self.run_package('necrogold_native_v8', proof)
        proof.assert_called_once_with(self.upstream, required_version=2)
        report = json.loads((self.base / 'build-manifest.json').read_text())
        self.assertEqual(report['perception_build_profile'], profile)

    def test_native_v10_profile_v2_is_included_in_actual_written_manifest(self):
        from unittest.mock import Mock
        profile = {'profile': 'strict-O2-v2', 'verified': True}
        proof = Mock(return_value=profile)
        self.run_package('necrogold_native_v10', proof)
        proof.assert_called_once_with(self.upstream, required_version=2)
        report = json.loads((self.base / 'build-manifest.json').read_text())
        self.assertEqual(report['perception_build_profile'], profile)

    def test_native_v11_profile_v2_is_included_in_actual_written_manifest(self):
        from unittest.mock import Mock
        profile = {'profile': 'strict-O2-v2', 'verified': True}
        proof = Mock(return_value=profile)
        self.run_package('necrogold_native_v11', proof)
        proof.assert_called_once_with(self.upstream, required_version=2)
        report = json.loads((self.base / 'build-manifest.json').read_text())
        self.assertEqual(report['perception_build_profile'], profile)

    def test_native_v5_preserves_earlier_package_behavior_without_profile(self):
        from unittest.mock import Mock
        proof = Mock(side_effect=AssertionError('legacy package requested new profile'))
        self.run_package('necrogold_native_v5', proof)
        proof.assert_not_called()

    def test_native_v6_profile_is_included_in_actual_written_manifest(self):
        from unittest.mock import Mock
        profile = {'profile': 'strict-O2-v1', 'verified': True}
        proof = Mock(return_value=profile)
        self.run_package('necrogold_native_v6', proof)
        proof.assert_called_once_with(self.upstream, required_version=1)
        report = json.loads((self.base / 'build-manifest.json').read_text())
        self.assertEqual(report['perception_build_profile'], profile)


class PerceptionGuardMutationTests(unittest.TestCase):
    def require_guard_removal_detected(self, reason, case_class, method):
        """Remove a real production guard, then require its named test to fail."""
        source_path = HERE / 'check_perception_build.py'
        source = source_path.read_text()
        guards = []
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.If) or len(node.body) != 1:
                continue
            statement = node.body[0]
            if not isinstance(statement, ast.Raise) or not isinstance(statement.exc, ast.Call):
                continue
            args = statement.exc.args
            if len(args) == 1 and isinstance(args[0], ast.Constant) and args[0].value == reason:
                guards.append(node)
        self.assertEqual(len(guards), 1, 'mutation must select exactly one actual guard')
        guard = guards[0]
        lines = source.splitlines(keepends=True)
        lines[guard.lineno - 1:guard.end_lineno] = [
            ' ' * guard.col_offset + 'pass  # actual guard removed by host mutant\n']
        mutant = types.ModuleType('perception_guard_mutant_' + reason)
        mutant.__file__ = str(source_path)
        exec(compile(''.join(lines), str(source_path), 'exec'), mutant.__dict__)
        target = case_class(method)
        output = io.StringIO()
        with patch.dict(globals(), {'checker': mutant}):
            result = unittest.TextTestRunner(stream=output, verbosity=0).run(target)
        self.assertEqual(result.testsRun, 1, output.getvalue())
        self.assertEqual(result.errors, [], 'compile/API/setup errors are not behavioral Red')
        self.assertGreater(len(result.failures), 0, 'named assertion did not detect removed guard')
        for failed, traceback in result.failures:
            self.assertTrue(failed.id().startswith(target.id()), output.getvalue())
            self.assertIn('AssertionError', traceback)

    def test_actual_optimization_guard_removal_is_detected(self):
        self.require_guard_removal_detected('perception_effective_optimization',
            PerceptionEffectiveFlagsTests, 'test_later_non_o2_optimization_is_rejected')

    def test_actual_independent_fp_guard_removal_is_detected(self):
        self.require_guard_removal_detected('perception_unsafe_fp_option',
            PerceptionEffectiveFlagsTests,
            'test_each_unsafe_fp_switch_is_rejected_even_when_followed_by_reset')

    def test_actual_pbx_source_count_guard_removal_is_detected(self):
        self.require_guard_removal_detected('perception_project_source_count',
            PerceptionProjectContractTests, 'test_repeated_build_entry_is_rejected')

    def test_actual_two_source_compile_count_guard_removal_is_detected(self):
        self.require_guard_removal_detected('perception_compile_strict_source_count',
            PerceptionCompileLogTests, 'test_both_strict_sources_must_compile_exactly_once')

    def test_actual_all_five_swift_module_guard_removal_is_detected(self):
        self.require_guard_removal_detected('perception_compile_swift_evidence_missing',
            PerceptionCompileLogTests, 'test_all_five_swift_modules_must_have_onone_evidence_in_v2')

    def require_package_profile_callsite_removal_detected(self, method):
        source_path = HERE / 'verify_package.py'
        source = source_path.read_text()
        main = next(node for node in ast.parse(source).body
                    if isinstance(node, ast.FunctionDef) and node.name == 'main')
        branches = [node for node in ast.walk(main)
                    if isinstance(node, ast.If)
                    and any(isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                            and value.func.id == 'read_compile_profile' for value in ast.walk(node))]
        self.assertEqual(len(branches), 1)
        branch = branches[0]
        lines = source.splitlines(keepends=True)
        lines[branch.lineno - 1:branch.end_lineno] = [
            ' ' * branch.col_offset + 'pass  # actual package callsite removed\n']
        mutant = types.ModuleType('perception_package_callsite_mutant')
        mutant.__file__ = str(source_path)
        exec(compile(''.join(lines), str(source_path), 'exec'), mutant.__dict__)
        original_setup = PerceptionPackageCallsiteTests.setUp

        def setup_with_mutant(case):
            original_setup(case)
            case.package = mutant

        target = PerceptionPackageCallsiteTests(method)
        output = io.StringIO()
        with patch.object(PerceptionPackageCallsiteTests, 'setUp', setup_with_mutant):
            result = unittest.TextTestRunner(stream=output, verbosity=0).run(target)
        self.assertEqual(result.testsRun, 1, output.getvalue())
        self.assertEqual(result.errors, [], 'compile/API/setup errors are not behavioral Red')
        self.assertEqual(len(result.failures), 1, output.getvalue())
        self.assertEqual(result.failures[0][0].id(), target.id())
        self.assertIn('AssertionError', result.failures[0][1])


    def test_actual_native_v6_package_profile_callsite_removal_is_detected(self):
        self.require_package_profile_callsite_removal_detected('test_native_v6_real_package_callsite_requires_profile')

    def test_actual_native_v8_package_profile_callsite_removal_is_detected(self):
        self.require_package_profile_callsite_removal_detected('test_native_v8_profile_v2_is_included_in_actual_written_manifest')

    def test_actual_native_v10_package_profile_callsite_removal_is_detected(self):
        self.require_package_profile_callsite_removal_detected('test_native_v10_profile_v2_is_included_in_actual_written_manifest')

    def test_actual_native_v11_package_profile_callsite_removal_is_detected(self):
        self.require_package_profile_callsite_removal_detected('test_native_v11_profile_v2_is_included_in_actual_written_manifest')


if __name__ == '__main__':
    unittest.main()
