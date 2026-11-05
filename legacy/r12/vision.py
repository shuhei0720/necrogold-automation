"""Vision for the 597 x 276 calibrated grid using Pillow and baseline i386 kernels."""
import ctypes
from dataclasses import dataclass
from math import sqrt
from pathlib import Path
from PIL import Image, ImageChops
from pixels import lib

RESAMPLE = getattr(Image, "Resampling", Image)
ROOT = Path(__file__).resolve().parent
DIRECTIONS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


def small(image):
    if image.size==(597,276) and image.mode=="RGB":return image
    saved = getattr(image,"_necro_small",None)
    if saved is not None:
        return saved
    rgb = image if image.mode=="RGB" else image.convert("RGB")
    frame = rgb.resize((597, 276), RESAMPLE.BILINEAR)
    if rgb is not image:rgb.close()
    if getattr(image,"_necro_cache_frame",False):
        image._necro_small = frame
        frame._necro_cache_frame = True
    return frame


def reference_mask(name, threshold):
    with Image.open(ROOT / (name + ".png")) as image:
        return tuple(value > threshold for value in image.convert("L").getdata())


HUD = (("pause", (285, 4, 311, 27), 55), ("floor", (494, 263, 582, 276), 90))
MASKS = {name: reference_mask(name, cutoff) for name, _, cutoff in HUD}
MASKS["timer"] = reference_mask("timer", 120)


def mask_overlap(frame, box, threshold, reference):
    observed = (sum(pixel) > 3*threshold for pixel in frame.crop(box).getdata())
    both = either = 0
    for a, b in zip(observed, reference):
        both += a and b
        either += a or b
    return both / max(either, 1)


def hud_matches(frame):
    if lib.hud_banner(frame.tobytes()):
        return False
    if not all(mask_overlap(frame, box, cut, MASKS[name]) >= .62 for name,box,cut in HUD):
        return False
    # Most of the footer is fixed Japanese text. Match the two narrow "1"
    # glyphs separately so a different zone or floor cannot pass on text alone.
    for x in (531,565):
        glyph = frame.crop((x-3,267,x+5,276)).convert("L")
        peak = glyph.getextrema()[1]
        if peak < 52:
            return False
        cutoff = min(90, peak * .62)
        digit = glyph.point(lambda v: 255 if v>cutoff else 0).getbbox()
        if digit is None:
            return False
        left,top,right,bottom = digit
        if right-left>3 or bottom-top<4 or not 2<=left<=4:
            return False
    return True


def has_gold(frame):
    return bool(lib.has_gold(frame.tobytes()))


def prices(frame, xs, sign_y):
    start = sign_y + 46
    if start < 0 or start+12 >= 270 or xs[0] < 17 or xs[-1]+17 >= 597:
        return False
    if xs[-1] > 483 and start > 212:
        return False
    rows = []
    for x in xs:
        crop = frame.crop((x-7,start,x+8,start+13))
        # Downsampling a thin white price through a portrait JPEG can drop
        # it below 163. Require near-neutral ink across all three price slots.
        flat = [min(p) > 140 and max(p)-min(p) < 40 for p in crop.getdata()]
        rows.append([sum(flat[t*15:(t+6)*15]) for t in range(8)])
    return any(min(counts) >= 10 for counts in zip(*rows))


def signs(frame, raw=None):
    if hasattr(frame,"_necro_signs"):return frame._necro_signs
    answer=_signs(frame,raw)
    if getattr(frame,"_necro_cache_frame",False):frame._necro_signs=answer
    return answer


def _signs(frame, raw=None):
    result = (ctypes.c_int * 3)()
    count = lib.locate_signs(raw if raw is not None else frame.tobytes(), result)
    x,y,gap = result
    if count == 2:
        return (x,x+gap//2,x+gap),y
    if count == 1:
        for left in (x,x-48):
            xs=(left,left+24,left+48)
            if prices(frame,xs,y):
                return xs,y
    return None


with Image.open(ROOT / "ring.png") as source:
    _ring = source.convert("RGBA").crop((0,0,22,19))
TEMPLATES = []
for width in (21,22,23):
    height = round(19*width/22)
    TEMPLATES.append((width,height,_ring.resize((width,height),RESAMPLE.BILINEAR).tobytes()))


def ring_score(frame, xs, sign_y, raw=None):
    raw = frame.tobytes() if raw is None else raw
    return max(lib.ring_match(raw, sprite, w,h,x,sign_y)
               for w,h,sprite in TEMPLATES for x in xs)


with Image.open(ROOT/"game-over-label.png") as source:
    DEATH_MASK=tuple(v>0 for v in source.getdata())


def game_over(image):
    return mask_overlap(small(image),(210,209,385,222),140,DEATH_MASK)>=.60


def inspect(image):
    frame=small(image)
    if game_over(frame):return "dead",1.
    if not hud_matches(frame):
        return "unknown",0.
    raw=frame.tobytes()
    anchor=signs(frame,raw)
    if anchor:
        xs,y=anchor
        score=ring_score(frame,xs,y,raw)
        if score>=.76:return "ring",score
        if score>=.64:return "possible",score
        return ("miss" if prices(frame,xs,y) else "near"),score
    return ("near" if lib.has_gold(raw) else "clear"),0.


def correlation(a,b,min_std=0):
    n=len(a)
    if not n or n!=len(b):return 0.
    sa,sb=sum(a),sum(b)
    va=sum(v*v for v in a)-sa*sa/n
    vb=sum(v*v for v in b)-sb*sb/n
    if min(va,vb) < n*min_std*min_std or min(va,vb)<=0:return 0.
    dot=sum(x*y for x,y in zip(a,b))-sa*sb/n
    return dot/max(1.,sqrt(va*vb))


@dataclass
class MapView:
    player: tuple
    floor: set
    wall: set
    goods: set
    doors: set


def blue_centres(mask):
    # bytes.find skips blank areas in native code.
    raw=mask.tobytes()
    if raw.count(b'\xff')>9000:return
    remaining=set()
    pos=raw.find(b'\xff')
    while pos>=0:
        remaining.add((pos%mask.width,pos//mask.width))
        pos=raw.find(b'\xff',pos+1)
    while remaining:
        group=[remaining.pop()]
        for x,y in group:
            for point in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if point in remaining:
                    remaining.remove(point)
                    group.append(point)
        if not 12<=len(group)<=64:continue
        xs,ys=zip(*group)
        w,h=max(xs)-min(xs)+1,max(ys)-min(ys)+1
        if 4<=w<=8 and 4<=h<=8 and len(group)>=.65*w*h:
            yield (max(xs)+min(xs))//2,(max(ys)+min(ys))//2


def minimap(image):
    x0,y0=1320,518
    # Resample only the map region, rather than enlarging the entire screenshot.
    image=image if image.mode=="RGB" else image.convert("RGB")
    region=(x0*image.width/1792, y0*image.height/828,
            1730*image.width/1792, 780*image.height/828)
    crop=image.resize((410,262),RESAMPLE.BILINEAR,box=region)
    r,g,b=crop.split()
    difference=ImageChops.subtract(b,ImageChops.lighter(r,g))
    blue=ImageChops.darker(b.point(lambda v:255 if v>100 else 0),
                          difference.point(lambda v:255 if v>85 else 0))
    candidates=[]
    pixels=crop.load()
    for px,py in blue_centres(blue):
        floor,walls,goods,doors=set(),set(),set(),set()
        for j in range(-22,23):
            yy=py+j*6
            if not 1<=yy<crop.height-1:continue
            for i in range(-31,32):
                xx=px+i*6
                if not 1<=xx<crop.width-1:continue
                rv,gv,bv=pixels[xx,yy]
                p=(i,j)
                if rv>90 and gv>67 and bv<37 and 1.18*gv<rv<1.49*gv:walls.add(p)
                elif rv>130 and gv>100 and bv<43 and rv<=1.2*gv:goods.add(p)
                elif 94<gv<221 and abs(rv-gv)<32 and 0<=gv-bv<45:floor.add(p)
                elif 86<rv<180 and 52<gv<138 and 22<bv<88 and rv>1.19*gv:doors.add(p)
        walls={(x,y) for x,y in walls if any(
            (x+dx,y+dy) in walls and ((x+2*dx,y+2*dy) in walls or (x-dx,y-dy) in walls)
            for dx,dy in DIRECTIONS.values())}
        if len(floor)>=4 and any(abs(x)+abs(y)<=2 for x,y in floor):
            candidates.append(MapView((px+x0,py+y0),floor,walls,goods,doors))
    return max(candidates,key=lambda view:len(view.floor),default=None)
