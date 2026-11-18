import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools import test116_request as subject

ROOT = Path(__file__).resolve().parents[1]
EVENT, SOURCE, BUILD = 'a'*40, 'c'*40, 'd'*40
WORKFLOW_SHA = hashlib.sha256(b'workflow').hexdigest()


def context(**changes):
    return dict(dict(repository=subject.REPOSITORY, ref='refs/heads/'+subject.BRANCH,
        event='push', sha=EVENT), **changes)


def device_request(**changes):
    return dict(dict(schema=subject.SCHEMA, operation='dispatch', request_id='test116-device-001',
        source_commit='event', native_lane='device', workflow_sha256=WORKFLOW_SHA), **changes)


def publish_request(**changes):
    return dict(dict(schema=subject.SCHEMA, operation='publish', request_id='test116-publish-001',
        source_commit=SOURCE, workflow_sha256=WORKFLOW_SHA, build_commit=BUILD,
        build_run_id='123', artifact_id='456', archive_sha256='1'*64,
        ipa_sha256='2'*64, source_sha256='3'*64, release_tag='test116-build239'), **changes)


class FakeAPI:
    def __init__(self):
        self.calls = []
        self.tags = {}
        self.releases = {}
        self.workflow = dict(type='file', path=subject.WORKFLOW, size=8,
            encoding='base64', content=base64.b64encode(b'workflow').decode())
        self.comparison = dict(status='ahead', base_commit=dict(sha=BUILD),
            merge_base_commit=dict(sha=BUILD), total_commits=1,
            files=[dict(filename='docs/reviews/test116.md')])
        self.run = dict(id=123, head_sha=BUILD, workflow_id=subject.WORKFLOW_ID,
            path=subject.WORKFLOW, status='completed', conclusion='success',
            repository=dict(full_name=subject.REPOSITORY), run_number=239)
        self.artifact = dict(id=456, name='loopctrl-ngg2-unsigned', expired=False,
            size_in_bytes=18000000, digest='sha256:'+'1'*64,
            workflow_run=dict(id=123, head_sha=BUILD,
                repository_id=1446496126, head_repository_id=1446496126))
        self.override = {}

    @property
    def posts(self):
        return [row for row in self.calls if row[0] == 'POST']

    def __call__(self, method, path, data=None, allow_missing=False):
        self.calls.append((method, path, deepcopy(data)))
        endpoint = path.removeprefix(subject.API_ROOT+'/')
        if (method, endpoint) in self.override:
            return deepcopy(self.override[(method, endpoint)])
        if method == 'GET' and endpoint.startswith('contents/'):
            return deepcopy(self.workflow)
        if method == 'GET' and endpoint.startswith('compare/'):
            before, after = endpoint[len('compare/'):].split('...')
            value = deepcopy(self.comparison)
            value['base_commit']['sha'] = value['merge_base_commit']['sha'] = before
            return value
        if endpoint.startswith('git/ref/tags/') and method == 'GET':
            self.assert_missing(allow_missing)
            name = endpoint[len('git/ref/tags/'):]
            value = self.tags.get(name)
            return None if value is None else dict(ref='refs/tags/'+name,
                object=dict(type='commit', sha=value, url='https://api.github.com/fixed'))
        if endpoint == 'git/refs' and method == 'POST':
            name = data['ref'].removeprefix('refs/tags/')
            if name in self.tags:
                raise AssertionError('duplicate tag creation')
            self.tags[name] = data['sha']
            return dict(ref=data['ref'], object=dict(type='commit', sha=data['sha']))
        if endpoint.startswith('actions/workflows/') and endpoint.endswith('/dispatches') and method == 'POST':
            return None
        if endpoint == 'actions/runs/123' and method == 'GET':
            return deepcopy(self.run)
        if endpoint == 'actions/artifacts/456' and method == 'GET':
            return deepcopy(self.artifact)
        if endpoint.startswith('releases/tags/') and method == 'GET':
            self.assert_missing(allow_missing)
            return deepcopy(self.releases.get(endpoint[len('releases/tags/'):]))
        if endpoint == 'releases' and method == 'POST':
            value = dict(deepcopy(data), id=789, assets=[])
            self.releases[data['tag_name']] = value
            return deepcopy(value)
        raise AssertionError((method, path, data))

    @staticmethod
    def assert_missing(value):
        if value is not True:
            raise AssertionError('optional GET must explicitly allow missing')


class CIRequest116Tests(unittest.TestCase):
    def test_valid_device_request_dispatches_the_exact_frozen_tag_once(self):
        context = dict(repository='shuhei0720/necrogold-automation',
            ref='refs/heads/work/p1-capture-probe', event='push', sha='a'*40)
        request = dict(schema='necrogold-test116-request-v1', operation='dispatch',
            request_id='test116-device-001', source_commit='event', native_lane='device',
            workflow_sha256='b'*64)
        calls = []

        def api(method, path, data=None, allow_missing=False):
            calls.append((method, path, data))
            if path.endswith('/contents/.github/workflows/loopctrl-geometry.yml?ref='+'a'*40):
                import base64
                return dict(type='file', path=subject.WORKFLOW, size=8,
                    encoding='base64', content=base64.b64encode(b'workflow').decode())
            if '/git/ref/tags/' in path:
                return None
            if method == 'POST' and path.endswith('/git/refs'):
                return dict(ref=data['ref'], object=dict(type='commit', sha=data['sha']))
            if method == 'POST' and path.endswith('/dispatches'):
                return None
            raise AssertionError((method, path))

        import hashlib
        request['workflow_sha256'] = hashlib.sha256(b'workflow').hexdigest()
        result = subject.execute_request(request, context, api)
        self.assertEqual('dispatched', result['status'])
        posts = [row for row in calls if row[0] == 'POST']
        self.assertEqual(2, len(posts))
        self.assertEqual(dict(ref='refs/tags/test116-ci-device-001', sha='a'*40), posts[0][2])
        self.assertEqual(dict(ref='test116-ci-device-001', inputs=dict(native_lane='device')), posts[1][2])

    def test_disabled_and_invalid_context_have_no_remote_calls(self):
        api = FakeAPI()
        result = subject.execute_request(dict(schema=subject.SCHEMA, operation='disabled'), context(), api)
        self.assertEqual(dict(status='disabled', mutations=0), result)
        self.assertEqual([], api.calls)
        for key, value in (('repository', 'other/repo'), ('ref', 'refs/heads/main'),
                ('event', 'workflow_dispatch'), ('sha', '../bad')):
            with self.subTest(key=key), self.assertRaises(ValueError):
                subject.execute_request(device_request(), context(**{key: value}), api)
        self.assertEqual([], api.calls)

    def test_request_schema_rejects_unknown_fields_lanes_values_and_unsafe_identifiers(self):
        bad = [dict(device_request(), extra='x'), device_request(operation='shell'),
            device_request(native_lane='full'), device_request(native_lane='publish-download'),
            device_request(request_id='test116-red-001'), device_request(source_commit='HEAD'),
            device_request(workflow_sha256='B'*64), device_request(request_id='test116-device-$(id)'),
            publish_request(source_commit='event'), publish_request(artifact_id=True),
            publish_request(artifact_id='0'), publish_request(build_run_id=str(2**63)),
            publish_request(release_tag='test115-build239'), publish_request(ipa_sha256='2'*63),
            dict(schema=subject.SCHEMA, operation='disabled', extra='x')]
        for request in bad:
            with self.subTest(request=request), self.assertRaises(ValueError):
                subject.validate_request(request)

    def test_request_file_rejects_duplicate_keys_symlinks_and_oversize(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'request.json'
            path.write_text('{"schema":"'+subject.SCHEMA+'","operation":"disabled","operation":"disabled"}')
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                subject.load_request(path)
            path.write_text(json.dumps(dict(schema=subject.SCHEMA, operation='disabled')))
            request, digest = subject.load_request(path)
            self.assertEqual('disabled', request['operation'])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
            link = Path(directory)/'link'
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                subject.load_request(link)
            path.write_text(' '*4097)
            with self.assertRaises(ValueError):
                subject.load_request(path)

    def test_workflow_hash_and_foreign_ancestry_fail_before_any_write(self):
        api = FakeAPI()
        for request in (device_request(workflow_sha256='0'*64), device_request(source_commit=SOURCE)):
            if request['source_commit'] == SOURCE:
                api.comparison['status'] = 'diverged'
            with self.subTest(request=request), self.assertRaises(ValueError):
                subject.execute_request(request, context(), api)
        self.assertEqual([], api.posts)

    def test_claim_prevents_automatic_duplicate_dispatch_and_never_moves_a_wrong_tag(self):
        api = FakeAPI()
        api.tags['test116-ci-device-001'] = EVENT
        result = subject.execute_request(device_request(), context(), api)
        self.assertEqual('already_claimed', result['status'])
        self.assertEqual([], api.posts)
        api.tags['test116-ci-device-001'] = BUILD
        with self.assertRaisesRegex(ValueError, 'tag identity'):
            subject.execute_request(device_request(), context(), api)
        self.assertEqual([], api.posts)

    def test_red_request_can_only_dispatch_an_explicit_red_lane(self):
        for lane in ('test115-runtime-red', 'test116-runtime-red'):
            api = FakeAPI()
            result = subject.execute_request(device_request(request_id='test116-red-001',
                native_lane=lane, source_commit=SOURCE), context(), api)
            self.assertEqual(SOURCE, api.tags['test116-ci-red-001'])
            self.assertEqual(lane, result['inputs']['native_lane'])

    def test_publish_qualifies_artifact_and_docs_then_creates_exact_draft_and_calls_existing_publisher(self):
        api = FakeAPI()
        result = subject.execute_request(publish_request(), context(), api)
        self.assertEqual('dispatched', result['status'])
        self.assertEqual(SOURCE, api.tags['test116-build239'])
        self.assertEqual(EVENT, api.tags['test116-ci-publish-001'])
        self.assertEqual(4, len(api.posts))
        self.assertEqual('test116-build239', result['dispatch_ref'])
        self.assertEqual('789', result['inputs']['release_id'])
        self.assertEqual('publish-download', result['inputs']['native_lane'])
        self.assertEqual(SOURCE, result['inputs']['source_commit'])
        release = api.releases['test116-build239']
        self.assertEqual((True, True, []), (release['draft'], release['prerelease'], release['assets']))
        first_post = next(index for index, row in enumerate(api.calls) if row[0] == 'POST')
        self.assertTrue(any('/actions/artifacts/' in row[1] for row in api.calls[:first_post]))

    def test_publish_reuses_only_an_empty_exact_draft_and_exact_source_tag(self):
        api = FakeAPI()
        api.tags['test116-build239'] = SOURCE
        api.releases['test116-build239'] = dict(id=900, tag_name='test116-build239',
            target_commitish=SOURCE, draft=True, prerelease=True, assets=[])
        result = subject.execute_request(publish_request(), context(), api)
        self.assertEqual('900', result['inputs']['release_id'])
        self.assertEqual(2, len(api.posts))
        for change in (dict(draft=False), dict(assets=[dict(name='existing.ipa')]),
                dict(target_commitish=BUILD), dict(prerelease=False)):
            wrong = FakeAPI()
            wrong.releases['test116-build239'] = dict(api.releases['test116-build239'], **change)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'draft'):
                subject.execute_request(publish_request(), context(), wrong)
            self.assertEqual([], wrong.posts)
        wrong = FakeAPI()
        wrong.tags['test116-build239'] = BUILD
        with self.assertRaisesRegex(ValueError, 'tag identity'):
            subject.execute_request(publish_request(), context(), wrong)
        self.assertEqual([], wrong.posts)

    def test_failed_mismatched_expired_or_foreign_builds_never_create_release_or_claim(self):
        for target, change in (('run', dict(conclusion='failure')), ('run', dict(head_sha=SOURCE)),
                ('run', dict(workflow_id=1)), ('run', dict(status='in_progress')),
                ('run', dict(run_number=240)), ('run', dict(repository=dict(full_name='other/repo'))),
                ('artifact', dict(expired=True)), ('artifact', dict(name='other')),
                ('artifact', dict(size_in_bytes=0)),
                ('artifact', dict(workflow_run=dict(id=124, head_sha=BUILD)))):
            api = FakeAPI()
            setattr(api, target, dict(getattr(api, target), **change))
            with self.subTest(target=target, change=change), self.assertRaises(ValueError):
                subject.execute_request(publish_request(), context(), api)
            self.assertEqual([], api.posts)

    def test_publish_never_hides_product_changes_or_a_truncated_source_comparison(self):
        for change in (dict(files=[dict(filename='necroprobe/test116.py')]),
                dict(files=[dict(filename='docs/a.md', previous_filename='product.py')]),
                dict(files=[]), dict(files=[dict(filename='docs/a.md')]*300),
                dict(total_commits=250)):
            api = FakeAPI()
            api.comparison.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                subject.execute_request(publish_request(), context(), api)
            self.assertEqual([], api.posts)

    def test_artifact_whole_archive_hash_and_both_repository_ids_must_match(self):
        for change in (dict(digest='sha256:'+'0'*64), dict(digest=None),
                dict(workflow_run=dict(id=123, head_sha=BUILD,
                    repository_id=1, head_repository_id=1446496126)),
                dict(workflow_run=dict(id=123, head_sha=BUILD,
                    repository_id=1446496126, head_repository_id=1))):
            api = FakeAPI()
            api.artifact.update(change)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'artifact'):
                subject.execute_request(publish_request(), context(), api)
            self.assertEqual([], api.posts)

    def test_cli_uses_structured_stdin_and_404_is_only_an_explicit_optional_read(self):
        response = subprocess.CompletedProcess([], 0, stdout=b'HTTP/2.0 201 Created\r\nContent-Type: application/json\r\n\r\n{"id":1}', stderr=b'')
        with patch.object(subject.subprocess, 'run', return_value=response) as call:
            self.assertEqual(dict(id=1), subject.github_api('POST', subject.API_ROOT+'/releases', dict(a='line\nvalue')))
        args, kwargs = call.call_args
        self.assertNotIn('shell', kwargs)
        self.assertEqual(['--input', '-'], args[0][-2:])
        self.assertEqual(dict(a='line\nvalue'), json.loads(kwargs['input']))
        response = subprocess.CompletedProcess([], 1, stdout=b'HTTP/2.0 404 Not Found\n\n{"message":"Not Found"}', stderr=b'redacted')
        with patch.object(subject.subprocess, 'run', return_value=response):
            self.assertIsNone(subject.github_api('GET', subject.API_ROOT+'/releases/tags/missing', allow_missing=True))
            with self.assertRaises(ValueError):
                subject.github_api('GET', subject.API_ROOT+'/releases/tags/missing')
        with self.assertRaises(ValueError):
            subject.github_api('POST', 'repos/other/repo/releases')

    def test_workflow_is_fixed_branch_standard_runner_pinned_checkout_and_disabled_by_default(self):
        text = (ROOT/'.github/workflows/test116-request.yml').read_text()
        for value in ('branches: [work/p1-capture-probe]', 'runs-on: ubuntu-latest',
                "github.repository == 'shuhei0720/necrogold-automation'", 'persist-credentials: false',
                'ref: ${{ github.sha }}', 'cancel-in-progress: false',
                'actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1',
                'python3 tools/test116_request.py .github/test116-request.json'):
            self.assertIn(value, text)
        self.assertNotIn('secrets.', text)
        request, _digest = subject.load_request(ROOT/'.github/test116-request.json')
        self.assertEqual(dict(schema=subject.SCHEMA, operation='disabled'), request)


if __name__ == '__main__':
    unittest.main()
