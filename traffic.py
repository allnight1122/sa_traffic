from __future__ import annotations
from typing import TYPE_CHECKING
from collections import Counter # キューの内容を集計するため

# 型チェック時のみインポート（循環参照対策）
if TYPE_CHECKING:
    from graph import Edge, Node

# 信号モードごとの進行許可
# key: モードID, value: {進入方向: [許可される動作のリスト]}
# 方位コード: 1:北, 2:南, 3:東, 4:西
MODE_FLOW = {
    1: {1: ["straight"], 2: ["straight"]},        # 北(1)から直進、南(2)から直進
    2: {2: ["straight", "right"]},               # 南(2)から直進・右折（合計でflow_limit）
    3: {1: ["straight", "right"]},               # 北(1)から直進・右折
    4: {3: ["straight"], 4: ["straight"]},        # 東(3)から直進、西(4)から直進
    5: {4: ["straight", "right"]},               # 西(4)から直進・右折
    6: {3: ["straight", "right"]},               # 東(3)から直進・右折
}
"""
信号モードごとの進行許可

- key: モードID
- value: {進入方向: [許可される動作のリスト(`"straight"`, `"right"`)]}

方位コード: 1:北, 2:南, 3:東, 4:西
"""



class EdgeTraffic:
    """
    有向エッジにおける交通状況（車両の位置）を管理するクラス
    """
    def __init__(self, start_id: int, end_id: int):
        self.start_id = start_id
        self.end_id = end_id
        # 車両の位置リスト (エッジの始点からの距離 [m])
        self.vehicles: list[float] = []

class NodeTraffic:
    """
    交差点（ノード）における交通状況（待機車両）を管理するクラス
    """
    def __init__(self, flow_limit: int = 5):
        # 各方位に対して進行希望のリスト（キューとして機能する）
        # 進入方向: 1:北, 2:南, 3:東, 4:西
        self.queues: dict[int, list[str]] = {
            1: [],  # 北からの進入待機キュー
            2: [],  # 南からの進入待機キュー
            3: [],  # 東からの進入待機キュー
            4: [],  # 西からの進入待機キュー
        }
        # 1方位から単位時間あたりに流出できる車の最大台数
        self.flow_limit_value = flow_limit 
        self.mode: int = 1  # 現在の信号モード（1〜6）

    def set_mode(self, mode: int):
        """信号モードを設定する"""
        if 1 <= mode <= 6:
            self.mode = mode

    def add_vehicle(self, direction: int, turn: str):
        """
        指定方位のキューに車両を追加する 
        
        - `direction` は親友方向であり, 1:北, 2:南, 3:東, 4:西
        - `turn` は希望進行方向であり, `"straight"`, `"right"`, `"left"`の文字列を受け入れる
        """
        if direction in self.queues and turn in ["straight", "right", "left"]:
            self.queues[direction].append(turn)

    def flow_out(self, direction: int, allowed_turns: list[str]) -> dict[str, int]:
        """
        指定方位から許可された進行方向の車両を、flow_limit 台まで順番に流す。

        車の流し方はFIFO
        """
        result: dict[str, int] = Counter()
        limit = self.flow_limit_value
        flowed = 0
        new_queue: list[str] = []

        # キューの先頭から処理
        for turn in self.queues[direction]:
            if flowed < limit and turn in allowed_turns:
                # 許可されており、かつリミットに達していない場合
                result[turn] += 1
                flowed += 1
            else:
                # 許可されていない、またはリミット超過の場合は待機
                new_queue.append(turn)

        # キューを更新
        self.queues[direction] = new_queue
        return dict(result)

    def flow_by_mode(self) -> dict[tuple[int, str], int]:
        """
        現在の信号モードに従って車両を流す。
        戻り値: {(進入方向, 進行方向): 流した台数}
        """
        result: dict[tuple[int, str], int] = {}
        # 現在のモードで許可されている進入方向と動作の組み合わせを取得
        allowed_flow = MODE_FLOW.get(self.mode, {})
        
        for direction, allowed_turns in allowed_flow.items():
            if direction in self.queues:
                # 許可された進入方向に対して flow_out を実行
                out = self.flow_out(direction, allowed_turns)
                
                # 流出した台数を結果辞書に格納
                for turn, count in out.items():
                    result[(direction, turn)] = count
                    
        return result