"""Offline regression tests. Only images in testdata are used; no device input is sent."""
import base64
from contextlib import redirect_stdout
import io
import json
import hashlib
import hmac
import random
import os
import signal
import subprocess
import time
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from PIL import Image

import navigation
import phone
import vision

FIXTURES = Path(__file__).resolve().parent / "testdata"
STEPS = json.loads((phone.ROOT / "quick-restart.json").read_text())
ROUTE = [(104, "left"), (109, "left"), (112, "up"), (115, "left"),
         (119, "left"), (121, "left"), (124, None)]


def fixture(filename):
    with Image.open(FIXTURES / filename) as source:
        return source.convert("RGB")


def floor_image(index):
    return fixture(f"floor-{index:03}.jpg")


def store_with_ring(slot):
    board = floor_image(124)
    xs, sign_y = vision.signs(vision.small(board))
    with Image.open(FIXTURES.parent / "ring.png") as source:
        ring = source.convert("RGBA").crop((0,0,22,19)).resize((33,29), vision.RESAMPLE.NEAREST)
    board.paste(ring, (round(1.5*xs[slot])-16, round(1.5*(sign_y+32))-14), ring)
    return board


def recorded_options():
    # Real device screenshot, including the border that exposed the R5 bug.
    return fixture("options.png")


def edge_direction(u,v):
    if u>.90:
        return "up" if v<.40 else ("down" if v>.60 else "right")
    if u<.10:
        return "up" if v<.40 else ("down" if v>.60 else "left")
    return None


class RecordedGame:
    """Each true tap must produce the expected event in the recorded room."""
    def __init__(self, slot=1, initial="pause", portrait=True, wrong_side=False):
        self.screen = initial
        self.floor = 0  # Clear floor, shop without the ring, shop with the inserted ring.
        self.position = 0
        self.slot = slot
        self.portrait = portrait
        self.wrong_side = wrong_side
        self.events = []
        self.taps = []
        self.messages = []
        self.responses = {}
        self.foregrounds = []
        self.foreground_after_resume = []
        self.locked = False

    def screenshot(self, scale, quality=.87):
        key = (self.screen, self.floor, self.position, scale, quality)
        if key not in self.responses:
            if self.screen == "pause":
                image = fixture("pause.jpg")
            elif self.screen == "options":
                image = recorded_options()
            elif self.screen == "other":
                image = Image.new("RGB", (896,414))
            else:
                index = ROUTE[self.position][0] if self.floor else 18
                image = store_with_ring(self.slot) if self.floor == 2 and index == 124 else floor_image(index)
            w,h = (414,896) if self.portrait else (896,414)
            data = io.BytesIO()
            image.resize((w*scale,h*scale), vision.RESAMPLE.BICUBIC).save(data, "JPEG", quality=round(quality*100))
            self.responses[key] = dict(point_width=w, point_height=h,
                                       data=base64.b64encode(data.getvalue()).decode())
        return self.responses[key]

    def apply_tap(self, x, y):
        self.taps.append((round(x),round(y)))
        if self.portrait:
            u,v = (1-y/896,x/414) if self.wrong_side else (y/896,1-x/414)
        else:
            u,v = x/896,y/414
        def at(point):
            return abs(u-point[0]) < .015 and abs(v-point[1]) < .015
        if self.screen == "pause" and at(phone.OPTIONS):
            self.events.append("options")
            self.screen = "options"
        elif self.screen == "options" and at(phone.DONE):
            self.events.append("done")
            self.screen = "pause"
        elif self.screen == "options" and self.wrong_side:
            self.events.append("other")
            self.screen = "other"
        elif self.screen == "pause" and at(phone.RESUME):
            self.events.append("resume")
            self.screen = "play"
            self.foregrounds.extend(self.foreground_after_resume)
        elif self.screen == "play" and at(phone.PAUSE):
            self.events.append("pause")
            self.screen = "pause"
        elif self.screen == "pause" and at(STEPS[0]["point"]):
            self.events.append("restart")
            self.floor += 1
            assert self.floor <= 2, "reset after ring"
            self.position = 0
            self.screen = "play"
        elif self.wrong_side and self.screen == "pause":
            self.events.append("other")
            self.screen = "other"
        else:
            assert self.screen == "play" and self.floor > 0, (self.screen,u,v)
            direction = ROUTE[self.position][1]
            # Independent control zones from the actual edge layout, NOT
            # phone.MOVES. Wrong code coordinates must fail this replay.
            actual = edge_direction(u,v)
            assert direction and direction==actual, (self.position,direction,u,v,actual)
            self.events.append(direction)
            self.position += 1

    def rpc(self, method, args=None):
        if method == "device_info":
            front = self.foregrounds.pop(0) if self.foregrounds else phone.GAME
            return {"system":{"screen_locked":self.locked, "foreground_app":front}}
        if method in ("launch_app","reset"):
            return {}
        if method == "screenshot":
            return self.screenshot(args["scale"],args.get("quality",.87))
        if method == "tap":
            self.apply_tap(args["x"],args["y"])
            return {}
        if method == "open_url":
            params = parse_qs(urlparse(args["url"]).query)
            assert self.screen == "pause" and params["name"] == [phone.NOTIFY_NAME]
            self.messages.extend(params["text"])
            return {}
        raise AssertionError(method)


class Regression(unittest.TestCase):
    def setUp(self):
        # Any unmocked attempt to reach the real phone fails this test.
        denied = patch.object(phone.loopctrl_rpc,"call",side_effect=AssertionError("unexpected network call"))
        denied.start()
        self.addCleanup(denied.stop)
        no_sleep = patch.object(phone.time,"sleep",lambda _:None)
        no_sleep.start()
        self.addCleanup(no_sleep.stop)

    def test_startup_unknown_app_resumes_from_actual_pause_without_polling(self):
        for front in (None,"com.apple.springboard"):
            device=RecordedGame();calls=[]
            def rpc(method,args=None):
                calls.append(method)
                if method=="device_info":return {"system":{"screen_locked":False,"foreground_app":front}}
                return device.rpc(method,args)
            with self.subTest(front=front),patch.object(phone,"rpc",rpc),redirect_stdout(io.StringIO()):
                game=phone.start_game()
                phone.begin(game,phone.opening_frame(game))
            self.assertEqual(device.events,["resume"])
            self.assertEqual(device.taps,[(298,448)])
            self.assertEqual(calls.count("launch_app"),1)
            self.assertNotIn("activate_app",calls)
            self.assertNotIn("reset",calls)
            self.assertLessEqual(calls.count("device_info"),3)

    def test_named_foreground_normalization_and_no_extra_captures(self):
        device=RecordedGame();calls=[]
        def rpc(method,args=None):
            calls.append(method)
            if method=="device_info":return {"system":{"screen_locked":False,"foreground_app":"  "+phone.GAME.upper()+"  "}}
            return device.rpc(method,args)
        with patch.object(phone,"rpc",rpc),redirect_stdout(io.StringIO()):
            game=phone.start_game()
            phone.begin(game,phone.opening_frame(game))
        self.assertEqual(device.events,["resume"])
        self.assertEqual(calls.count("screenshot"),2)  # pause, then resumed 1-1

    def test_unknown_app_requires_current_target_not_old_pause(self):
        for current in ("options","other"):
            device=RecordedGame();calls=[]
            def rpc(method,args=None):
                calls.append(method)
                if method=="device_info":return {"system":{"screen_locked":False,"foreground_app":None}}
                return device.rpc(method,args)
            with self.subTest(current=current),patch.object(phone,"rpc",rpc),redirect_stdout(io.StringIO()):
                game=phone.start_game();initial=phone.opening_frame(game)
                device.screen=current
                with self.assertRaises(RuntimeError):phone.begin(game,initial)
            self.assertEqual(device.events,[])
            self.assertNotIn("tap",calls)

    def test_unknown_app_with_obscured_resume_does_not_tap(self):
        device=RecordedGame()
        def rpc(method,args=None):
            if method=="device_info":return {"system":{"screen_locked":False,"foreground_app":None}}
            return device.rpc(method,args)
        with patch.object(phone,"rpc",rpc),redirect_stdout(io.StringIO()):
            game=phone.start_game();initial=phone.opening_frame(game)
            covered=initial.copy();covered.paste((160,160,160),(240,65,350,90))
            with patch.object(game,"capture",return_value=covered):
                with self.assertRaisesRegex(phone.StartupScreenError,"入力先"):
                    phone.begin(game,initial)
        self.assertEqual(device.events,[])

    def test_visual_mode_still_blocks_other_apps_locks_and_alerts(self):
        for system in ({"screen_locked":True,"foreground_app":phone.GAME},
                       {"screen_locked":False,"foreground_app":"com.apple.mobilesafari"},
                       {"screen_locked":False,"foreground_app":"com.apple.Preferences"},
                       {},None,"malformed"):
            calls=[]
            def rpc(method,args=None):
                calls.append(method)
                if method=="launch_app":return {}
                if method=="device_info":return {"system":system}
                raise AssertionError(method)
            with self.subTest(system=system),patch.object(phone,"rpc",rpc),redirect_stdout(io.StringIO()):
                game=phone.start_game()
                with self.assertRaises(RuntimeError):phone.opening_frame(game)
            self.assertEqual(calls,["launch_app","device_info"])
        with patch.object(phone,"rpc",return_value={"system_alert":True}) as rpc,redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(phone.StartupScreenError,"確認画面"):phone.start_game()
            self.assertEqual(rpc.call_count,1)

    def test_unknown_foreground_full_run_through_restarts(self):
        device=RecordedGame();calls=[]
        def rpc(method,args=None):
            calls.append(method)
            if method=="device_info":return {"system":{"screen_locked":False,"foreground_app":None}}
            return device.rpc(method,args)
        with tempfile.TemporaryDirectory() as tmp,patch.object(phone,"ROOT",Path(tmp)), \
             patch.object(phone,"rpc",rpc),redirect_stdout(io.StringIO()):
            game=phone.start_game()
            phone.begin(game,phone.opening_frame(game))
            phone.run(game,STEPS,3,True)
        self.assertNotIn("options",device.events)
        self.assertEqual(device.events.count("resume"),1)
        self.assertEqual(device.events.count("restart"),2)
        self.assertEqual(len(device.messages),1)
        self.assertNotIn("activate_app",calls)
        self.assertNotIn("reset",calls)

    def test_visual_foreground_failure_records_phase_and_image(self):
        import diagnostics
        device=RecordedGame()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);record=root/"stage.json"
            def rpc(method,args=None):
                if method=="device_info":return {"system":{"screen_locked":False,"foreground_app":None}}
                if method=="tap":raise RuntimeError("tap transport failed")
                return device.rpc(method,args)
            with patch.object(diagnostics,"_path",record),patch.object(diagnostics,"_current",None), \
                 patch.object(phone,"ROOT",root),patch.object(phone,"rpc",rpc), \
                 patch.object(phone,"CONFIG",root/"menu.json"),patch.object(phone,"load_steps",return_value=STEPS), \
                 patch.object(phone.loopctrl_rpc,"STORE",str(record)),patch.object(sys,"argv",["phone.py","hold"]), \
                 redirect_stdout(io.StringIO()):
                record.write_text("{}")
                with self.assertRaisesRegex(RuntimeError,"tap transport failed"):phone.main()
                self.assertEqual(diagnostics.read_record(record)["phase"],"ポーズ解除・1-1への復帰確認")
                self.assertTrue((root/"start-failed.jpg").exists())

    def test_full_runs(self):
        for slot, initial, portrait in [(0,"pause",True),(1,"options",True),(2,"pause",True),
                                       (1,"pause",False),(1,"play",True)]:
            with self.subTest(slot=slot,initial=initial,portrait=portrait), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root/"quick-restart.json").write_text(json.dumps(STEPS))
                device = RecordedGame(slot, initial, portrait)
                device.foreground_after_resume = ["com.apple.springboard", None,
                                                   "com.apple.springboard", phone.GAME]
                with patch.object(phone,"rpc",device.rpc), patch.object(phone,"ROOT",root), \
                     patch.object(phone,"CONFIG",root/"missing"), patch.object(sys,"argv",["phone.py","hold"]), \
                     patch.object(phone.loopctrl_rpc,"STORE",str(root/"quick-restart.json")), redirect_stdout(io.StringIO()):
                    phone.main()
                walk = [direction for _,direction in ROUTE if direction]
                opening = ["done","resume"] if initial=="options" else (["resume"] if initial=="pause" else [])
                self.assertEqual(device.events,opening+["pause","restart"]+walk+["pause","restart"]+walk+["pause"])
                self.assertNotIn("options",device.events)
                self.assertEqual(len(device.messages),1)
                self.assertIn("ポーズ確認済み",device.messages[0])
                self.assertEqual(len(list((root/"results").glob("*.png"))),1)

    def test_before_any_input_and_after_menu_ack(self):
        scenarios = [([None]*6,False,0), ([None,"com.apple.mobilesafari"],False,0),
                     ([phone.GAME],True,0), ([phone.GAME],False,1),
                     (["com.apple.springboard"]*6,False,0),
                     (["com.apple.springboard"],True,0)]
        for states, locked, count in scenarios:
            device = RecordedGame()
            device.foregrounds = list(states)
            device.locked = locked
            device.foreground_after_resume = [None]*6
            with patch.object(phone,"rpc",device.rpc), self.assertRaises(RuntimeError), redirect_stdout(io.StringIO()):
                game = phone.Game()
                phone.begin(game,phone.opening_frame(game))
            self.assertEqual(len(device.events),count)

    def test_actual_options_image_and_compression(self):
        original = recorded_options()
        self.assertTrue(phone.options_menu(original))
        for scale in (1,2):
            for method in (vision.RESAMPLE.NEAREST, vision.RESAMPLE.BILINEAR,
                           vision.RESAMPLE.BICUBIC, vision.RESAMPLE.LANCZOS):
                with self.subTest(scale=scale, method=method):
                    stretched = original.resize((414*scale,896*scale),method)
                    encoded = io.BytesIO()
                    stretched.save(encoded,"JPEG",quality=87)
                    encoded.seek(0)
                    restored = Image.open(encoded).convert("RGB").resize((896,414),vision.RESAMPLE.LANCZOS)
                    self.assertTrue(phone.options_menu(restored))
        self.assertFalse(phone.options_menu(fixture("pause.jpg")))
        self.assertFalse(phone.options_menu(floor_image(124)))
        for box in ((186,38,260,58),(155,60,293,74),(155,105,293,120),(155,135,293,151)):
            # All four labels must be visible before tapping Done.
            incomplete = original.resize((448,207),vision.RESAMPLE.BILINEAR)
            incomplete.paste((0,0,0),box)
            self.assertFalse(phone.options_menu(incomplete))

    def test_springboard_persists_after_resume(self):
        device = RecordedGame()
        device.foreground_after_resume = ["com.apple.springboard"]*6
        with patch.object(phone,"rpc",device.rpc), redirect_stdout(io.StringIO()):
            game=phone.Game()
            initial=phone.opening_frame(game)
            with self.assertRaisesRegex(RuntimeError,"6回確認"):
                phone.begin(game,initial)
        self.assertEqual(device.events,["resume"])

    def test_springboard_then_other_app_stops_after_resume(self):
        device = RecordedGame()
        device.foreground_after_resume = ["com.apple.springboard","com.apple.mobilesafari"]
        with patch.object(phone,"rpc",device.rpc), redirect_stdout(io.StringIO()):
            game=phone.Game()
            initial=phone.opening_frame(game)
            with self.assertRaisesRegex(RuntimeError,"mobilesafari"):
                phone.begin(game,initial)
        self.assertEqual(device.events,["resume"])

    def test_wrong_rotation(self):
        for initial in ("pause","options"):
            device = RecordedGame(initial=initial,wrong_side=True)
            with patch.object(phone,"rpc",device.rpc), self.assertRaises(phone.StartupScreenError), redirect_stdout(io.StringIO()):
                game=phone.Game()
                phone.begin(game,phone.opening_frame(game))
            self.assertEqual(device.events,["other"])

    def test_direct_resume_uses_confirmed_coordinates(self):
        device=RecordedGame()
        with patch.object(phone,"rpc",device.rpc), redirect_stdout(io.StringIO()):
            game=phone.Game()
            phone.begin(game,phone.opening_frame(game))
        # Independent values recorded on the user's phone in R6, 2026-11-05.
        self.assertEqual(device.taps,[(298,448)])
        self.assertEqual(device.events,["resume"])
        self.assertEqual(device.screen,"play")

    def test_frame_reuse_is_one_shot_and_expires(self):
        game=phone.Game()
        sample=floor_image(18)
        with patch.object(phone.time,"monotonic",return_value=10):
            game.remember_assessment_frame(sample)
        with patch.object(phone.time,"monotonic",return_value=10.5):
            self.assertIs(game.take_assessment_frame(),sample)
            self.assertIsNone(game.take_assessment_frame())
        with patch.object(phone.time,"monotonic",return_value=20):
            game.remember_assessment_frame(sample)
        with patch.object(phone.time,"monotonic",return_value=21):
            self.assertIsNone(game.take_assessment_frame())

    def test_gold_walk_uses_one_frame_but_reset_decisions_use_two(self):
        for index, expected, count in ((104,"near",1),(18,"clear",2),(124,"miss",2)):
            sample=floor_image(index)
            game=phone.Game()
            with patch.object(game,"frame",return_value=sample) as capture:
                self.assertEqual(phone.assess(game)[0],expected)
            self.assertEqual(capture.call_count,count)

    def test_reused_clear_image_still_checks_fresh_ring_candidate(self):
        game=phone.Game()
        with patch.object(phone.time,"monotonic",return_value=10):
            game.remember_assessment_frame(floor_image(18))
            with patch.object(game,"frame",return_value=store_with_ring(1)) as capture:
                self.assertIn(phone.assess(game)[0],("ring","possible"))
        self.assertEqual(capture.call_count,1)

    def test_reusing_frame_does_not_skip_foreground_guard(self):
        device=RecordedGame(initial="play")
        device.floor=1
        with patch.object(phone,"rpc",device.rpc), redirect_stdout(io.StringIO()), \
             patch.object(phone.time,"monotonic",return_value=10):
            game=phone.Game()
            game.remember_assessment_frame(game.frame())
            device.foregrounds=["com.apple.mobilesafari"]
            self.assertEqual(phone.assess(game)[0],"near")
            with self.assertRaisesRegex(RuntimeError,"mobilesafari"):
                game.tap(phone.MOVES["left"])
        self.assertEqual(device.events,[])

    def test_recovered_input_requires_current_menu(self):
        for visible, expected_count in (("pause",1),("other",0)):
            device=RecordedGame()
            with patch.object(phone,"rpc",device.rpc), redirect_stdout(io.StringIO()):
                game=phone.Game()
                phone.opening_frame(game)
                device.screen=visible
                device.foregrounds=[None, phone.GAME]
                if visible=="pause":
                    game.tap(phone.RESUME,expected=phone.pause_menu)
                else:
                    with self.assertRaises(RuntimeError):
                        game.tap(phone.RESUME,expected=phone.pause_menu)
                self.assertEqual(len(device.events),expected_count)

    def test_save_error_and_lost_tap_ack_still_alert_once(self):
        device=RecordedGame(initial="play",portrait=False)
        def lost_ack(method,args=None):
            result=device.rpc(method,args)
            if method=="tap":
                raise TimeoutError("ack lost")
            return result
        with tempfile.TemporaryDirectory() as tmp, patch.object(phone,"rpc",lost_ack), \
             patch.object(phone,"ROOT",Path(tmp)), redirect_stdout(io.StringIO()):
            (Path(tmp)/"results").write_text("not a directory")
            game=phone.Game()
            board=game.frame()
            phone.pause_run(game,board,"ring",STEPS,1)
        self.assertEqual(device.events,["pause"])
        self.assertEqual(len(device.messages),1)
        self.assertIn("ポーズ確認済み",device.messages[0])

    def test_unread_shop_modes(self):
        blank=floor_image(104)
        scene=navigation.Scene({},set(),None)
        for hold in (True, False):
            device=RecordedGame()
            scripted=[("near",blank,scene)]*4+[("ring",blank,None)]
            with patch.object(phone,"assess",side_effect=scripted), \
                 patch.object(phone,"restart",return_value=None) as restart, \
                 patch.object(phone,"pause_run") as stop, redirect_stdout(io.StringIO()):
                phone.run(device,STEPS,0,hold)
            self.assertEqual(restart.call_count,0 if hold else 1)
            self.assertEqual(stop.call_args.args[2],"unread" if hold else "ring")
    def test_floor_numbers_and_unchanged_restart(self):
        im = floor_image(18)
        self.assertTrue(phone.on_floor(im))
        for x in (531,565):
            other = vision.small(im)
            other.paste((255,255,255),(x-2,269,x+3,271))
            self.assertFalse(phone.on_floor(other))
        class Unchanged:
            def frame(self):
                return im
        with self.assertRaises(RuntimeError):
            phone.wait_new_floor(Unchanged(),STEPS,im)

    def test_weak_and_late_candidates(self):
        class Game:
            def frame(self):
                return floor_image(124)
            def tap(self,*a,**kw):
                raise AssertionError("a candidate was reset")
        with patch.object(vision,"inspect",side_effect=[("miss",.4),("possible",.70)]):
            self.assertEqual(phone.assess(Game())[0],"possible")
        with patch.object(vision,"inspect",return_value=("ring",.9)):
            self.assertEqual(phone.restart(Game(),STEPS)[0],"ring")

    def test_config_validation_before_launch(self):
        with tempfile.TemporaryDirectory() as td:
            invalid=Path(td)/"menu.json"
            invalid.write_text("[]")
            with patch.object(phone,"CONFIG",invalid), patch.object(phone,"start_game") as launch, \
                 patch.object(phone.loopctrl_rpc,"STORE",str(invalid)),patch.object(sys,"argv",["phone.py","hold"]):
                with self.assertRaisesRegex(RuntimeError,"リスタート位置"):
                    phone.main()
                launch.assert_not_called()
            invalid.write_text(json.dumps(STEPS*2))
            with patch.object(phone,"CONFIG",invalid):
                self.assertEqual(phone.load_steps(),STEPS*2)

    def test_missing_confirmation_never_sends_second_tap(self):
        device=RecordedGame(initial="play",portrait=False)
        # This fixture game resets directly; simulate a saved profile that
        # also expects a second confirmation label which never appears.
        extra={"point":[.25,.25],"patch":STEPS[0]["patch"]}
        with patch.object(phone,"rpc",device.rpc):
            game=phone.Game()
            with self.assertRaisesRegex(RuntimeError,"登録したリスタート画面"):
                phone.restart(game,STEPS+[extra])
        self.assertEqual(device.events,["pause","restart"])

    def test_notification_failure_preserves_found_run(self):
        device=RecordedGame(initial="play",portrait=False)
        def send(method,args=None):
            if method=="open_url":
                raise OSError("shortcut unavailable")
            return device.rpc(method,args)
        with tempfile.TemporaryDirectory() as td, patch.object(phone,"ROOT",Path(td)), \
             patch.object(phone,"rpc",send), redirect_stdout(io.StringIO()):
            game=phone.Game()
            board=game.frame()
            with self.assertRaises(OSError):
                phone.pause_run(game,board,"possible",STEPS,1)
            self.assertEqual(device.events,["pause"])
            self.assertEqual(len(list((Path(td)/"results").glob("*-possible.png"))),1)

    def test_merchandise_and_gates(self):
        scene = navigation.scan(floor_image(124))
        items = {point for point,kind in scene.tiles.items() if kind=="item"}
        self.assertEqual(len(items),3)
        nav = navigation.Navigator()
        nav.update(scene)
        self.assertTrue(items.isdisjoint(nav.paths()))
        for dx,dy in navigation.DIRECTIONS.values():
            gate = (3*dx,3*dy)
            tiles={gate:"door",(3*dx-dy,3*dy+dx):"gold",(3*dx+dy,3*dy-dx):"gold"}
            tiles.update({(i*dx,i*dy):"floor" for i in (0,1,2,4)})
            nav=navigation.Navigator()
            scene=navigation.Scene(tiles,{p for p,k in tiles.items() if k=="gold"},None)
            self.assertEqual(navigation.DIRECTIONS[nav.choose(scene)],(dx,dy))
            self.assertEqual(nav.inside,(4*dx,4*dy))

    def test_taps_explicitly_skip_visual_settle(self):
        device=RecordedGame()
        params=[]
        def send(method,args=None):
            if method=="tap":params.append(args)
            return device.rpc(method,args)
        with patch.object(phone,"rpc",send), redirect_stdout(io.StringIO()):
            game=phone.Game()
            phone.begin(game,phone.opening_frame(game))
        self.assertEqual(len(params),1)
        self.assertIs(params[0].get("settle"),False)
        self.assertNotIn("manual",params[0])

    def test_straight_burst_excludes_door_dirt_goods_and_unknown(self):
        for obstacle,expected in (("floor",3),("door",1),("dirt",1),("gold",1),("item",1),(None,1)):
            nav=navigation.Navigator()
            tiles={(0,0):"floor",(1,0):"floor",(2,0):"floor",(3,0):"floor"}
            if obstacle is None:del tiles[2,0]
            else:tiles[2,0]=obstacle
            nav.tiles=tiles.copy();nav.target=(3,0)
            scene=navigation.Scene(tiles,set(),None)
            self.assertEqual(nav.burst(scene,"right"),expected,obstacle)
        nav.tiles={(i,0):"floor" for i in range(5)};nav.target=(4,0)
        current=navigation.Scene({(0,0):"floor",(1,0):"floor"},set(),None)
        self.assertEqual(nav.burst(current,"right"),1) # old map is not fresh sight
        nav.crossed=True
        self.assertEqual(nav.burst(navigation.Scene(nav.tiles,set(),None),"right"),1)

    def test_burst_measures_zero_partial_and_full_displacement(self):
        rng=random.Random(1241)
        board=Image.frombytes("RGB",(597,276),bytes(rng.randrange(256) for _ in range(597*276*3)))
        old=navigation.scan(board)
        for name,(dx,dy) in navigation.DIRECTIONS.items():
            for count in range(4):
                moved=phone.ImageChops.offset(board,-24*dx*count,-24*dy*count)
                new=navigation.scan(moved)
                nav=navigation.Navigator();nav.last=old;nav.pending=name;nav.pending_count=3
                nav.update(new)
                self.assertEqual(nav.pos,(dx*count,dy*count),(name,count))
        # With insufficient visual evidence, discard the old world map.
        nav=navigation.Navigator();nav.last=old;nav.pending="left";nav.pending_count=3
        nav.pos=(7,5);nav.tiles={(99,99):"gold"}
        nav.update(navigation.scan(Image.new("RGB",(597,276))))
        self.assertEqual(nav.pos,(0,0));self.assertNotIn((99,99),nav.tiles)

    def test_burst_stops_when_another_app_appears_between_taps(self):
        device=RecordedGame(initial="play");device.floor=1
        original=device.rpc
        def send(method,args=None):
            result=original(method,args)
            if method=="tap":device.foregrounds=["com.apple.mobilesafari"]
            return result
        with patch.object(phone,"rpc",send),redirect_stdout(io.StringIO()):
            game=phone.Game();game.capture_scale=2
            with self.assertRaisesRegex(RuntimeError,"mobilesafari"):
                phone.run(game,STEPS,1,True)
        self.assertEqual(device.events,["left"])

    def test_compact_quality_preserves_recorded_frames_and_candidates(self):
        for im in [floor_image(i) for i in (18,104,109,112,115,119,121,124)]+[store_with_ring(i) for i in range(3)]:
            outcomes=[]
            for quality in (60,87):
                data=io.BytesIO()
                im.resize((828,1792),vision.RESAMPLE.BICUBIC).save(data,"JPEG",quality=quality)
                restored=Image.open(io.BytesIO(data.getvalue())).convert("RGB").resize((896,414),vision.RESAMPLE.LANCZOS)
                outcomes.append(vision.inspect(restored)[0])
            self.assertEqual(*outcomes)

    def test_rejection_uses_high_quality_final_observation(self):
        device=RecordedGame(initial="play");qualities=[]
        def send(method,args=None):
            if method=="screenshot":qualities.append(args["quality"])
            return device.rpc(method,args)
        with patch.object(phone,"rpc",send):
            game=phone.Game();game.capture_scale=2
            self.assertEqual(phone.assess(game)[0],"clear")
        self.assertEqual(qualities,[.60,.87])

    def test_native_crypto_matches_independent_hmac_vectors_and_fallback(self):
        import fast_crypto
        if not fast_crypto.AVAILABLE:self.skipTest("native OpenSSL adapter unavailable; official fallback used")
        rng=random.Random(792)
        for keylen in (0,32,64,65,100):
            key=bytes(rng.randrange(256) for _ in range(keylen));nonce=bytes(range(16))
            for size in (0,1,31,32,33,65,4097):
                data=bytes(rng.randrange(256) for _ in range(size))
                stream=b"".join(hmac.new(key,nonce+i.to_bytes(4,"big"),hashlib.sha256).digest()
                                for i in range((size+31)//32))
                expected=bytes(a^b for a,b in zip(data,stream))
                self.assertEqual(fast_crypto.xor(key,nonce,data),expected)
                self.assertEqual(fast_crypto.xor(key,nonce,expected),data)
                with patch.object(fast_crypto,"AVAILABLE",False):
                    self.assertEqual(phone.loopctrl_rpc._keystream_xor(key,nonce,data),expected)

    def test_bad_response_mac_is_rejected_before_decryption(self):
        rpc=phone.loopctrl_rpc
        reply={"ct":base64.b64encode(b"tampered").decode(),"tag":"00"*32}
        record={"key":"ab"*32,"tok":"cd"*16}
        with patch.object(rpc,"_post",return_value=(200,reply)), \
             patch.object(rpc,"_keystream_xor",wraps=rpc._keystream_xor) as crypt:
            with self.assertRaisesRegex(SystemExit,"MAC mismatch"):
                rpc._call_with("127.0.0.1:8300",record,"screenshot",{},1,1)
        self.assertEqual(crypt.call_count,1) # request only; no unverified response decryption

    def test_edge_control_zones_are_independent_of_driver_coordinates(self):
        self.assertIsNone(edge_direction(.60,.085)) # R10's wrong UP position
        self.assertIsNone(edge_direction(.60,.90))  # R10's wrong DOWN position
        for name,point in phone.MOVES.items():
            self.assertEqual(edge_direction(*point),name)
        device=RecordedGame(initial="play");device.floor=1;device.position=2
        game=phone.Game();game.size=(414,896);game.stretched=True;game.can_tap=True
        with patch.object(phone,"rpc",device.rpc):game.tap(phone.MOVES["up"])
        self.assertEqual(device.events,["up"])
        self.assertEqual(device.taps,[(290,838)])

    def test_actual_game_over_blocks_movement_and_start(self):
        image=fixture("game-over.png")
        for quality in (.60,.87):
            stream=io.BytesIO()
            image.resize((828,1792),vision.RESAMPLE.BICUBIC).save(stream,"JPEG",quality=round(quality*100))
            game=phone.Game();game.last_quality=quality
            decoded=game.decode_frame(dict(point_width=414,point_height=896,data=base64.b64encode(stream.getvalue()).decode()))
            self.assertEqual(vision.inspect(decoded)[0],"dead")
            with patch.object(game,"tap",side_effect=AssertionError("input after game over")), \
                 patch.object(game,"frame",return_value=decoded):
                with self.assertRaisesRegex(RuntimeError,"ゲームオーバー"):phone.assess(game,True)
                with self.assertRaisesRegex(RuntimeError,"ゲームオーバー"):phone.begin(game,decoded)

    def test_reduced_decode_falls_back_before_rejecting_a_run(self):
        image=fixture("top-edge-gold.png");game=phone.Game();game.capture_scale=2
        def capture(method,args=None):
            if method=="device_info":return {"system":{"screen_locked":False,"foreground_app":phone.GAME}}
            self.assertEqual(method,"screenshot")
            stream=io.BytesIO()
            image.resize((828,1792),vision.RESAMPLE.BICUBIC).save(stream,"JPEG",quality=round(args["quality"]*100))
            return dict(point_width=414,point_height=896,data=base64.b64encode(stream.getvalue()).decode())
        # Establish orientation from the original full-detail capture first.
        with patch.object(phone,"rpc",capture):
            game.detail_frame()
            state,_,scene=phone.assess(game,True)
        self.assertEqual(state,"near")
        self.assertIn((-2,-5),scene.gold)

    def test_unconfirmed_motion_cannot_clear_the_retry_budget(self):
        scene=navigation.Scene({(0,0):"floor",(1,0):"floor",(2,0):"gold"},{(2,0)},None)
        nav=navigation.Navigator()
        with patch.object(navigation.lib,"observed_count",return_value=-1):
            self.assertEqual(nav.choose(scene),"right")
            for _ in range(4):nav.choose(scene)
        self.assertIsNone(nav.pending)
        self.assertEqual(nav.unconfirmed,4)
        self.assertTrue(nav.halt_reason)
        nav=navigation.Navigator();nav.last=scene
        with patch.object(navigation.lib,"observed_count",return_value=0):
            for _ in range(6):
                nav.pending="right";nav.update(scene)
        self.assertEqual(nav.no_progress,6)
        self.assertIsNone(nav.choose(scene))

    def test_failed_foreground_check_records_correct_stage(self):
        import diagnostics
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"stage.json"
            with patch.object(diagnostics,"_path",path),patch.object(diagnostics,"_current",None), \
                 patch.object(phone,"rpc",return_value={"system":{"screen_locked":False,"foreground_app":None}}), \
                 redirect_stdout(io.StringIO()):
                with self.assertRaises(RuntimeError):phone.Game().guard()
                self.assertEqual(diagnostics.read_record(path)["phase"],"前面アプリ確認")

    def test_actual_top_edge_gold_without_visible_shop_door(self):
        image=fixture("top-edge-gold.png")
        for quality in (60,87):
            stream=io.BytesIO()
            image.resize((828,1792),vision.RESAMPLE.BICUBIC).save(stream,"JPEG",quality=quality)
            payload=dict(point_width=414,point_height=896,data=base64.b64encode(stream.getvalue()).decode())
            game=phone.Game();decoded=game.decode_frame(payload)
            scene=phone.scene_for(decoded)
            self.assertIn((-2,-5),scene.gold)
            nav=navigation.Navigator();action=nav.choose(scene)
            self.assertEqual(action,"left")
            self.assertIsNone(nav.entrance) # The shop door is NOT visible in this image.
            # JPEG quality can change a distant dirt/stone classification;
            # the invariant is to approach the gold on a known route.
            self.assertLess(min(navigation.distance(nav.target,p) for p in scene.gold),
                            min(navigation.distance((0,0),p) for p in scene.gold))
            # Never burst through a JPEG-dependent dirt cell.
            count=nav.burst(scene,action)
            self.assertIn(count,(1,2))
            if count>1:
                self.assertTrue(all(scene.tiles.get((-i,0))=="floor" for i in range(1,count+1)))

    def test_grey_gap_can_be_an_iron_door_but_other_stone_is_blocked(self):
        # A grey door may have the same first-pass colour as stone. Structure
        # makes it a candidate, then actual opening/movement must be observed.
        for dx,dy in navigation.DIRECTIONS.values():
            gate=(2*dx,2*dy)
            tiles={gate:"stone",(2*dx-dy,2*dy+dx):"gold",(2*dx+dy,2*dy-dx):"gold"}
            tiles.update({(i*dx,i*dy):"floor" for i in (0,1,3)})
            self.assertNotIn(gate,navigation.entrances(tiles))
            self.assertIn(gate,navigation.entrances(tiles,allow_stone=True))
            tiles[gate]="door_candidate"
            nav=navigation.Navigator();scene=navigation.Scene(tiles,{p for p,k in tiles.items() if k=="gold"},None)
            action=nav.choose(scene)
            self.assertEqual(nav.entrance,gate)
            self.assertEqual(navigation.DIRECTIONS[action],(dx,dy))
            self.assertEqual(nav.burst(scene,action),1)
        nav=navigation.Navigator();nav.tiles={(0,0):"floor",(1,0):"stone"}
        self.assertNotIn((1,0),nav.paths())
        self.assertFalse(navigation.entrances(nav.tiles,allow_stone=True))

    def test_decoded_image_stays_usable_after_decoder_is_closed(self):
        device=RecordedGame(initial="play");device.floor=2;device.position=len(ROUTE)-1
        game=phone.Game()
        frame=game.decode_frame(device.screenshot(2,.87))
        before=frame.tobytes()
        self.assertIn(vision.inspect(frame)[0],("ring","possible"))
        one=vision.small(frame);two=vision.small(frame)
        self.assertIs(one,two)
        self.assertEqual(frame.tobytes(),before)
        # Ordinary mutable caller images do not reuse a cached downsample.
        mutable=floor_image(18)
        a=vision.small(mutable)
        mutable.paste((0,0,0),(0,0,mutable.width,mutable.height))
        self.assertNotEqual(a.tobytes(),vision.small(mutable).tobytes())

    def test_oversized_image_is_rejected_before_pixel_decode(self):
        image=Image.new("RGB",(4097,1));stream=io.BytesIO();image.save(stream,"PNG")
        payload=dict(point_width=414,point_height=896,data=base64.b64encode(stream.getvalue()).decode())
        with self.assertRaisesRegex(RuntimeError,"想定範囲外"):
            phone.Game().decode_frame(payload)

    def test_native_kernel_buffer_bounds(self):
        import ctypes
        from pixels import lib
        count=10*23
        guard=(ctypes.c_int*(count+2))();guard[0]=123456;guard[-1]=654321
        pointer=ctypes.cast(ctypes.byref(guard,ctypes.sizeof(ctypes.c_int)),ctypes.POINTER(ctypes.c_int))
        lib.scan_tiles(vision.small(fixture("top-edge-gold.png")).tobytes(),pointer)
        self.assertEqual((guard[0],guard[-1]),(123456,654321))
        self.assertEqual(lib.kernel_abi(),10)


class WorkerRegression(unittest.TestCase):
    def setUp(self):
        from runner_status import Worker
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.worker=Worker(self.root/"run.log",self.root/"stage.json",self.root/"status.json")
        self.addCleanup(self.worker.close)

    def script(self,body):
        script=self.root/"worker.py"
        script.write_text("import sys\nsys.path.insert(0,"+repr(str(phone.ROOT))+")\n"+body)
        return script

    def test_normal_exit_and_previous_log_preserved(self):
        script=self.script("print('completed')\n")
        self.worker.start(script,"test")
        self.worker.process.wait(timeout=5);self.worker.poll()
        self.assertEqual(self.worker.message,"")
        self.worker.start(script,"test")
        self.worker.process.wait(timeout=5);self.worker.poll()
        self.assertIn("completed",(self.root/"run-previous.log").read_text())

    def test_native_crash_exit_is_visible_with_last_phase(self):
        script=self.script("import diagnostics, os, signal\n"
                           "diagnostics.enable()\ndiagnostics.mark('native test')\n"
                           "os.kill(os.getpid(),signal.SIGSEGV)\n")
        self.worker.start(script,"test")
        self.worker.process.wait(timeout=5);self.worker.poll()
        self.assertIn("SIGSEGV",self.worker.message)
        self.assertIn("native test",self.worker.message)
        self.assertIn("Fatal Python error",(self.root/"run.log").read_text())

    def test_unhandled_python_error_and_last_phase(self):
        script=self.script("import diagnostics\ndiagnostics.enable()\n"
                           "diagnostics.mark('decode test')\nraise ValueError('repro')\n")
        self.worker.start(script,"test")
        self.worker.process.wait(timeout=5);self.worker.poll()
        self.assertIn("終了コード 1",self.worker.message)
        self.assertIn("decode test",self.worker.message)

    def test_hang_is_stopped_without_retrying_or_relaunching(self):
        import diagnostics
        script=self.script("import time\ntime.sleep(100)\n")
        self.worker.start(script,"test");process=self.worker.process
        diagnostics.write_record(self.worker.stage,dict(state="running",phase="stuck",since=time.monotonic()-60,limit=30))
        self.worker.poll();process.wait(timeout=5);self.worker.poll()
        self.assertIn("進まない",self.worker.message)
        self.assertIn("stuck",self.worker.message)
        self.assertIsNone(self.worker.process)

    def test_user_stop_is_distinguished_from_crash(self):
        script=self.script("import time\ntime.sleep(100)\n")
        self.worker.start(script,"test");process=self.worker.process
        self.worker.stop();process.wait(timeout=5);self.worker.poll()
        self.assertEqual(self.worker.message,"停止操作で終了しました。")

    def test_unclean_previous_session_is_reported_on_restart(self):
        import diagnostics
        from runner_status import Worker
        diagnostics.write_record(self.worker.receipt,dict(state="running"))
        diagnostics.write_record(self.worker.stage,dict(phase="previous decode"))
        restarted=Worker(self.worker.log,self.worker.stage,self.worker.receipt)
        self.assertIn("完了記録なし",restarted.message)
        self.assertIn("previous decode",restarted.message)


if __name__ == "__main__":
    unittest.main(verbosity=2)
