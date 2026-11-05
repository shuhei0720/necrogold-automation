"""Cadence Zone 1-1. Input and capture use LoopCtrl's local authenticated XCUITest service."""
import argparse
import base64
import io
import json
import subprocess
import sys
from urllib.parse import urlencode
from datetime import datetime
from pathlib import Path
import time
from collections import defaultdict

from PIL import Image, ImageChops, ImageOps
import loopctrl_rpc
import vision
import navigation
import diagnostics
from calibrate import CONFIG

HOST = "127.0.0.1:8300"
GAME = "jp.co.spike-chunsoft.necrodancerjp"
PAUSE = (.50,.056)
# Edge control layout 0: each SIDE has an upper/middle/lower segment.
# The middle of the top/bottom of the display is not an edge control.
MOVES = {"up":(.935,.30),"down":(.935,.70),"left":(.055,.5),"right":(.935,.5)}
ROOT = Path(__file__).resolve().parent
NOTIFY_NAME = "ネクロ通知"
VERSION = "R12"
MOVE_PERIOD = .35
TIMINGS = defaultdict(float)


def measured(name, action, *args, **kwargs):
    started = time.perf_counter()
    try:
        label = {"decode_frame":"画像の展開・補正", "inspect":"金壁・商品判定",
                 "scan":"経路用の画像解析", "minimap":"ミニマップ判定"}.get(getattr(action,"__name__",""))
        with diagnostics.stage(label or ("通信: "+name)):
            return action(*args, **kwargs)
    finally:
        TIMINGS[name] += time.perf_counter() - started


def timing_summary(started, previous):
    elapsed = time.perf_counter() - started
    capture = TIMINGS["screenshot"] - previous.get("screenshot", 0)
    front = TIMINGS["device_info"] - previous.get("device_info", 0)
    processing = TIMINGS["analysis"] - previous.get("analysis", 0)
    touch = TIMINGS["tap"] - previous.get("tap",0)
    crypto = TIMINGS["crypto"] - previous.get("crypto",0)
    size = (TIMINGS["jpeg_bytes"] - previous.get("jpeg_bytes",0))/1024
    return f"計{elapsed:.1f}秒・画像{capture:.1f}秒({size:.0f}KB/復号等{crypto:.1f}秒)・前面{front:.1f}秒・判定{processing:.1f}秒・入力{touch:.1f}秒"

# Two grayscale templates from the user's GAME PAUSE screen: the title and
# the Japanese Continue label. Sample only text, away from animated borders.
RESUME = (.5, .281)
OPTIONS = (.5, .5)
DONE = (.5, .69)
PAUSE_LABELS = (
    ((0.393, 0.153, 0.603, 0.236),
     "GWpTBDssLjEmW3JzSQEAEmtyLAlREUkRRDBsTz11cSyHcX8shWZjs6jDok8yAQAluWWHJ6wvmSOPoG6DoYVOH688ESW2om+mlcB9AQAAACWnI51qv3GaI5C+NhJ+TwEAr4qLTMCvdGRLv8B/FQAAJcmZc2/EgJsjj4aYYX2vawivYqCs0c+rYkm/nj4LAAAlt00nrMu/sCOPP0CUrX41BK4+gcBZdL9iSb9+AwIAACWnDBWjMaq3JY9jFo2+UAMBWZKzrEBbrFlCrLKKVwIAIZcLE48Yj3qSiF6SjYmmhzUIKSwiDRIiEQ0iLC0dAQAHHgIEHAUcEiwcCSoeFi0tEQ=="),
    ((0.431, 0.254, 0.559, 0.309),
     "AAAAAAIWAQAAAAAAAAAAAAAAAAAAAAAACQ8AAAABAQAABjkEPkwVAAAAAAACOQYAAAAzDgABLShLXRklJVxtKQAKbCg/NgQAAAAAAANeCgAIWpx1Px9gOo6gVkQLEhUIACVndoFCEDAgIBYBFVEICgIukkslH346dIZMJzxkcFMBKwwvPAAFSGVlRgIrQRlECVZGlFwlj5N+d2pzHiBtLQAACFMZAAAAAAAAB1pFXV8STVNzDx10R1NlIWcNAFgWABRaQwMAAAAAAAAke2EpWg8NXWQzHWduRHtdVwwqeRUADSEBAAAAAAAAAAABAQAUBAAcOCEAFDMKJiEVAxwuBQ=="),
)
LANDSCAPE_RATIO = 1792 / 828
TRANSPOSE = getattr(Image, "Transpose", Image)
RESTART_LABEL = json.loads((ROOT / "quick-restart.json").read_text())[0]


def label_matches(image, label):
    box, encoded = label
    rect = tuple(round(v * n) for v, n in zip(box, image.size * 2))
    sample = image.crop(rect).convert("L").resize((32, 8), vision.RESAMPLE.BILINEAR)
    return vision.correlation(sample.tobytes(), base64.b64decode(encoded), min_std=11) >= .78


def pause_menu(image):
    # Only resume when the touch target itself is visible. A banner over the
    # title can be tolerated if the Quick Restart label below also matches.
    title, resume = PAUSE_LABELS
    return label_matches(image, resume) and (label_matches(image, title) or patch_matches(image, RESTART_LABEL))


def options_menu(image):
    # The frame crosses the title's row. Keep that crop inside the central
    # title gap; including the frame makes an actual OPTION screen look too wide.
    # Validate four separate text rows, including the intended Done target.
    mask = image.resize((448,207), vision.RESAMPLE.BILINEAR).convert("L").point(lambda v: 255 if v > 105 else 0)
    for x0, top, x1, bottom, min_width, max_width in (
            (186,38,260,58,47,65), (155,60,293,74,88,111),
            (155,105,293,120,44,65), (155,135,293,151,13,23)):
        box = mask.crop((x0,top,x1,bottom)).getbbox()
        if box is None:
            return False
        left, first_row, right, last_row = box
        if not (min_width <= right-left <= max_width and last_row-first_row >= 6
                and abs((left+right)/2 + x0-224) <= 4):
            return False
    return True


def known_screen(image):
    return pause_menu(image) or options_menu(image) or vision.hud_matches(vision.small(image)) or vision.game_over(image)


def oriented(image, turn):
    return image.transpose(turn) if turn is not None else image


def rpc(method, params=None):
    try:
        started = time.perf_counter()
        response = measured(method, loopctrl_rpc.call, HOST, method, params or {}, timeout=15)
        engine = getattr(loopctrl_rpc,"_fast_crypto",None)
        if engine is not None:
            TIMINGS["crypto"] = engine.SECONDS
    except SystemExit as exc:
        raise RuntimeError(f"{method} に失敗。LoopCtrlの接続または承認を確認してください。{exc}") from exc
    if "error" in response or not isinstance(response.get("result"),dict):
        raise RuntimeError(method+" に失敗。追加タップを止めました。 "+str(response.get("error","結果なし")))
    return response["result"]


class StartupScreenError(RuntimeError):
    pass


class UnrecognizedGeometry(StartupScreenError):
    pass


def foreground_state(info):
    system = info.get("system")
    if not isinstance(system, dict):
        system = {}
    front = system.get("foreground_app")
    front = front.strip().lower() if isinstance(front, str) else ""
    return front, system.get("screen_locked")


class Game:
    @diagnostics.stage("前面アプリ確認")
    def guard(self, *, read_only=False):
        # iOS may briefly report no foreground app or SpringBoard while changing
        # apps. No input is permitted until the game itself is confirmed again.
        for attempt in range(6):
            if attempt:
                time.sleep(.5)
            front, locked = foreground_state(rpc("device_info"))
            if locked is False and front == GAME:
                self.visual_guard = False
                return attempt > 0
            if locked is not False or front not in ("", "unknown", "不明", "com.apple.springboard"):
                raise RuntimeError(f"前面確認で停止（前面 {front or '不明'}、ロック {locked}）。")
            if self.allow_visual_guard:
                self.visual_guard = True
                if not self.visual_guard_logged:
                    print(f"前面名={front or '不明'}。実画面と入力先を確認して進めます。", flush=True)
                    self.visual_guard_logged = True
                if not read_only and not known_screen(self.capture()):
                    raise StartupScreenError("実画面でゲームを確認できません。入力を止めました。")
                return False
            if attempt == 0:
                print(f"前面アプリを再確認中（{front or '不明'}）。入力は待機します。", flush=True)
        raise RuntimeError(f"6回確認してもゲームの前面を確認できません（前面 {front or '不明'}）。追加タップを止めました。")

    def __init__(self):
        self.size = None
        self.layout = None
        self.turn = None
        self.can_tap = False
        self.stretched = False
        self.capture_scale = 1
        self.dimensions = ""
        self.save_diagnostics = False
        self.capture_bytes = None
        self.assessment_frame = None
        self.last_quality = 0
        self.want_detail = False
        self.last_frame = None
        self.fast_decode = True
        self.allow_visual_guard = False
        self.visual_guard = False
        self.visual_guard_logged = False

    def remember_assessment_frame(self, image):
        # Used only by assess(), never by a pre-tap screen/foreground check.
        self.assessment_frame = (time.monotonic(), image)

    def take_assessment_frame(self):
        saved, self.assessment_frame = self.assessment_frame, None
        if saved is not None and time.monotonic() - saved[0] <= .75:
            return saved[1]
        return None

    def frame(self, quality=None):
        self.guard(read_only=True)
        return self.capture(quality)

    def capture(self, quality=None):
        # Full-screen, read-only capture; also used when process identity is
        # unavailable. Input authorization is always separate in tap().
        if quality is None:
            quality = .87 if self.want_detail else .60
        payload = rpc("screenshot", {"format":"jpeg", "quality":quality, "scale":self.capture_scale})
        self.last_quality = quality
        self.last_frame = measured("analysis", self.decode_frame, payload)
        return self.last_frame

    def detail_frame(self):
        return self.frame(quality=.87)

    def decode_frame(self, payload):
        raw = base64.b64decode(payload["data"])
        TIMINGS["jpeg_bytes"] += len(raw)
        if self.save_diagnostics:
            self.capture_bytes = raw
        with io.BytesIO(raw) as stream, Image.open(stream) as source:
            if source.format not in ("JPEG","PNG") or min(source.size)<=0 or max(source.size)>4096 or source.width*source.height>8_000_000:
                raise RuntimeError("画像サイズ・形式が想定範囲外です。")
            # Only movement-quality JPEGs use libjpeg's half-size IDCT.
            # Full-quality rejection/item frames keep all original detail.
            if self.fast_decode and source.format=="JPEG" and .59<=self.last_quality<=.61 and min(source.size)>=828:
                source.draft("RGB",(source.width//2,source.height//2))
            with diagnostics.stage("JPEG/PNGの展開"):
                source.load()
            image = source
            try:
                if source.getexif().get(274,1) != 1:
                    image = ImageOps.exif_transpose(source)
                if image.mode != "RGB":
                    converted = image.convert("RGB")
                    if image is not source:image.close()
                    image = converted
                with diagnostics.stage("画面の向き・サイズ補正"):
                    result = self.normalize_image(image, payload)
                # Only decoder-owned, immutable game frames opt into caching.
                result._necro_cache_frame = True
                return result
            finally:
                if image is not source:image.close()

    def normalize_image(self, image, payload):
        points = float(payload["point_width"]), float(payload["point_height"])
        self.dimensions = f"画像 {image.width}×{image.height}px、座標 {points[0]:g}×{points[1]:g}pt"
        if min(points) <= 0:
            raise RuntimeError(self.dimensions + "：座標サイズを取得できません。")
        # Changing capture resolution doesn't change the input coordinate space.
        aspect = image.width / image.height
        layout = aspect, points
        if self.layout == layout:
            if self.stretched:
                return image.resize((597,276), vision.RESAMPLE.BILINEAR)
            return oriented(image, self.turn).resize((597,276), vision.RESAMPLE.BILINEAR)

        # The runner sizes its JPEG using a cached SpringBoard frame. It may
        # remain portrait after Safari opens the game. Trust quarter-turns only
        # when the HUD or the two pause labels identify exactly one orientation.
        self.layout = None
        self.turn = None
        self.stretched = False
        self.can_tap = False
        self.size = points
        matching_points = abs(aspect / (points[0] / points[1]) - 1) <= .015
        if abs(aspect - LANDSCAPE_RATIO) <= .066 and matching_points:
            self.turn = None
            self.can_tap = True
            self.layout = layout
            return image.resize((597,276), vision.RESAMPLE.BILINEAR)
        if abs(1 / aspect - LANDSCAPE_RATIO) <= .066 and matching_points:
            upright = image.resize((597,276), vision.RESAMPLE.BILINEAR)
            if known_screen(upright):
                self.stretched = True
                # R6 on this device confirmed the left-edge-down input profile:
                # Resume (298,448) -> the 1-1 HUD. Reuse that profile directly.
                self.can_tap = True
                self.layout = layout
                return upright
            upright.close()
            candidates = [t for t in (TRANSPOSE.ROTATE_90, TRANSPOSE.ROTATE_270)
                          if known_screen(oriented(image, t))]
            if len(candidates) == 1:
                self.turn = candidates[0]
                self.can_tap = True
                self.layout = layout
                return oriented(image, self.turn).resize((597,276), vision.RESAMPLE.BILINEAR)
        raise UnrecognizedGeometry(self.dimensions + "：横向きのメニュー・1-1画面を確認できません。")

    def tap(self, point, *, expected=None):
        recovered = self.guard(read_only=True)
        if self.visual_guard:
            # A screenshot from launch/assessment is never an input permit.
            # Read again now, and validate THIS action's target. This keeps
            # working when iOS reports SpringBoard over the actual game.
            layout = self.layout
            image = self.capture(quality=.87)
            matches = expected or (on_floor if point in MOVES.values() else None)
            if matches is None or not matches(image) or self.layout != layout:
                raise StartupScreenError("実画面で今回の入力先を確認できません。タップは送っていません。")
        elif recovered:
            # After a wait, the earlier screenshot is stale. Startup menu
            # targets can be checked again before sending an input.
            if expected is None and point in MOVES.values():
                return False  # The navigator will read the board again.
            layout = self.layout
            if expected is None or not expected(self.frame()) or self.layout != layout:
                raise RuntimeError("前面はゲームに戻りましたが、タップ前の画面を再確認できず停止しました。")
        if not self.can_tap:
            raise RuntimeError(self.dimensions + "：タップ座標が未確認のため操作を停止しました。")
        x,y = point
        # Original left edge down: the notch is on the left in landscape.
        # XCUITest's portrait touch axes rotate even though the JPEG is upright.
        if self.stretched or self.turn == TRANSPOSE.ROTATE_90:
            x,y = 1-y,x
        elif self.turn == TRANSPOSE.ROTATE_270:
            x,y = y,1-x
        # Explicitly disable the default 2-second visual settling pass. This
        # game animates continuously; subsequent reads validate game state.
        # Keep LoopCtrl's ordinary input checks (do not use manual:true).
        target = {"x":x*self.size[0], "y":y*self.size[1], "settle":False}
        rpc("tap", target)
        if point in (DONE, RESUME):
            print("タップ送信済み (%d, %d)pt" % (round(target["x"]), round(target["y"])), flush=True)
        return True


def patch_matches(im,step):
    x,y=step["point"];w,h=im.size
    box=tuple(round(v) for v in ((x-.043)*w,(y-.027)*h,(x+.043)*w,(y+.027)*h))
    sample=im.crop(box).convert("L").resize((56,15),vision.RESAMPLE.BILINEAR)
    return vision.correlation(sample.tobytes(),step["patch"],min_std=11) >= .74


def fresh(im):
    return vision.mask_overlap(vision.small(im),(77,261,102,275),120,vision.MASKS["timer"]) > .67


def on_floor(im):
    return not vision.game_over(im) and vision.hud_matches(vision.small(im))


def room_thumbnail(im):
    # Exclude HUD, minimap and edges. Coarse cells suppress single-pixel
    # animations when comparing the room before and after a Quick Restart.
    return im.convert("L").resize((25,11), vision.RESAMPLE.BILINEAR).crop((4,2,21,9))


def restart(game,steps):
    before = game.frame()
    state, _ = measured("analysis", vision.inspect, before)
    if state=="dead":raise RuntimeError("ゲームオーバーを検出しました。リスタート入力を停止します。")
    if state in ("ring", "possible"):
        return state, before
    if state == "unknown":
        raise RuntimeError("1-1を確認できません。")
    game.tap(PAUSE, expected=on_floor)
    for step in steps:
        for _ in range(6):
            time.sleep(.20)
            if patch_matches(game.frame(),step):break
        else:raise RuntimeError("登録したリスタート画面を確認できません。")
        game.tap(step["point"], expected=lambda im: patch_matches(im, step))
    game.remember_assessment_frame(wait_new_floor(game,steps,before))


def wait_new_floor(game,steps,before):
    previous = room_thumbnail(before)
    was_early = fresh(before)
    faded = False
    for _ in range(8):
        time.sleep(.26)
        im=game.frame()
        if not on_floor(im):
            faded |= im.convert("L").resize((32,16)).getextrema()[1] < 30
            continue
        if patch_matches(im,steps[-1]):
            continue
        changed = ImageChops.difference(previous, room_thumbnail(im)).histogram()
        if sum(changed[20:]) >= 8 or (fresh(im) and (not was_early or faded)):
            return im
    raise RuntimeError("リスタート後に1-1の更新を確認できません。連打せず停止しました。")


def scene_for(image):
    scene = measured("analysis", navigation.scan, image)
    if not scene.gold:
        view = measured("analysis", vision.minimap, image)
        if view and view.wall:
            for points,terrain in ((view.floor,"floor"),(view.doors,"dirt"),(view.wall,"gold"),(view.goods,"item")):
                for point in points:
                    scene.tiles.setdefault(point,terrain)
            scene.gold = {p for p,k in scene.tiles.items() if k=="gold"}
    return scene


def assess(game, tracking=False):
    # A single overlaid price or a camera-in-motion frame cannot rule out the ring.
    first = game.take_assessment_frame() if hasattr(game,"take_assessment_frame") else None
    if first is None:
        first=game.frame()
    state,score=measured("analysis", vision.inspect, first)
    if state=="dead":raise RuntimeError("ゲームオーバーを検出しました。移動入力を停止します。")
    if state=="unknown":
        # If reduced JPEG decoding loses the small floor label, keep full
        # decode detail for this run. Never guess a floor from a blurry HUD.
        game.fast_decode=False
        # During a reset a fade can briefly leave the latest captured HUD incomplete.
        time.sleep(.22)
        first=game.detail_frame() if hasattr(game,"detail_frame") else game.frame()
        state,score=measured("analysis", vision.inspect, first)
        if state=="dead":raise RuntimeError("ゲームオーバーを検出しました。移動入力を停止します。")
        if state=="unknown":return state,first,None
    if state in ("ring","possible"):
        return state,first,None
    # Following visible gold does not discard the run. One fresh image suffices;
    # destructive clear/miss decisions still require two agreeing observations.
    if state == "near" or (state == "clear" and tracking):
        return "near", first, scene_for(first)
    time.sleep(.12)
    # The final rejection decision retains full-quality detail. Reduced JPEG
    # quality is for approaching the shop, not for ruling out a thin ring.
    im=game.detail_frame() if hasattr(game,"detail_frame") else game.frame()
    second,score=measured("analysis", vision.inspect, im)
    if second=="dead":raise RuntimeError("ゲームオーバーを検出しました。移動入力を停止します。")
    if second in ("ring","possible","unknown"):return second,im,None
    if second==state=="miss":return "miss",im,None
    scene=scene_for(im)
    if second==state=="clear" and not tracking and not scene.gold:
        return "clear",im,None
    return "near",im,scene


def notify(text):
    url="shortcuts://run-shortcut?"+urlencode({"name":NOTIFY_NAME,"input":"text","text":text})
    rpc("open_url",{"url":url})
    print("通知ショートカットに実行を依頼しました。",flush=True)


def pause_run(game,im,kind,steps,attempt):
    folder=ROOT/"results"
    name=datetime.now().strftime("%Y%m%d-%H%M%S-%f")+"-"+kind+".png"
    try:
        game.tap(PAUSE, expected=on_floor)
    except (RuntimeError, OSError) as exc:
        # The device may have received a tap even if its acknowledgement was lost.
        print("ポーズ入力を確認できません。再送せず画面を確認します。", exc, flush=True)
    try:
        folder.mkdir(exist_ok=True)
        im.save(folder/name)
    except OSError as exc:
        print("検出画像を保存できませんでした。", exc, flush=True)
        name = ""
    paused=False
    try:
        for _ in range(4):
            time.sleep(.18)
            screen = game.frame()
            if pause_menu(screen) or patch_matches(screen,steps[0]):
                paused=True;break
    except (RuntimeError, OSError) as exc:
        print("ポーズの読み戻しに失敗しました。", exc, flush=True)
    label={"ring":"のろいのゆびわを検出","possible":"指輪候補（目視確認）","unread":"店頭未確認","limit":"上限に到達"}[kind]
    message=f"ネクロダンサー 第{attempt}回・{label}・"+("ポーズ確認済み" if paused else "ポーズ未確認。ゲームを確認してください")
    print(message,name,flush=True)
    # Notification is the LAST action; even if the shortcut fails we never re-roll the find.
    if kind in ("ring","possible"):
        game.guard()
        notify(message)


@diagnostics.stage("金壁・店への探索")
def run(game,steps,limit,hold):
    attempt=0
    while limit==0 or attempt<limit:
        attempt+=1
        if attempt>1:
            print(f"第{attempt}回へリスタート中", flush=True)
            reset_started, reset_previous = time.perf_counter(), dict(TIMINGS)
            late_hit = restart(game,steps)
            if late_hit:
                kind, image = late_hit
                pause_run(game,image,kind,steps,attempt-1)
                return
            print("リスタート完了（"+timing_summary(reset_started,reset_previous)+"）",flush=True)
        game.want_detail=False
        nav=navigation.Navigator()
        tracking=False
        visited=set()
        stale=0
        lost=0
        while True:
            assess_started, assess_previous = time.perf_counter(), dict(TIMINGS)
            state,im,scene=assess(game,tracking)
            assessment_time = timing_summary(assess_started,assess_previous)
            if state=="unknown":raise RuntimeError("1-1を読み取れないため停止しました。")
            if state in ("ring","possible"):
                pause_run(game,im,state,steps,attempt);return
            if state in ("clear","miss"):break
            if not tracking:
                print(f"第{attempt}回 金壁の手掛かりあり（{assessment_time}）",flush=True)
            tracking=True
            move=measured("analysis", nav.choose, scene)
            assessment_time = timing_summary(assess_started,assess_previous)
            if nav.last_motion is not None:
                print("実移動: "+("未確認" if nav.last_motion<0 else str(nav.last_motion)+"マス")+
                      f"／現在位置 {nav.pos}／連続未進行 {nav.no_progress}",flush=True)
            if nav.halt_reason:
                print(nav.halt_reason,flush=True)
                state="unread"
                if hold:pause_run(game,im,state,steps,attempt);return
                break
            game.want_detail=nav.crossed or (nav.entrance is not None and nav.pos==nav.entrance)
            # A newly reached tile or a newly seen piece of gold/perimeter means progress.
            fingerprint=(nav.pos, nav.entrance, tuple(sorted(scene.gold)))
            if fingerprint in visited:stale+=1
            else:visited.add(fingerprint);stale=0
            if not move:
                lost+=1
                if lost<4:
                    time.sleep(.18)
                    continue
            else:lost=0
            if not move or stale>=12 or len(visited)>240:
                state="unread"
                if hold:pause_run(game,im,state,steps,attempt);return
                break
            count=nav.burst(scene,move)
            sent=0
            motion_started=time.perf_counter()
            for _ in range(count):
                tick=time.perf_counter()
                if game.tap(MOVES[move]) is False:break
                sent+=1
                # Account for time already spent on guard and input. Do not
                # add another fixed sleep on top of a slow RPC.
                time.sleep(max(0,MOVE_PERIOD-(time.perf_counter()-tick)))
            nav.pending=move if sent else None
            nav.pending_count=max(1,sent)
            print(f"第{attempt}回 移動 {move}×{sent}／直前の判定 {assessment_time}／入力区間 {time.perf_counter()-motion_started:.1f}秒",flush=True)
        print(f"第{attempt}回 "+{"clear":"開幕に金壁なし","miss":"店頭3枠に指輪なし","unread":"入口・陳列未確認"}[state]+f"（{assessment_time}）",flush=True)
    im=game.frame()
    if vision.hud_matches(vision.small(im)):pause_run(game,im,"limit",steps,attempt)


@diagnostics.stage("ゲーム起動・前面復帰の確認")
def start_game():
    print("ゲームを開きます。ポーズ画面では「ゲームを続行」を直接押します。", flush=True)
    result = rpc("launch_app", {"bundle_id":GAME})
    front = result.get("foreground_app")
    print(f"launch_app: 前面={front if isinstance(front,str) else '不明'}、システム通知={result.get('system_alert', False)}", flush=True)
    if result.get("system_alert") is True:
        raise StartupScreenError("システムの確認画面が出ています。確認画面を閉じてから開始してください。タップは送っていません。")
    game = Game()
    # launch_app succeeded, but iOS may be unable to name the front process.
    # Read the live screen immediately. Every ambiguous-app tap needs a NEW
    # full-screen capture and its exact target, never the launch acknowledgement.
    game.allow_visual_guard = True
    return game


@diagnostics.stage("起動時のポーズ・1-1画面確認")
def opening_frame(game):
    # Recognize the actual screen before acting. Stretched captures use the
    # left-edge-down touch profile confirmed on the user's phone in R6.
    for attempt in range(12):
        if attempt:
            time.sleep(.8)
        # Portrait-sized JPEGs are expected; resetting the runner here would
        # clear its foreground cache. Observe the fade without resetting.
        try:
            image = game.frame()
        except UnrecognizedGeometry:
            continue
        if known_screen(image):
            return image
        game.layout = None
    raise UnrecognizedGeometry(game.dimensions + "：起動後12回の画像でポーズ、OPTION、1-1のいずれも確認できません。")


def check_screen(game):
    # Keep the final capture that was actually inspected, before EXIF handling,
    # resizing or rotation. Do not capture another screen after the failure.
    game.save_diagnostics = True
    corrected = None
    try:
        image = opening_frame(game)
    except UnrecognizedGeometry as exc:
        result = str(exc)
        save = True
    else:
        if pause_menu(image) or options_menu(image):
            result = "ポーズ画面を認識（GAME PAUSE）" if pause_menu(image) else "オプション画面を認識（OPTION）"
            save = not game.can_tap
        else:
            state, score = vision.inspect(image)
            result = f"{state} ({score:.2f})"
            save = state == "unknown" or not game.can_tap
        result += "／" + game.dimensions
        if game.stretched:
            result += " → 896×414に縦伸び補正。左側が下の確認済み座標で、開始時は直接「ゲームを続行」を押します。"
            corrected = image
        elif game.can_tap:
            result += "・入力座標の向きを特定"
    print("画面判定:", result, flush=True)
    if save and game.capture_bytes:
        game.guard()
        filename = ROOT / "loopctrl-frame.jpg"
        temporary = filename.with_suffix(".tmp")
        temporary.write_bytes(game.capture_bytes)
        temporary.replace(filename)
        print("診断画像を保存:", filename.name, flush=True)
        if corrected is not None:
            preview = ROOT / "loopctrl-landscape.jpg"
            temporary = preview.with_suffix(".tmp")
            corrected.save(temporary, format="JPEG", quality=92)
            temporary.replace(preview)
            print("横長に補正した画像:", preview.name, flush=True)


def wait_for_start_screen(game, matches, description):
    layout = game.layout
    for _ in range(6):
        time.sleep(.20)
        image = game.frame()
        if game.layout != layout:
            raise StartupScreenError("開始中に画面の座標が変わりました。")
        if matches(image):
            return image
    raise StartupScreenError(description + "を確認できません。追加タップを止めました。")


@diagnostics.stage("ポーズ解除・1-1への復帰確認")
def begin(game, initial):
    if vision.game_over(initial):raise RuntimeError("ゲームオーバー画面です。通常オールゾーン1-1を開いてから開始してください。")
    if options_menu(initial):
        print("すでに開いているOPTIONを「完了」で閉じます。", flush=True)
        game.tap(DONE, expected=options_menu)
        initial = wait_for_start_screen(game, pause_menu, "「完了」からGAME PAUSEへの復帰")
    if pause_menu(initial):
        print("ポーズ画面を確認。「ゲームを続行」を押します。", flush=True)
        game.tap(RESUME, expected=pause_menu)
        game.capture_scale = 2
        confirmed = wait_for_start_screen(game, lambda im: vision.hud_matches(vision.small(im)), "続行後の1-1")
        game.remember_assessment_frame(confirmed)
        print("1-1への復帰を確認。自動操作を開始します。", flush=True)
        return
    if not vision.hud_matches(vision.small(initial)):
        raise RuntimeError("開始時にポーズメニューまたは1-1を確認できません。")
    print("1-1を確認。自動操作を開始します。", flush=True)
    game.capture_scale = 2


def load_steps():
    source = CONFIG if CONFIG.exists() else ROOT / "quick-restart.json"
    try:
        steps = json.loads(source.read_text())
        if not isinstance(steps,list) or not 1 <= len(steps) <= 2:
            raise ValueError()
        for step in steps:
            point, sample = step["point"], step["patch"]
            if (len(point) != 2 or not all(type(n) in (float,int) and .04<n<.96 for n in point)
                    or len(sample) != 840 or not all(type(v) is int and 0<=v<=255 for v in sample)
                    or max(sample)-min(sample)<45):
                raise ValueError()
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"リスタート位置の設定を読み取れません（{source.name}）。登録内容を確認してください。") from exc
    return steps


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("mode",choices=["setup","check","run","hold","test-notify"])
    parser.add_argument("--limit",type=int,default=0,help="0 は当たりまたは停止操作まで")
    args=parser.parse_args()
    print(f"実行版 {VERSION} / {ROOT}", flush=True)
    engine=getattr(loopctrl_rpc,"_fast_crypto",None)
    print("通信暗号処理: "+("高速ネイティブ" if engine and engine.AVAILABLE else "Python互換動作"),flush=True)
    if args.mode=="setup":
        from calibrate import configure
        configure();return
    if args.limit<0:raise ValueError("上限は0以上で指定してください。")
    # Pair only when no saved record exists. First use still requires the user to approve.
    if not Path(loopctrl_rpc.STORE).exists():
        subprocess.run([sys.executable,str(ROOT/"loopctrl_rpc.py"),"--host",HOST,"pair","--name","NecroGold"],check=True)
    if args.mode=="test-notify":
        notify("ネクロダンサーの当たり通知テスト");return
    if args.mode=="check":
        check_screen(start_game())
        return
    steps=load_steps()
    game=start_game()
    game.save_diagnostics = True
    try:
        initial = opening_frame(game)
        begin(game,initial)
    except RuntimeError:
        # Preserve the actual failed run. A later screen-check may show a
        # perfectly readable pause menu which wasn't visible during startup.
        if game.capture_bytes:
            try:
                filename = ROOT / "start-failed.jpg"
                temporary = filename.with_suffix(".tmp")
                temporary.write_bytes(game.capture_bytes)
                temporary.replace(filename)
                print("今回の開始失敗画像:", filename.name, flush=True)
            except (RuntimeError, OSError) as exc:
                print("開始失敗画像を保存できませんでした。", exc, flush=True)
        raise
    finally:
        game.save_diagnostics = False
        game.capture_bytes = None
    try:
        run(game,steps,args.limit,args.mode=="hold")
    except Exception:
        if game.last_frame is not None:
            try:
                game.last_frame.save(ROOT/"failure-frame.jpg",quality=92)
                print("停止直前の画像を保存: failure-frame.jpg",flush=True)
            except OSError as exc:print("停止画像の保存失敗:",exc,flush=True)
        raise


if __name__=="__main__":
    diagnostics.enable()
    try:
        main()
    except KeyboardInterrupt:
        diagnostics.finish("stopped")
        print("停止: 中断操作を受け付けました。",flush=True)
        raise SystemExit(130)
    except Exception as exc:
        import traceback
        diagnostics.finish("error")
        print("停止:",exc,flush=True)
        traceback.print_exc()
        raise SystemExit(1)
    else:
        diagnostics.finish("completed")
