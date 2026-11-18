"""Execute only a reviewed TEST116 CI request on its fixed GitHub branch.

No credentials or user evidence enter the request/receipt.  This is a narrow
fallback for a cloud session without GitHub Actions/Release write tools.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

REPOSITORY = 'shuhei0720/necrogold-automation'
BRANCH = 'work/p1-capture-probe'
WORKFLOW = '.github/workflows/loopctrl-geometry.yml'
WORKFLOW_ID = 408047272
REPOSITORY_ID = 1446496126
SCHEMA = 'necrogold-test116-request-v1'
API_ROOT = 'repos/'+REPOSITORY
COMMON = frozenset({'schema', 'operation', 'request_id', 'source_commit', 'workflow_sha256'})
DISPATCH = COMMON | {'native_lane'}
PUBLISH = COMMON | {'build_commit', 'build_run_id', 'artifact_id', 'archive_sha256',
    'ipa_sha256', 'source_sha256', 'release_tag'}
LANES = frozenset({'device', 'test115-runtime-red', 'test116-runtime-red'})


def require(value, message):
    if not value:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for name, value in pairs:
        require(name not in result, 'duplicate JSON key')
        result[name] = value
    return result


def load_request(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'request must be a regular file')
    raw = path.read_bytes()
    require(0 < len(raw) <= 4096, 'request byte limit')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object)
    validate_request(value)
    return value, hashlib.sha256(raw).hexdigest()


def validate_request(value):
    require(type(value) is dict and value.get('schema') == SCHEMA, 'request schema')
    operation = value.get('operation')
    if operation == 'disabled':
        require(set(value) == {'schema', 'operation'}, 'disabled request fields')
        return
    require(operation in ('dispatch', 'publish'), 'request operation')
    require(set(value) == (DISPATCH if operation == 'dispatch' else PUBLISH), 'request fields')
    require(all(type(item) is str for item in value.values()), 'request values must be strings')
    require(re.fullmatch(r'[0-9a-f]{64}', value['workflow_sha256']), 'workflow hash')
    require(re.fullmatch(r'[0-9a-f]{40}', value['source_commit'])
            or operation == 'dispatch' and value['source_commit'] == 'event', 'source commit')
    if operation == 'dispatch':
        lane = value['native_lane']
        require(lane in LANES, 'native lane')
        kind = 'device' if lane == 'device' else 'red'
    else:
        kind = 'publish'
        require(re.fullmatch(r'[0-9a-f]{40}', value['build_commit']), 'build commit')
        for key in ('build_run_id', 'artifact_id'):
            require(re.fullmatch(r'[1-9][0-9]{0,18}', value[key])
                    and int(value[key]) < 2**63, 'positive identifier: '+key)
        for key in ('archive_sha256', 'ipa_sha256', 'source_sha256'):
            require(re.fullmatch(r'[0-9a-f]{64}', value[key]), 'SHA256: '+key)
        require(re.fullmatch(r'test116-build[1-9][0-9]{0,18}', value['release_tag']), 'release tag')
    require(re.fullmatch(r'test116-'+kind+r'-[0-9]{3}', value['request_id']), 'request identifier')


def check_context(context):
    require(type(context) is dict and set(context) == {'repository', 'ref', 'event', 'sha'}, 'context fields')
    require(context['repository'] == REPOSITORY and context['ref'] == 'refs/heads/'+BRANCH
            and context['event'] == 'push', 'fixed repository/branch/push context')
    require(type(context['sha']) is str and re.fullmatch(r'[0-9a-f]{40}', context['sha']), 'event commit')


def ancestor(api, before, after, docs_only=False):
    if before == after:
        return
    value = api('GET', API_ROOT+'/compare/'+before+'...'+after)
    require(type(value) is dict and value.get('status') == 'ahead'
            and value.get('base_commit', {}).get('sha') == before
            and value.get('merge_base_commit', {}).get('sha') == before, 'commit ancestry')
    if docs_only:
        files = value.get('files')
        count = value.get('total_commits')
        require(type(count) is int and 0 < count < 250 and type(files) is list
                and 0 < len(files) < 300, 'complete closing source comparison')
        require(all(type(row) is dict and type(row.get('filename')) is str
                    and row['filename'].startswith('docs/')
                    and ('previous_filename' not in row or type(row['previous_filename']) is str
                         and row['previous_filename'].startswith('docs/')) for row in files),
                'closing source must change documents only')


def verify_workflow(api, source, expected):
    value = api('GET', API_ROOT+'/contents/'+WORKFLOW+'?ref='+source)
    require(type(value) is dict and value.get('type') == 'file'
            and value.get('path') == WORKFLOW and value.get('encoding') == 'base64'
            and type(value.get('content')) is str and len(value['content']) <= 512*1024,
            'workflow content response')
    raw = base64.b64decode(value['content'].replace('\n', ''), validate=True)
    require(type(value.get('size')) is int and value['size'] == len(raw)
            and hashlib.sha256(raw).hexdigest() == expected, 'source workflow SHA256')


def tag(api, name, source, create=False):
    value = api('GET', API_ROOT+'/git/ref/tags/'+name, allow_missing=True)
    if value is not None:
        require(type(value) is dict and value.get('ref') == 'refs/tags/'+name
                and value.get('object', {}).get('type') == 'commit'
                and value['object'].get('sha') == source, 'tag identity')
        return False
    if create:
        value = api('POST', API_ROOT+'/git/refs', dict(ref='refs/tags/'+name, sha=source))
        require(type(value) is dict and value.get('ref') == 'refs/tags/'+name
                and value.get('object', {}).get('type') == 'commit'
                and value['object'].get('sha') == source, 'created tag identity')
    return True


def validate_artifact(api, request):
    run = api('GET', API_ROOT+'/actions/runs/'+request['build_run_id'])
    require(type(run) is dict and run.get('id') == int(request['build_run_id'])
            and run.get('head_sha') == request['build_commit']
            and run.get('workflow_id') == WORKFLOW_ID and run.get('path') == WORKFLOW
            and run.get('status') == 'completed' and run.get('conclusion') == 'success'
            and run.get('repository', {}).get('full_name') == REPOSITORY
            and type(run.get('run_number')) is int and run['run_number'] > 0
            and request['release_tag'] == 'test116-build'+str(run['run_number']), 'successful build run')
    artifact = api('GET', API_ROOT+'/actions/artifacts/'+request['artifact_id'])
    require(type(artifact) is dict and artifact.get('id') == int(request['artifact_id'])
            and artifact.get('name') == 'loopctrl-ngg2-unsigned' and artifact.get('expired') is False
            and artifact.get('digest') == 'sha256:'+request['archive_sha256']
            and type(artifact.get('size_in_bytes')) is int and 0 < artifact['size_in_bytes'] <= 128*1024*1024
            and artifact.get('workflow_run', {}).get('id') == run['id']
            and artifact['workflow_run'].get('head_sha') == request['build_commit']
            and artifact['workflow_run'].get('repository_id') == REPOSITORY_ID
            and artifact['workflow_run'].get('head_repository_id') == REPOSITORY_ID, 'exact build artifact')


def verify_draft(release, request):
    require(type(release) is dict and type(release.get('id')) is int and release['id'] > 0
            and release.get('tag_name') == request['release_tag']
            and release.get('target_commitish') == request['source_commit']
            and release.get('draft') is True and release.get('prerelease') is True
            and release.get('assets') == [], 'empty exact source draft')


def execute_request(request, context, api):
    validate_request(request)
    check_context(context)
    if request['operation'] == 'disabled':
        return dict(status='disabled', mutations=0)
    source = context['sha'] if request['source_commit'] == 'event' else request['source_commit']
    ancestor(api, source, context['sha'])
    verify_workflow(api, source, request['workflow_sha256'])
    claim = 'test116-ci-'+request['request_id'][len('test116-'):]
    receipt = dict(schema='necrogold-test116-request-receipt-v1', request_id=request['request_id'],
        event_commit=context['sha'], source_commit=source, workflow_sha256=request['workflow_sha256'],
        claim_tag=claim, status='not_dispatched')
    if request['operation'] == 'dispatch':
        if not tag(api, claim, source, create=True):
            return dict(receipt, status='already_claimed')
        inputs = dict(native_lane=request['native_lane'])
        dispatch_ref = claim
    else:
        ancestor(api, request['build_commit'], source, docs_only=True)
        validate_artifact(api, request)
        release = api('GET', API_ROOT+'/releases/tags/'+request['release_tag'], allow_missing=True)
        if release is not None:
            verify_draft(release, request)
        # Do every read-only qualification before claiming this operation.
        tag(api, request['release_tag'], source)
        if not tag(api, claim, context['sha'], create=True):
            return dict(receipt, status='already_claimed')
        tag(api, request['release_tag'], source, create=True)
        if release is None:
            release = api('POST', API_ROOT+'/releases', dict(tag_name=request['release_tag'],
                target_commitish=source, name='TEST116 / '+request['release_tag'], draft=True,
                prerelease=True, make_latest='false',
                body='TEST116実機テスト資材。検証範囲と未確認事項は付属資料を参照してください。'))
            verify_draft(release, request)
        inputs = {key: request[key] for key in ('artifact_id', 'archive_sha256', 'ipa_sha256',
            'source_commit', 'source_sha256', 'release_tag')}
        inputs.update(native_lane='publish-download', release_id=str(release['id']))
        dispatch_ref = request['release_tag']
        receipt['release_id'] = release['id']
    api('POST', API_ROOT+'/actions/workflows/'+str(WORKFLOW_ID)+'/dispatches',
        dict(ref=dispatch_ref, inputs=inputs))
    return dict(receipt, status='dispatched', dispatch_ref=dispatch_ref, inputs=inputs)


def github_api(method, path, data=None, allow_missing=False):
    require(method in ('GET', 'POST') and path.startswith(API_ROOT+'/'), 'fixed API scope')
    require(allow_missing is False or method == 'GET', 'missing response scope')
    command = ['gh', 'api', '--include', '--method', method, path]
    if data is not None:
        command.extend(['--input', '-'])
    process = subprocess.run(command, input=None if data is None else json.dumps(data).encode(),
        capture_output=True, check=False, timeout=120)
    raw = process.stdout
    require(len(raw) <= 2*1024*1024, 'API response byte limit')
    header, separator, body = raw.partition(b'\r\n\r\n')
    if not separator:
        header, separator, body = raw.partition(b'\n\n')
    status = re.match(rb'HTTP/\S+ ([0-9]{3})\b', header)
    require(status is not None and separator, 'API HTTP response')
    code = int(status.group(1))
    if code == 404 and allow_missing:
        return None
    require(process.returncode == 0 and 200 <= code < 300, 'GitHub API status '+str(code))
    return None if not body.strip() else json.loads(body, object_pairs_hook=unique_object)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path)
    parser.add_argument('receipt', type=Path)
    args = parser.parse_args()
    context = {key: os.environ.get(env, '') for key, env in (
        ('repository', 'GITHUB_REPOSITORY'), ('ref', 'GITHUB_REF'),
        ('event', 'GITHUB_EVENT_NAME'), ('sha', 'GITHUB_SHA'))}
    check_context(context)
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    require(event.get('after') == context['sha'] and event.get('ref') == context['ref']
            and event.get('deleted') is False and event.get('forced') is False, 'ordinary exact push event')
    request, request_sha = load_request(args.request)
    receipt = execute_request(request, context, github_api)
    receipt['request_sha256'] = request_sha
    args.receipt.write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
