"""Track the shop in world tile coordinates and walk through a gap in the gold perimeter."""
from dataclasses import dataclass
from heapq import heappop, heappush
import ctypes
from pixels import lib
from PIL import Image
from vision import DIRECTIONS, ROOT, small, correlation, signs

WALK = {"floor":1, "dirt":2.5, "door":1.5, "door_candidate":2.0}
ORIGIN = (0,0)


def add(p, d):
    return p[0]+d[0], p[1]+d[1]


def distance(p,q):
    return abs(p[0]-q[0])+abs(p[1]-q[1])


@dataclass
class Scene:
    tiles: dict
    gold: set
    signature: object


with Image.open(ROOT/"door.png") as original:
    door = original.convert("L").crop((3,3,original.width-3,original.height-3))
_door = door.tobytes()
_door_transposed = door.transpose(getattr(Image,"Transpose",Image).TRANSPOSE).tobytes()


def wooden_gate(frame,x,y):
    for ox,oy in ((0,0),(-2,0),(2,0),(0,-2),(0,2)):
        patch=frame.crop((x+ox-9,y+oy-9,x+ox+9,y+oy+9))
        values=[sum(rgb) for rgb in patch.getdata()]
        if max(correlation(values,_door),correlation(values,_door_transposed))>=.58:
            return True
    return False


def scan(image):
    frame=small(image)
    raw=frame.tobytes()
    kinds=(ctypes.c_int*(10*23))()
    lib.scan_tiles(raw,kinds)
    names={1:"floor",2:"dirt",3:"stone",4:"gold"}
    tiles={(i-11,j-5):names[kinds[j*23+i]] for j in range(10) for i in range(23)
           if kinds[j*23+i]}
    for x,y in entrances(tiles,allow_dirt=True,allow_stone=True):
        if wooden_gate(frame,298+24*x,138+24*y):
            tiles[x,y]="door"
        elif tiles[x,y] in ("stone","dirt"):
            # Iron doors can have the same grey median as an impassable stone
            # wall. Only a ONE-tile gap between two gold walls is a candidate.
            # Probe once, read the next frame, and measure opening/movement.
            # This never makes arbitrary stone walls walkable.
            tiles[x,y]="door_candidate"
    # Never route through an identified merchandise slot. The gold signs
    # anchor the same three slots used by the ring detector.
    anchor = signs(frame)
    if anchor:
        slots, sign_y = anchor
        for x in slots:
            tile = (round((x-298)/24), round((sign_y+32-138)/24))
            if tile != ORIGIN:
                tiles[tile] = "item"
    signature=ctypes.create_string_buffer(lib.gradient_bytes())
    lib.gradients(frame.tobytes(),signature)
    return Scene(tiles,{p for p,k in tiles.items() if k=="gold"},signature)


def observed_step(old,new,delta):
    result=lib.observed_move(old.signature,new.signature,*delta)
    return bool(result) if result>=0 else None


def entrances(tiles, allow_dirt=False, allow_stone=False):
    gold={p for p,k in tiles.items() if k=="gold"}
    # Door is an interruption in the wall: gold above AND below, or left AND right.
    result={}
    for x,y in gold:
        for ax,ay in ((1,0),(0,1)):
            p=x+ax,y+ay
            if (x+2*ax,y+2*ay) in gold and (tiles.get(p) in ("floor","door","door_candidate") or
                    (allow_dirt and tiles.get(p)=="dirt") or (allow_stone and tiles.get(p)=="stone")):
                normal=(ay,ax)
                sides=(add(p,normal),add(p,(-normal[0],-normal[1])))
                if any(tiles.get(s) in WALK for s in sides):
                    result[p]=sides
    return result


class Navigator:
    def __init__(self):
        self.pos=ORIGIN
        self.tiles={}
        self.last=None
        self.pending=None
        self.pending_count=1
        self.target=None
        self.fails={}
        self.visits={}
        self.entrance=None
        self.inside=None
        self.crossed=False
        self.last_motion=None
        self.no_progress=0
        self.unconfirmed=0
        self.halt_reason=""

    def update(self,scene):
        if self.pending:
            p,name=self.pos,self.pending
            count=lib.observed_count(self.last.signature,scene.signature,
                                     *DIRECTIONS[name],self.pending_count)
            self.last_motion=count
            if count > 0:
                self.no_progress=self.unconfirmed=0
                dx,dy=DIRECTIONS[name]
                self.pos=add(p,(dx*count,dy*count))
                self.fails.pop((p,name),None)
            elif count == 0:
                self.no_progress+=1
                self.unconfirmed=0
                self.fails[p,name]=self.fails.get((p,name),0)+1
            else:
                self.no_progress+=1
                self.unconfirmed+=1
                # Do not combine two incompatible maps if motion was ambiguous.
                self.pos=ORIGIN;self.tiles.clear();self.visits.clear();self.fails.clear()
                self.entrance=self.inside=None;self.crossed=False
            self.pending=None
            self.pending_count=1
        self.last=scene
        for p,kind in scene.tiles.items():
            world=add(self.pos,p)
            if self.tiles.get(world)=="item" or (p==ORIGIN and self.tiles.get(world) in ("door","door_candidate")):continue
            self.tiles[world]=kind
        self.visits[self.pos]=self.visits.get(self.pos,0)+1
        if self.inside==self.pos:self.crossed=True

    def paths(self, extras=(), full=False):
        allowed=set(extras)
        queue=[(0.,self.pos,())]
        found={self.pos:(0.,())}
        while queue:
            cost,p,first=heappop(queue)
            if cost>found[p][0]:continue
            for name,d in DIRECTIONS.items():
                q=add(p,d);kind=self.tiles.get(q)
                if kind not in WALK and not (kind is None and q in allowed):continue
                failures=self.fails.get((p,name),0)
                if failures>=2:continue
                step=WALK.get(kind,3.)+.20*min(self.visits.get(q,0),6)+.6*failures
                total=cost+step
                if q not in found or total<found[q][0]:
                    action=first+(name,)
                    found[q]=(total,action);heappush(queue,(total,q,action))
        return found if full else {p:(c,path[0] if path else "") for p,(c,path) in found.items()}

    def choose(self,scene):
        self.update(scene)
        self.target=None
        if self.unconfirmed>=4 or self.no_progress>=6:
            self.halt_reason="移動の進行を確認できないため探索を終了します。"
            self.pending=None
            return None
        gold={p for p,k in self.tiles.items() if k=="gold"}
        if not gold:return None
        gates=entrances(self.tiles)
        paths=self.paths()
        if self.entrance not in gates and not self.crossed:
            self.entrance = self.inside = None
            candidates=[p for p in gates if p in paths]
            if candidates:
                self.entrance=min(candidates,key=lambda p:paths[p][0])
                sides=gates[self.entrance]
                # Enter from the reachable near side; the opposite cell leads inside.
                near=min(sides,key=lambda p:(p not in paths, distance(self.pos,p), -self.visits.get(p,0),
                                             -sum(distance(p,g) for g in gold)))
                self.inside=next(s for s in sides if s!=near)
        action=None
        if self.entrance and not self.crossed:
            goal=self.entrance if self.pos!=self.entrance else self.inside
            route=self.paths((goal,)).get(goal)
            if route:action=route[1];self.target=goal
        if not action:
            # Only seen a piece of gold, or passed the door but not yet the price row.
            # Stand at a new walkable vantage beside the walls; allow basic dirt digs.
            options=[]
            for p,(cost,first) in paths.items():
                if not first:continue
                if self.crossed and self.inside and self.entrance:
                    d=(self.inside[0]-self.entrance[0],self.inside[1]-self.entrance[1])
                    if (p[0]-self.entrance[0])*d[0]+(p[1]-self.entrance[1])*d[1]<1:continue
                gap=min(distance(p,g) for g in gold)
                rank=2.7*gap+cost+3.5*self.visits.get(p,0)
                options.append((rank,first,p))
            if options:
                _,action,self.target=min(options)
        self.pending=action
        return action

    def burst(self,scene,action):
        """At most three straight taps on floors seen in THIS image.

        Stop before a door, dirt, merchandise, a turn, or the inside of a shop.
        Actual displacement is measured on the next image; a partial/blocked
        burst is never assumed successful. Each tap still has a live guard.
        """
        self.pending_count=1
        if not action or self.target is None or self.crossed or self.pos==self.entrance:
            return 1
        route=self.paths((self.target,),full=True).get(self.target)
        if not route:
            return 1
        point=self.pos
        count=0
        for name in route[1][:3]:
            if name!=action:break
            point=add(point,DIRECTIONS[name])
            local=(point[0]-self.pos[0],point[1]-self.pos[1])
            if scene.tiles.get(local)!="floor" or point in (self.entrance,self.inside):break
            # Re-read before getting close to any merchandise slot.
            if any(kind=="item" and distance(local,p)<=1 for p,kind in scene.tiles.items()):break
            count+=1
        self.pending_count=max(1,count)
        return self.pending_count
