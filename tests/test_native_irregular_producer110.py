"""TEST110 positive UI/actor certificates from immutable RGBA.

Procedural fixtures test the closed geometry, not unknown accuracy or device
speed. The R12 image is known calibration. Before the new API, the compatibility
bridge runs the actual old Scene decoder and provides its conservative NONE;
that semantic Red is not a missing-symbol or compilation failure.
"""
import ctypes as C
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from PIL import Image, ImageDraw
from necroprobe import gold_scan
from tests import test_native_perception as perception

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT/'patches/loopctrl/ngg2'
HEART = ("..####....####.", ".######.#######", "###############",
         "###############", "###############", "###############",
         ".##############", "..############.", "...##########..",
         "....########...", ".....######....", "......####.....",
         ".......##......")


class Irregular(C.Structure):
    _fields_ = [('abi_version', C.c_uint32), ('struct_size', C.c_uint32)] + [
        (n, C.c_int32) for n in ('kind', 'glyph_intersection', 'glyph_union',
            'hud_mask', 'empty_hearts', 'matches', 'left', 'top', 'width', 'height')] + [
        (n, C.c_int32*3) for n in ('heart_inter', 'heart_union', 'heart_red',
            'heart_dark', 'heart_bright')] + [('enemy_mask', C.c_uint32)] + [
        (n, C.c_int32*4) for n in ('enemy_matches', 'enemy_inter', 'enemy_union',
            'enemy_left', 'enemy_top', 'enemy_body_luma', 'enemy_body_saturation',
            'enemy_red_outside', 'enemy_heart_count', 'enemy_width', 'enemy_height')]


DECLARATION = r'''
typedef struct {
 uint32_t abi_version,struct_size;
 int32_t kind,glyph_intersection,glyph_union,hud_mask;
 int32_t empty_hearts,matches,left,top,width,height;
 int32_t heart_inter[3],heart_union[3],heart_red[3],heart_dark[3],heart_bright[3];
 uint32_t enemy_mask;
 int32_t enemy_matches[4],enemy_inter[4],enemy_union[4];
 int32_t enemy_left[4],enemy_top[4],enemy_body_luma[4];
 int32_t enemy_body_saturation[4],enemy_red_outside[4];
 int32_t enemy_heart_count[4],enemy_width[4],enemy_height[4];
} NG2IrregularObservation;
'''


def depleted_heart():
    # Independent existing source: not the new production constant/bank.
    path = ROOT/'legacy/r12/testdata/game-over.png'
    if hashlib.sha256(path.read_bytes()).hexdigest() != (
            'a711fa2f1935fd3c161058f82e0073c2c0ec6fe32f1e4ad75be6efa33b35dede'):
        raise AssertionError('immutable known R12 death calibration changed')
    image = Image.open(path).resize((896, 414), Image.Resampling.NEAREST).convert('RGB')
    mask = Image.new('L', (25, 25))
    pixels = image.load()
    mask.putdata([255 if r >= 40 and r >= g+25 and r >= b+25 else 0
                  for y in range(6, 31) for x in range(683, 708)
                  for r, g, b in (pixels[x, y],)])
    return mask


def death_image():
    image = perception.synthetic_floor()
    perception.paint_template(image, 'death')
    for center in (695, 724, 753):
        image.paste((90, 0, 0), (center-12, 6), depleted_heart())
    return image


def actor_image(direction=2, count=1, lefts=None, tops=None, body=(40, 140, 40)):
    image = perception.synthetic_floor()
    dx, dy = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}[direction]
    cx, cy = 448+36*dx, 207+36*dy
    ImageDraw.Draw(image).rectangle((cx-14, cy-9, cx+14, cy+14), fill=body)
    lefts = lefts if lefts is not None else [cx-7-9*(count-1)+18*k for k in range(count)]
    tops = tops if tops is not None else [cy-31]*len(lefts)
    draw = ImageDraw.Draw(image)
    for left, top in zip(lefts, tops):
        for y, row in enumerate(HEART):
            for x, value in enumerate(row):
                if value == '#':
                    draw.point((left+x, top+y), fill=(200, 0, 0))
    return image


def restart_image(left=357, top=256, color=(200, 200, 200)):
    image = Image.new('RGB', (896, 414))
    mask = gold_scan._TEMPLATES['restart'][3]
    image.paste(color, (left, top), mask)
    return image


class NativeIrregularProducer110Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        core = Path(os.environ.get('NECRO_TEST110_IRREGULAR_CORE', str(CORE)))
        cls.directory = tempfile.TemporaryDirectory(prefix='irregular-producer110-')
        cls.addClassCleanup(cls.directory.cleanup)
        directory = Path(cls.directory.name)
        source = directory/'bridge.c'
        source.write_text('#include "'+str(core/'NG2Core.h')+'"\n'
            '#include <string.h>\n#ifndef NG2_IRREGULAR_ABI_VERSION\n'+DECLARATION+
            '#endif\n'+r'''
/* HOST TEST ONLY. The old branch invokes the old real decoder, not a
 * missing symbol. It cannot manufacture a new positive UI certificate. */
int ng2_test_irregular110(const uint8_t *rgba,size_t length,size_t stride,
                         uint32_t flags,NG2IrregularObservation *out){
#ifdef NG2_IRREGULAR_ABI_VERSION
 return ng2_analyze_irregular_rgba(rgba,length,stride,flags,out);
#else
 NG2Scene scene;int result=ng2_analyze_rgba(rgba,length,stride,&scene);
 (void)flags;memset(out,0,sizeof(*out));out->abi_version=1;out->struct_size=sizeof(*out);
 return result;
#endif
}
int ng2_test_irregular110_native(void){
#ifdef NG2_IRREGULAR_ABI_VERSION
 return 1;
#else
 return 0;
#endif
}
''')
        output = directory/'perception.so'
        subprocess.run(['cc', '-std=c99', '-O2', '-fno-fast-math', '-ffp-contract=off',
            '-Wall', '-Wextra', '-Werror', '-pedantic', '-fPIC', '-shared',
            str(core/'NG2Perception.c'), str(source), '-lm', '-o', str(output)], check=True)
        cls.lib = C.CDLL(str(output))
        cls.lib.ng2_test_irregular110.argtypes = [C.c_void_p, C.c_size_t, C.c_size_t,
            C.c_uint32, C.POINTER(Irregular)]
        cls.lib.ng2_test_irregular110.restype = C.c_int
        cls.lib.ng2_analyze_rgba.argtypes = [C.c_void_p, C.c_size_t, C.c_size_t,
            C.POINTER(perception.NativeScene)]
        cls.lib.ng2_analyze_rgba.restype = C.c_int

    def analyze(self, image, flags=0, raw=None, stride=3584):
        raw = image.convert('RGBA').tobytes() if raw is None else raw
        value = Irregular()
        result = self.lib.ng2_test_irregular110(raw, len(raw), stride, flags, C.byref(value))
        self.assertEqual(0, result)
        self.assertEqual((1, 288), (value.abi_version, value.struct_size))
        return value

    def test_full_death_prompt_and_three_depleted_shapes_are_positive(self):
        value = self.analyze(death_image())
        self.assertEqual((1, 15, 3, 1),
                         (value.kind, value.hud_mask, value.empty_hearts, value.matches),
                         'whole observed death prompt plus three depleted HUD hearts is a positive certificate')
        self.assertEqual((312, 312, 270, 24),
                         (value.left, value.top, value.width, value.height))
        source = Image.open(ROOT/'legacy/r12/testdata/game-over.png').resize(
            (896, 414), Image.Resampling.NEAREST)
        known = self.analyze(source)
        self.assertEqual((1, 476, 727, 3),
                         (known.kind, known.glyph_intersection, known.glyph_union, known.empty_hearts))

    def test_death_requires_full_text_positive_empty_shapes_and_independent_hud(self):
        for mode in ('no_text', 'half_text', 'colored_text', 'black_health',
                     'filled_health', 'red_rectangles', 'missing_footer', 'pause_menu'):
            with self.subTest(mode=mode):
                image = death_image()
                if mode in ('no_text', 'half_text', 'colored_text'):
                    image.paste(0, gold_scan._TEMPLATES['death'][0])
                    if mode == 'colored_text':
                        perception.paint_template(image, 'death', (255, 60, 60))
                    elif mode == 'half_text':
                        perception.paint_template(image, 'death')
                        image.paste(0, (447, 312, 582, 336))
                elif mode in ('black_health', 'filled_health', 'red_rectangles'):
                    for center in (695, 724, 753):
                        image.paste(0, (center-12, 6, center+13, 31))
                        if mode == 'filled_health':
                            image.paste((200, 0, 0), (center-12, 6), depleted_heart())
                        elif mode == 'red_rectangles':
                            image.paste((90, 0, 0), (center-12, 6, center+13, 31))
                elif mode == 'missing_footer':
                    image.paste(0, gold_scan._TEMPLATES['footer'][0])
                elif mode == 'pause_menu':
                    perception.paint_template(image, 'continue')
                self.assertNotEqual(1, self.analyze(image).kind)

    def test_one_two_three_whole_actor_markers_qualify_only_the_observed_direction(self):
        for direction in range(1, 5):
            for count in (1, 2, 3):
                with self.subTest(direction=direction, count=count):
                    value = self.analyze(actor_image(direction, count))
                    self.assertEqual((3, 1 << (direction-1)), (value.kind, value.enemy_mask))
                    self.assertEqual(1, value.enemy_matches[direction-1])
                    self.assertEqual(count, value.enemy_heart_count[direction-1])
                    self.assertEqual((15+18*(count-1), 13),
                        (value.enemy_width[direction-1], value.enemy_height[direction-1]))
                    self.assertEqual(137*count, value.enemy_inter[direction-1])
                    self.assertEqual(137*count, value.enemy_union[direction-1])

    def test_maximality_halo_body_and_multiple_bars_fail_closed(self):
        cases = {
            'right_clipped_four': actor_image(lefts=[454, 472, 490, 508]),
            'left_clipped_four': actor_image(lefts=[445, 463, 481, 499]),
            'top_staircase': actor_image(lefts=[459, 477, 495], tops=[175, 176, 177]),
            'absent_body': actor_image(body=(0, 0, 0)),
            'achromatic_body': actor_image(body=(140, 140, 140)),
            'multiple_bars': actor_image(lefts=[477, 477], tops=[169, 183]),
        }
        partial = actor_image()
        partial.paste(0, (477, 176, 485, 189))
        cases['partial'] = partial
        flooded = actor_image()
        ImageDraw.Draw(flooded).rectangle((477, 176, 491, 188), fill=(200, 0, 0))
        cases['rectangle'] = flooded
        for name, image in cases.items():
            with self.subTest(case=name):
                value = self.analyze(image)
                self.assertEqual(0, value.enemy_mask)
                self.assertNotEqual(3, value.kind)
                if name == 'multiple_bars':
                    self.assertEqual(2, value.enemy_matches[1])

    def test_restart_scan_is_opt_in_unique_full_word_and_uses_its_actual_box(self):
        for left, top in ((357, 256), (160, 60), (555, 332), (230, 110)):
            with self.subTest(origin=(left, top)):
                image = restart_image(left, top)
                self.assertEqual(0, self.analyze(image).kind)
                value = self.analyze(image, 1)
                self.assertEqual((2, 1, 223, 223),
                    (value.kind, value.matches, value.glyph_intersection, value.glyph_union))
                self.assertEqual((left, top, 181, 28),
                    (value.left, value.top, value.width, value.height))
        image = restart_image(180, 80)
        second = restart_image(450, 300)
        image.paste(second.crop((450, 300, 631, 328)), (450, 300))
        value = self.analyze(image, 1)
        self.assertEqual((0, 2), (value.kind, value.matches))

    def test_restart_rejects_partial_colored_flooded_outside_and_present_death(self):
        cases = [restart_image(159, 60), restart_image(555, 333),
                 restart_image(color=(255, 60, 60))]
        partial = restart_image()
        partial.paste(0, (447, 256, 538, 284))
        cases.append(partial)
        white = Image.new('RGB', (896, 414))
        ImageDraw.Draw(white).rectangle((357, 256, 537, 283), fill=(255,)*3)
        cases.append(white)
        for image in cases:
            self.assertEqual(0, self.analyze(image, 1).kind)
        death = death_image()
        mask = gold_scan._TEMPLATES['restart'][3]
        death.paste((200,)*3, (200, 100), mask)
        self.assertEqual(1, self.analyze(death, 1).kind, 'death takes priority over a restart label')

    def test_visible_death_text_vetoes_restart_without_a_complete_death_certificate(self):
        image = perception.synthetic_floor()
        image.paste((255, 160, 0), gold_scan._TEMPLATES['death'][0])
        perception.paint_template(image, 'death')
        image.paste((200,)*3, (200, 100), gold_scan._TEMPLATES['restart'][3])
        raw = image.convert('RGBA').tobytes()
        old = perception.NativeScene()
        self.assertEqual(0, self.lib.ng2_analyze_rgba(raw, len(raw), 3584, C.byref(old)))
        self.assertEqual(2, old.state, 'colored background defeats the old non-neutral death veto')
        value = self.analyze(image, 1)
        self.assertEqual(0, value.empty_hearts)
        self.assertEqual(0, value.kind,
            'observed full neutral death text forbids menu input even without three empty HUD hearts')
        self.assertEqual((1, 522, 522, 312, 312, 270, 24),
            (value.matches, value.glyph_intersection, value.glyph_union,
             value.left, value.top, value.width, value.height),
            'prompt-only support remains available to every downstream UI qualification veto')

    def test_old_death_veto_support_survives_without_new_ninety_percent_coverage(self):
        image = death_image()
        left, top = gold_scan._TEMPLATES['death'][0][:2]
        mask = gold_scan._TEMPLATES['death'][3]
        points = [(left+x, top+y) for y in range(mask.height) for x in range(mask.width)
                  if mask.getpixel((x, y))]
        draw = ImageDraw.Draw(image)
        for point in points[:100]:
            draw.point(point, fill=0)
        image.paste((200,)*3, (200, 100), gold_scan._TEMPLATES['restart'][3])
        raw = image.convert('RGBA').tobytes()
        old = perception.NativeScene()
        self.assertEqual(0, self.lib.ng2_analyze_rgba(raw, len(raw), 3584, C.byref(old)))
        self.assertEqual(0, old.state, 'the retained old full-box death veto is positive')
        value = self.analyze(image, 1)
        self.assertEqual(0, value.kind, 'old veto evidence is never DEATH_CONTINUE authority')
        self.assertEqual((2, 422, 522, 312, 312, 270, 24),
            (value.matches, value.glyph_intersection, value.glyph_union,
             value.left, value.top, value.width, value.height),
            'retain the old non-neutral mask support for every downstream UI veto')

    def test_a_complete_half_of_a_fourth_marker_is_ambiguous_instead_of_a_three_bar(self):
        for side in ('left', 'right', 'partial_with_noise'):
            with self.subTest(side=side):
                if side == 'left':
                    image = actor_image(lefts=[445, 463, 481, 499])
                    image.paste(0, (445, 176, 452, 189))
                elif side == 'right':
                    image = actor_image(lefts=[454, 472, 490, 508])
                    image.paste(0, (516, 176, 523, 189))
                else:
                    image = actor_image(lefts=[445, 463, 481, 499])
                    image.paste(0, (445, 176, 460, 189))
                    reference = {(x, y) for y, row in enumerate(HEART)
                                 for x, pixel in enumerate(row) if pixel == '#'}
                    removed = {(x, y) for y in (3, 4) for x in range(4, 10)}
                    observed = reference-removed
                    noise = [(x, y) for y in range(13) for x in range(15)
                             if (x, y) not in reference and any(
                                 (x+dx, y+dy) in observed
                                 for dx in (-1, 0, 1) for dy in (-1, 0, 1))][:13]
                    observed.update(noise)
                    self.assertEqual((138, 125), (len(observed), len(observed & reference)))
                    draw = ImageDraw.Draw(image)
                    for x, y in observed:
                        draw.point((445+x, 176+y), fill=(200, 0, 0))
                value = self.analyze(image)
                self.assertEqual(0, value.enemy_mask,
                    'do not discard the partial fourth component and certify the remaining three')
                self.assertEqual(2, value.enemy_matches[1])
                self.assertNotEqual(3, value.kind)

    def test_invalid_rasters_and_flags_clear_all_permission_fields(self):
        raw = death_image().convert('RGBA').tobytes()
        cases = [(raw[:-1], 3584, 0), (raw[:-1]+b'\0', 3584, 0),
                 (raw, 3583, 0), (raw, 7681, 0), (raw, 3584, 2)]
        for data, stride, flags in cases:
            with self.subTest(length=len(data), stride=stride, flags=flags):
                value = Irregular()
                C.memset(C.byref(value), 255, C.sizeof(value))
                self.assertEqual(-1, self.lib.ng2_test_irregular110(
                    data, len(data), stride, flags, C.byref(value)))
                self.assertEqual((1, 288), (value.abi_version, value.struct_size))
                self.assertEqual(bytes(280), bytes(value)[8:])

    def test_companion_is_real_native_and_does_not_mutate_pixels_or_scene(self):
        self.assertEqual(1, self.lib.ng2_test_irregular110_native())
        for image in (death_image(), actor_image(count=3), restart_image()):
            raw = image.convert('RGBA').tobytes()
            buffer = C.create_string_buffer(raw, len(raw))
            before = perception.NativeScene()
            after = perception.NativeScene()
            self.assertEqual(0, self.lib.ng2_analyze_rgba(buffer, len(raw), 3584, C.byref(before)))
            value = Irregular()
            self.assertEqual(0, self.lib.ng2_test_irregular110(buffer, len(raw), 3584, 1, C.byref(value)))
            self.assertEqual(raw, buffer.raw)
            self.assertEqual(0, self.lib.ng2_analyze_rgba(buffer, len(raw), 3584, C.byref(after)))
            self.assertEqual(bytes(before), bytes(after))
            padded = b''.join(raw[y*3584:(y+1)*3584]+bytes((7, 9, 11, 0))*7 for y in range(414))
            self.assertEqual(bytes(value), bytes(self.analyze(image, 1, padded, 3612)))


if __name__ == '__main__':
    unittest.main()
