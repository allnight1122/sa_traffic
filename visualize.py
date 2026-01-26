import matplotlib.pyplot as plt
import os
from typing import Dict, Tuple, Any
from collections import Counter
# グラフ情報（MapInfo, Nodeなど）
from graph import MapInfo 
# 交通情報（EdgeTraffic, NodeTraffic, DIRECTION_VECTORS, MODE_FLOWなど）
from traffic import EdgeTraffic, NodeTraffic, MODE_FLOW 



# 描画関連定数

NODE_SCALE = 2.0
ARROW_LENGTH_RATIO = 0.3 
"""
矢印がノード中心から伸びる割合 (NODE_SCALEに対する割合)
"""
CAR_OFFSET_MAGNITUDE = 0.5 
"""
トーラス車輛描画時のノードからのオフセットの最大値 (NODE_SCALEに対する割合)
"""
DIRECTION_VECTORS = {
    # 進入元: 北 (1)
    (1, "straight"): (0, 1),   # 北(1) -> 南へ流出 (Y増加)
    (1, "right"):    (1, 0),   # 北(1) -> 東へ流出 (X増加)
    (1, "left"):     (-1, 0),  # 北(1) -> 西へ流出 (X減少)

    # 進入元: 南 (2)
    (2, "straight"): (0, -1),  # 南(2) -> 北へ流出 (Y減少)
    (2, "right"):    (-1, 0),  # 南(2) -> 西へ流出 (X減少)
    (2, "left"):     (1, 0),   # 南(2) -> 東へ流出 (X増加)

    # 進入元: 東 (3)
    (3, "straight"): (-1, 0),  # 東(3) -> 西へ流出 (X減少)
    (3, "right"):    (0, 1),   # 東(3) -> 南へ流出 (Y増加)
    (3, "left"):     (0, -1),  # 東(3) -> 北へ流出 (Y減少)

    # 進入元: 西 (4)
    (4, "straight"): (1, 0),   # 西(4) -> 東へ流出 (X増加)
    (4, "right"):    (0, -1),  # 西(4) -> 北へ流出 (Y減少)
    (4, "left"):     (0, 1),   # 西(4) -> 南へ流出 (Y増加)
}
"""
信号モードの矢印描画用ベクトル

- key: (進入方向, 進行方向), value: (`dx`, `dy`)
- (`dx`, `dy` は流出先に向かうベクトル。Y座標は南方向が増加する前提)

方位コード: 1:北, 2:南, 3:東, 4:西
"""


def get_node_coords(node_id: int, mapinfo: MapInfo) -> Tuple[float, float]:
    """ノードIDから描画座標 (x, y) を取得するヘルパー関数"""
    x = (node_id % mapinfo.width()) * NODE_SCALE
    y = (node_id // mapinfo.width()) * NODE_SCALE
    return x, y

def draw_nodes_and_traffic_queues(ax: Any, mapinfo: MapInfo, node_traffics: Dict[int, NodeTraffic]):
    """ノード自体と、各方位の待機車両数を描画する"""
    w = mapinfo.width()
    
    for node_id, node_traffic in node_traffics.items():
        x, y = get_node_coords(node_id, mapinfo)
        
        # ノード描画
        ax.plot(x, y, 'ko', markersize=5, zorder=3) # ノードは最前面に
        # ax.text(x, y + 0.3, f"{node_id}", fontsize=6, ha="center", color="black", zorder=4)

        # 待機車両数の表示
        offsets_text = {1: (0, 0.3), 2: (0, -0.3), 3: (0.3, 0), 4: (-0.3, 0)} # テキストオフセット
        labels_dir = {1: "N", 2: "S", 3: "E", 4: "W"}
        
        for direction in [1, 2, 3, 4]:
            queue_counts = Counter(node_traffic.queues[direction])
            
            parts = []
            for turn_type in ["straight", "right", "left"]:
                count = queue_counts[turn_type]
                if count > 0:
                    parts.append(f"{turn_type[0].upper()}:{count}")
            
            if parts:
                dx_text, dy_text = offsets_text[direction]
                label_text = f"{labels_dir[direction]}:" + " ".join(parts)
                ax.text(x + dx_text, y + dy_text, label_text, color="darkgreen", fontsize=7, ha="center", zorder=4)

def draw_signal_arrows(ax: Any, mapinfo: MapInfo, node_traffics: Dict[int, NodeTraffic]):
    """現在の信号モードに従って、許可された通過方向の矢印を描画する"""
    for node_id, node_traffic in node_traffics.items():
        x, y = get_node_coords(node_id, mapinfo)
        mode = node_traffic.mode
        allowed_flow = MODE_FLOW.get(mode, {})
        
        drawn_entry_directions = set() # 進入元への直線は一度だけ描画
        
        for direction, allowed_turns in allowed_flow.items():
            if not allowed_turns: continue

            # 1. 進入元 -> 中心 (直線) の描画
            if direction not in drawn_entry_directions:
                # 許可されているターンの一つを使って進入方向の逆ベクトルを決定
                turn_sample = allowed_turns[0] 
                vec_exit = DIRECTION_VECTORS.get((direction, turn_sample))
                if vec_exit is None: continue
                
                dx_entry = -vec_exit[0] # 進入元から中心へ向かうX方向
                dy_entry = -vec_exit[1] # 進入元から中心へ向かうY方向
                
                start_x_line = x + dx_entry * ARROW_LENGTH_RATIO * NODE_SCALE # ノード中心からARROW_LENGTH_RATIO分離れた点
                start_y_line = y + dy_entry * ARROW_LENGTH_RATIO * NODE_SCALE
                
                ax.plot([start_x_line, x], [start_y_line, y], color='gray', linewidth=2.5, zorder=1)
                drawn_entry_directions.add(direction)

            # 2. 中心 -> 流出先 (矢印) の描画
            for turn in allowed_turns:
                vec_exit = DIRECTION_VECTORS.get((direction, turn))
                if vec_exit is None: continue

                dx_exit = vec_exit[0] * ARROW_LENGTH_RATIO * NODE_SCALE
                dy_exit = vec_exit[1] * ARROW_LENGTH_RATIO * NODE_SCALE
                
                ax.arrow(
                    x, y, dx_exit, dy_exit,
                    head_width=0.15 * NODE_SCALE, head_length=0.2 * NODE_SCALE, # スケールに合わせる
                    fc='blue', ec='blue', linewidth=1.5,
                    length_includes_head=True, zorder=2
                )

def draw_vehicles(ax: Any, mapinfo: MapInfo, edge_traffics: Dict[Tuple[int, int], EdgeTraffic]):
    """エッジ上の車両を描画する"""
    w = mapinfo.width()
    h = mapinfo.height()

    for (start_id, end_id), traffic in edge_traffics.items():
        edge = mapinfo.getEdgeBetween(start_id, end_id)
        if edge is None or edge.length == 0:
            continue

        sx, sy = get_node_coords(start_id, mapinfo)
        ex, ey = get_node_coords(end_id, mapinfo)

        # 描画上の差分座標とトーラス補正の計算
        dx_draw = ex - sx
        dy_draw = ey - sy

        is_wrapped = False
        if abs(dx_draw) > w * NODE_SCALE / 2: 
            dx_draw -= w * NODE_SCALE if dx_draw > 0 else -w * NODE_SCALE
            is_wrapped = True
        if abs(dy_draw) > h * NODE_SCALE / 2: 
            dy_draw -= h * NODE_SCALE if dy_draw > 0 else -h * NODE_SCALE
            is_wrapped = True
            
        for pos in traffic.vehicles:
            ratio = pos / edge.length
            car_x, car_y = 0.0, 0.0 # 車の描画座標

            if is_wrapped:
                # トーラス構造上の車両描画: ノードの外側へオフセット
                if ratio < 0.5:
                    # 始点 n1 を基準: n1 から外界へ去っていくイメージ (d_draw を加算)
                    car_x = sx + dx_draw * ratio
                    car_y = sy + dy_draw * ratio
                else:
                    # 終点 n2 を基準: 外界から n2 へ近づいてくるイメージ (d_draw を減算)
                    car_x = ex - dx_draw * (1 - ratio)
                    car_y = ey - dy_draw * (1 - ratio)
            else:
                # 非トーラス構造上の車両描画: 線形補間
                car_x = sx + dx_draw * ratio
                car_y = sy + dy_draw * ratio

            ax.plot(car_x, car_y, 'ro', markersize=3, zorder=5) # 車は最前面より一つ下

def visualize_simulation_step(mapinfo: MapInfo, edge_traffics: Dict, node_traffics: Dict, time_step: int, output_dir: str = "frames"):
    """
    シミュレーションの各ステップの全体像を描画する。

    描画実装のメイン
    """
    os.makedirs(output_dir, exist_ok=True)
    plt.clf()
    ax = plt.gca()

    # 描画要素を順番に呼び出す (zorderで重ね順を制御)
    draw_nodes_and_traffic_queues(ax, mapinfo, node_traffics)
    draw_signal_arrows(ax, mapinfo, node_traffics)
    draw_vehicles(ax, mapinfo, edge_traffics)

    # 軸設定と保存
    ax.set_title(f"Simulation Time: {time_step}", fontsize=12)
    ax.set_xlim(-1 * NODE_SCALE, (mapinfo.width() + 1) * NODE_SCALE)
    ax.set_ylim(-1 * NODE_SCALE, (mapinfo.height() + 1) * NODE_SCALE)
    ax.set_aspect('equal')
    ax.invert_yaxis()  # 北を上にする
    plt.savefig(os.path.join(output_dir, f"frame_{time_step:03d}.png"))
    plt.pause(0.01)

















