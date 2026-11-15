# TEST106: 左の観測口と暗い横通路の見逃し

2026-11-15（日本時間）。[要件SHOP-03](../requirements/necrogold.md)・[局所通路契約](../contracts/passage-approach.md)・FR-104-OBSERVED-MOUTH/FR-100-LOWER-FRINGEを修正前に照合した。

TEST105実2の原62は左口(-3,-2)だけFLOOR、外側と内側はUNKNOWN。両flank/外側屋根と長い左境界が見えているが、104の観測口は上方向だけで、旧genericは内側床経路、旧cornerは外側FLOORを要求するためmask0となった。左の正常候補へbit5を追加する。口のFLOOR・外側/内側UNKNOWNに加え、外側屋根の連続3壁と左のy=-1..2の連続4壁を必要にする。単純な104の転置ではなく追加の正の壁支持を使い、旧転置拒否assertを維持する。

実3の原72は左の口(-3,1)と外側が暗い。上側の左境界終端、下側の角、別の外側柱が観測されているが、100の外側FLOOR/口壁条件には入らない。これら3組の独立した正の壁支持と暗いgapを要求する有限の左shadow仮説bit8を追加する。世界外の床や金壁を生成しない。

両方とも正常CLEAR/商品UNKNOWN/全ITEM・保護0、中央の床、(-2,0)と既観測vantage(-2,-1)又は(-2,1)、元path searchで3歩の床経路だけを使う。public chooserの原地形だけの投影で、LEFT→LEFT→UP又はDOWNの3歩後はHOLDとなることを確認した。口/外側のUNKNOWNへ入力しない。これは未来の実フレームや実MOVEDの再現ではない。

Navigationだけの局所変更と新試験。意味Redを全実行source/fixtureの凍結前像で確認してから実装し、新guard/旧104/097/100の直接回帰を選ぶ。各正の壁/床/暗部、保護・ABI・商品・金状態、方向/平行移動、固定口と観測経路の境界を確認する。Controller/Perception/Runtime/公開ABI/元予算/UNKNOWN無再送は変更しない。次実機の候補発見・商店到達・全商品確認は未確認。
