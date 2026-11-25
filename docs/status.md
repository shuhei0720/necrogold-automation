# 最新状態

更新: 2026-11-25（日本時間）。TEST118実機9ZIP（4campaign/5run・132PNG/154記録）を全照合し、TEST119の原因別修正を準備。[今回計画](plans/test119-device-failures.md)・[修正表](fix-records.md)。初回RSと`--until-target`を維持。

通路の新床で判断が変わる停止、PARTIAL入口からの観測継続、価格の縦断片/低い配置、松明床、早期FULL後の実入店/新DATA所有を修正。実周回のyield有効時の処理順も因果Red→Greenで修正した。新28件/直接関連と独立差分レビューを確認。3fの実機完全陰性→RS→ef継承成功と判定packetを保持し、efの別停止は別原因として扱う。

基準は[TEST118/build263](https://github.com/shuhei0720/necrogold-automation/releases/tag/test118-build263)、CODEdca8ca3/保存64f7b4f。TEST119は37native中4変更/33保持、API/ABI/profile3を保持して再seal/配置を照合。選択host130/client53・新Mac1case/2subrunと実IPA/固定配布をこれから確認する。過去Mac成功や単体合格を新版iPhoneの改善完了とは扱わない。
