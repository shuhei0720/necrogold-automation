#!/bin/sh
set -eu
cd "$(dirname "$0")"
echo '金壁リセマラ 検証版 R12'
if ! python3 -c 'from PIL import Image; import ctypes, cryptography' 2>/dev/null; then
  apk update
  apk add python3 py3-pillow py3-cryptography
fi
if [ "${1-}" = selftest ]; then
  exec python3 selftest.py
fi
python3 - <<'PYTEST'
from PIL import Image
from pixels import lib
frame = Image.new("RGB", (597, 276))
frame.paste((200, 160, 45), (225, 100, 250, 125))
if not lib.has_gold(frame.tobytes()):
    raise SystemExit("画像処理の起動テストに失敗しました。")
print("画像処理OK（NumPy不要版）", flush=True)
import fast_crypto
print("通信暗号処理: " + ("高速ネイティブ" if fast_crypto.AVAILABLE else "Python互換動作"), flush=True)
PYTEST
if [ ! -r /dev/location ]; then
  echo 'iSHの位置情報デバイスが使えません。バックグラウンド実行の設定を確認してください。'
  exit 1
fi
echo 'ゲーム中にiSHが止まらないよう、実行中は位置情報を読み捨てます。端末外に送信しません。'
cat /dev/location >/dev/null &
keeper=$!
trap 'kill "$keeper" 2>/dev/null || true' EXIT
trap 'exit 130' INT TERM
case "${1-panel}" in
 panel) python3 panel.py ;;
 setup) python3 phone.py setup ;;
 pair) python3 loopctrl_rpc.py --host 127.0.0.1:8300 pair --name NecroGold ;;
 *) python3 phone.py "$@" ;;
esac
