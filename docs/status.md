# 最新状態

更新: 2026-11-25（日本時間）。TEST119実機11ZIP/7run/4campaign・170PNG/203記録を全照合。[TEST120計画](plans/test120-device-failures.md)・[検証](reviews/test120.md)。欠損なし。

成功3rootの正常陰性→実RS→child継承を確認して保持。通路3停止は新9/関連22件、開扉後のPARTIAL重複計算は新6/関連13件、左上候補は新6/関連39件で確認し、最終製品差分レビューP0/P1なし。発見した新routeの元P継承漏れも境界Red→Greenで修正した。

Ccf471e36/Nav6b4faeb6をfresh G1からseal/applyし、37native中Controller/Nav/RPCの3変更・34保持、API/native_v15/profile3同一を照合。Mac結合はpartial_begin_dispatchのnormal/lateだけを選び、最終fixtureの静的レビュー完了、実Mac/IPAはこれから。初回RS・--until-target・全商品観測・候補保持・元期限/UNKNOWN無再送を維持。

配布基準は[TEST119/build266](https://github.com/shuhei0720/necrogold-automation/releases/tag/test119-build266)、CODE617fc248/保存1d9a0a4。TEST120の実機到達率・改善・速度は未確認。
