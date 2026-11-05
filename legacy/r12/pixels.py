"""Image kernels built for baseline i386. Load from iSH's own temporary filesystem."""
import ctypes as C
from pathlib import Path
import shutil
import tempfile

with tempfile.TemporaryDirectory() as folder:
    binary = Path(folder) / "pixels.so"
    shutil.copyfile(Path(__file__).with_name("pixels_i386.so"), binary)
    lib = C.CDLL(str(binary))

try:
    if lib.kernel_abi()!=10:raise RuntimeError("画像ライブラリの版が一致しません。R12フォルダ全体で起動してください。")
except AttributeError as exc:
    raise RuntimeError("古い画像ライブラリです。R12フォルダ全体で起動してください。") from exc

lib.has_gold.argtypes = [C.c_char_p]
lib.locate_signs.argtypes = [C.c_char_p, C.POINTER(C.c_int)]
lib.ring_match.argtypes = [C.c_char_p, C.c_char_p, C.c_int, C.c_int, C.c_int, C.c_int]
lib.ring_match.restype = C.c_double
lib.gradient_bytes.argtypes = []
lib.gradients.argtypes = [C.c_char_p, C.c_void_p]
lib.gradients.restype = None
lib.observed_move.argtypes = [C.c_void_p, C.c_void_p, C.c_int, C.c_int]
lib.observed_count.argtypes = [C.c_void_p, C.c_void_p, C.c_int, C.c_int, C.c_int]
lib.hud_banner.argtypes = [C.c_char_p]
lib.scan_tiles.argtypes = [C.c_char_p, C.POINTER(C.c_int)]
lib.scan_tiles.restype = None
