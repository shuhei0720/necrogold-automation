"""TEST-014: 896×414の原画像だけを判定する暫定の開幕金壁検出。

全画像のresize/rotateとPythonの全画素ループを行わない。金色の比較、
領域mask、27×27密度窓はPillowのnative演算。閾値は既知画像での暫定値で、
未知の端末画像での精度・所要時間は未確認。unknownはrestartの許可ではない。
"""
import base64
import io
import zlib

from PIL import Image, ImageChops, ImageFilter, ImageStat

SIZE = (896, 414)
FINGERPRINT_LENGTH = 48
# TEST-013の未加工JPEGから固定HUD/メニューの1bit maskを抽出。
# deathのみR12既存1792×828資料をオフライン896×414化して抽出。
# 生画像や外部パスは実行時に必要ない。
_TEMPLATE_DATA = {'continue': ((384, 104, 512, 132),
              180,
              0.74,
              'eNq9j7ENwjAQRX+iSHYRyS5dgSMxABvggiJjMAZdDuEhKBgmozBCBkAyd+eEBZC44vTfv/O3Dfxa3Sas9jhIY9fadj+LXBmhVWlXHkquI21lSdaLPFYOSEHzTm9lj+tEwol4LWHH17XTwoa4qb6gITQgU3gpPiSftjnd5wlP1Vp0o4BeuJFzoEz20H3ZRU9j5ZobPcZOuWd2L+Gz5l/qr83iTHaEf9cH8iMj6w=='),
 'restart': ((357, 256, 538, 284),
             180,
             0.74,
             'eNrN0DEOwjAMBdCfOgIPCHlkqIS5B0OOwjEYO3GuHqVH6NgBCZy4gUiIFZHF0ZPzaxf4m9PVItFKrPKdw8r0eDM13dTwUu60GAds55Ujg60wFxapX2NPcYasscK4BBnUWSWBJmNlUuOUOeImx3vX+/vMZebYLCiHwuo8GlNuEhNrULvsgPTa27kM0YQk52R8Aoa6ZY7t87ApjMMGbcjnrz5nnnC1Z3vo3HT/+DwBq5wVvQ=='),
 'icon': ((429, 6, 465, 42), 55, 0.8, 'eNpjYMAHmP8w/sEkmKlMMGKw8AMA5CwvxQ=='),
 'footer': ((752, 396, 856, 414),
            90,
            0.65,
            'eNqVzsEJhTAQBNAJEeJhC/AYCPyz4F0sZYXfhwEb+iWsXViMqGNOehH+3h47DAP8fy7e8buhXYHyDAcB9FHCNpl3+YGamSSodEhjRtoRCz4uo9uhBV+CMRM0OhhhcLOgJcYL3gtUjQis5g6bltfVJ7bzHl0='),
 'zone_one': ((791, 399, 804, 414), 90, 0.78, 'eNpjYIAANiBsA5Mgug0qCgAU7gGx'),
 'floor_one': ((842, 399, 855, 414), 90, 0.78, 'eNpjYIAANiBsA5Mgug0qCgAU7gGx'),
 'death': ((312, 312, 582, 336),
           140,
           0.64,
           'eNrN0j1OhUAQB/D/woaPhADmNRTGt4UHwN4EoonnIBav1Rs4aGNhrLXyKs+Eg3AEsHomRpxZQDQxsbFwCdnJ7m93ZheAv2jm5+GYX9dGdQAoQEscjAsyifcISuF0BxAWgUX4RyxWucxSuYiTRQw94BW9FcseaTqKdWvrGO6ULWQSnogpS15xH60fYteRkaEVkUg3CyPHC4o0eeo4cBzehVNoR4SxojTnOZ/L1MDFGxPYImwd8N9FNGYjonrOcJvL2mKnNSJOl6aJCHVfnRkWzaZ4JTPtoXEoJUxnUVsWKW6SbkXzjWubxWAWqJDjWpESITcdaNXIZDAtIJQsSHnbT/ES6y+Cr6fkXSjUNGfJnG/fZWplGNUiLjm+GgU5o4jgwyVUYfbIwpVb5wMdz4KTtNjnBweq6+v2t9+L8G/aBzi1QXA=')}


def _template(spec):
    box, cutoff, minimum, encoded = spec
    mask = Image.frombytes("1", (box[2] - box[0], box[3] - box[1]),
                           zlib.decompress(base64.b64decode(encoded))).convert("L")
    return box, [255 if value >= cutoff else 0 for value in range(256)], minimum, mask


_TEMPLATES = {name: _template(spec) for name, spec in _TEMPLATE_DATA.items()}
_POSITIVE = [0] + [255] * 255
_RED = [255 if value > 52 else 0 for value in range(256)]
_G_LOWER = [value * 685 // 1000 for value in range(256)]
_G_UPPER = [(value * 92 + 99) // 100 for value in range(256)]
_B_LOWER = [value * 7 // 100 for value in range(256)]
_B_UPPER = [(value * 58 + 99) // 100 for value in range(256)]
_EXCLUDED = ((0, 0, 143, 54), (663, 0, 896, 80), (717, 315, 896, 414),
             (405, 321, 485, 414), (0, 380, 896, 414))
_TERRAIN = tuple((224 + col * 56, 70 + row * 48, 280 + col * 56, 118 + row * 48)
                 if not (2 <= col <= 5 and 2 <= row <= 4) else None
                 for row in range(6) for col in range(8))


def _matches(gray, name):
    box, table, minimum, reference = _TEMPLATES[name]
    observed = gray.crop(box).point(table)
    intersection = ImageChops.darker(observed, reference).histogram()[255]
    union = ImageChops.lighter(observed, reference).histogram()[255]
    return intersection >= minimum * max(1, union)


def _gold_peak(image):
    red, green, blue = image.split()
    mask = red.point(_RED)
    # R>52, .685R<G<.92R, .07G<B<.58G。整数LUTで厳密な不等式。
    for left, right in ((green, red.point(_G_LOWER)), (red.point(_G_UPPER), green),
                        (green.point(_B_UPPER), blue), (blue, green.point(_B_LOWER))):
        mask = ImageChops.darker(mask, ImageChops.subtract(left, right).point(_POSITIVE))
    for box in _EXCLUDED:
        mask.paste(0, box)
    # 画面上端は除外しない。BoxBlurの端延長で上端に残った金壁も保持。
    return mask.filter(ImageFilter.BoxBlur(13)).getextrema()[1]


def _fingerprint(gray):
    # 文字・プレイヤーの中央領域を除き、地形の広い変化だけを照合する。
    return [round(ImageStat.Stat(gray.crop(box)).mean[0]) if box else 0 for box in _TERRAIN]


def analyze(raw):
    """画像を安全側へ分類。寸法不一致・不正画像・未対応画面はunknown。"""
    answer = {"state": "unknown", "gold": "unknown", "fingerprint": [],
              "gold_peak": 0, "restart_label": False}
    if type(raw) is not bytes or not 0 < len(raw) <= 4 * 1024 * 1024:
        return answer
    try:
        with Image.open(io.BytesIO(raw)) as source:
            if source.size != SIZE:
                return answer
            return analyze_image(source)
    except (OSError, ValueError, TypeError):
        return answer


def analyze_image(source):
    """既に検証・復号した原寸RGBを受け取り、二重decodeを避ける。"""
    from .native_scan import scan
    answer = {"state": "unknown", "gold": "unknown", "fingerprint": [],
              "gold_peak": 0, "restart_label": False}
    if not isinstance(source, Image.Image) or source.size != SIZE:
        return answer
    image = source if source.mode == "RGB" else source.convert("RGB")
    try:
        with image.convert("L") as gray:
            if _matches(gray, "continue"):
                answer.update(state="pause", restart_label=_matches(gray, "restart"))
            elif (all(_matches(gray, name) for name in ("icon", "footer", "zone_one", "floor_one"))
                  and not _matches(gray, "death")):
                result = scan(image.tobytes())
                peak, fingerprint = result if result is not None else (_gold_peak(image), _fingerprint(gray))
                answer.update(state="floor", gold="candidate" if peak >= 135 else "clear" if peak < 100 else "unknown",
                              gold_peak=peak, fingerprint=fingerprint)
            return answer
    finally:
        if image is not source:
            image.close()


def changed(a, b):
    """ハッシュ差や小さなanimationで新ランとしない。複数行・列の地形差を要求。"""
    if not all(type(value) is list and len(value) == FINGERPRINT_LENGTH
               and all(type(item) is int and 0 <= item <= 255 for item in value) for value in (a, b)):
        return False
    cells = [index for index, (old, new) in enumerate(zip(a, b)) if abs(old - new) >= 12]
    return len(cells) >= 6 and len({index % 8 for index in cells}) >= 3 and len({index // 8 for index in cells}) >= 2
