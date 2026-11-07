"""起動前の版・Pillow確認。ゲーム操作やRPC/nativeのimportは行わない。"""
import ast
from pathlib import Path
import sys


MAX_SOURCE_BYTES = 256 * 1024


def _literal(path, name):
    with Path(path).open('rb') as source:
        raw = source.read(MAX_SOURCE_BYTES + 1)
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError('source too large')
    tree = ast.parse(raw.decode('utf-8'))
    assignments = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
            targets = [node.target]
        else:
            continue
        if any(isinstance(target, ast.Name) and target.id == name
               for item in targets for target in ast.walk(item)):
            assignments.append(node)
    if len(assignments) != 1:
        raise ValueError('ambiguous version')
    node = assignments[0]
    if (node not in tree.body or not isinstance(node, ast.Assign) or len(node.targets) != 1
            or not isinstance(node.targets[0], ast.Name) or node.targets[0].id != name
            or not isinstance(node.value, ast.Constant) or type(node.value.value) is not str):
        raise ValueError('version is not a top-level string literal')
    return node.value.value


def check_version(package, version, revision):
    """Check local source metadata without executing that source.

    This catches an incorrect or incomplete extraction, not hostile source code.
    Actual runtime imports and validation still happen when the probe starts.
    """
    try:
        package = Path(package)
        return (_literal(package / '__init__.py', 'VERSION') == version
                and _literal(package / 'shop_walk.py', 'REVISION') == revision)
    except (OSError, UnicodeError, SyntaxError, ValueError, RecursionError):
        return False


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print('起動前確認: 版とrevisionの2引数が必要です。試験は開始していません。', file=sys.stderr)
        return 2
    if not check_version(Path(__file__).resolve().parent, *args):
        print('起動前確認: 指定された版の展開先で実行してください。試験は開始していません。', file=sys.stderr)
        return 1
    try:
        from PIL import Image
    except Exception:
        print('起動前確認: Pillowを読み込めません。試験は開始していません。', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
