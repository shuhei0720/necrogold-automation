"""新しい実画像で零移動を確認できた床だけ、有限の入力先行量を試す。"""
from .shop_navigation import Scene,DIRECTIONS,_gates,_add

LEADS_NS=tuple(ms*1_000_000 for ms in (150,75,225,300,375,450,25))
OBSERVE_DELAY_NS=200_000_000  # 対象拍後の観測待ち。入力受付幅の値ではない。


def eligible(scene,direction):
    if (not isinstance(scene,Scene) or not isinstance(direction,str) or direction not in DIRECTIONS
            or scene.goods!='unknown' or not scene.gold or scene.tiles.get((0,0))!='floor'):
        return False
    target=DIRECTIONS[direction]
    if scene.tiles.get(target)!='floor' or target in _gates(scene.tiles):return False
    return not any(_add(point,delta) in scene.protected
                   for point in ((0,0),target) for delta in ((0,0),*DIRECTIONS.values()))
