import matplotlib.pyplot as plt
import os
import io
from typing import Dict, Tuple, Any
from collections import Counter
from PIL import Image

# グラフ情報・交通情報のインポート
from graph import MapInfo 
from traffic import EdgeTraffic, NodeTraffic, MODE_FLOW 

# --- 描画関連定数 ---
NODE_SCALE = 2.0
ARROW_LENGTH_RATIO = 0.3 
CAR_OFFSET_MAGNITUDE = 0.5 

DIRECTION_VECTORS = {
    (1, "straight"): (0, 1),   (1, "right"): (1, 0),    (1, "left"): (-1, 0),
    (2, "straight"): (0, -1),  (2, "right"): (-1, 0),   (2, "left"): (1, 0),
    (3, "straight"): (-1, 0),  (3, "right"): (0, 1),    (3, "left"): (0, -1),
    (4, "straight"): (1, 0),   (4, "right"): (0, -1),   (4, "left"): (0, 1),
}

class TrafficVisualizer:
    def __init__(self, fps: int = 10):
        self.frames = []
        self.fps = fps
        # Aggバックエンドを使用して非表示で描画（Colab/ローカル共通で高速）
        import matplotlib
        matplotlib.use('Agg')
        self.fig = plt.figure(figsize=(10, 10))

    def _get_node_coords(self, node_id: int, mapinfo: MapInfo) -> Tuple[float, float]:
        x = (node_id % mapinfo.width()) * NODE_SCALE
        y = (node_id // mapinfo.width()) * NODE_SCALE
        return x, y

    def capture(self, mapinfo: MapInfo, edge_traffics: Dict, node_traffics: Dict, time_step: int):
        """現在のステップをメモリ上の画像として保存する"""
        self.fig.clf()
        ax = self.fig.gca()

        # 1. ノードとキューの描画
        self._draw_nodes_and_queues(ax, mapinfo, node_traffics)
        # 2. 信号矢印の描画
        self._draw_signals(ax, mapinfo, node_traffics)
        # 3. 車両の描画
        self._draw_vehicles(ax, mapinfo, edge_traffics)

        # 軸とタイトルの設定
        ax.set_title(f"Simulation Time: {time_step}", fontsize=12)
        ax.set_xlim(-1 * NODE_SCALE, (mapinfo.width() + 1) * NODE_SCALE)
        ax.set_ylim(-1 * NODE_SCALE, (mapinfo.height() + 1) * NODE_SCALE)
        ax.set_aspect('equal')
        ax.invert_yaxis()

        # メモリ（BytesIO）に保存してImageオブジェクトとして保持
        buf = io.BytesIO()
        self.fig.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        self.frames.append(Image.open(buf))

    def save_gif(self, output_path: str = "results/simulation.gif"):
        """溜まったフレームをGIFとして書き出し、Colabなら表示する"""
        if not self.frames:
            print("No frames to save.")
            return

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        self.frames[0].save(
            output_path,
            save_all=True,
            append_images=self.frames[1:],
            duration=1000 // self.fps,
            loop=0
        )
        print(f"\nAnimation saved to: {output_path}")

        # Colab環境であればインライン表示
        try:
            from IPython.display import display, Image as IPImage
            display(IPImage(filename=output_path))
        except:
            pass

    # --- 内部描画メソッド（旧関数の移植） ---

    def _draw_nodes_and_queues(self, ax, mapinfo, node_traffics):
        for node_id, node_traffic in node_traffics.items():
            x, y = self._get_node_coords(node_id, mapinfo)
            ax.plot(x, y, 'ko', markersize=5, zorder=3)
            
            offsets = {1: (0, 0.3), 2: (0, -0.3), 3: (0.3, 0), 4: (-0.3, 0)}
            labels = {1: "N", 2: "S", 3: "E", 4: "W"}
            for d in [1, 2, 3, 4]:
                counts = Counter(node_traffic.queues[d])
                parts = [f"{t[0].upper()}:{counts[t]}" for t in ["straight", "right", "left"] if counts[t] > 0]
                if parts:
                    dx, dy = offsets[d]
                    ax.text(x + dx, y + dy, f"{labels[d]}:" + " ".join(parts), 
                            color="darkgreen", fontsize=7, ha="center", zorder=4)

    def _draw_signals(self, ax, mapinfo, node_traffics):
        for node_id, nt in node_traffics.items():
            x, y = self._get_node_coords(node_id, mapinfo)
            allowed = MODE_FLOW.get(nt.mode, {})
            drawn_dirs = set()
            for d, turns in allowed.items():
                if not turns: continue
                if d not in drawn_dirs:
                    vec = DIRECTION_VECTORS.get((d, turns[0]))
                    if vec:
                        ax.plot([x - vec[0]*ARROW_LENGTH_RATIO*NODE_SCALE, x], 
                                [y - vec[1]*ARROW_LENGTH_RATIO*NODE_SCALE, y], 
                                color='gray', linewidth=2.5, zorder=1)
                        drawn_dirs.add(d)
                for t in turns:
                    v = DIRECTION_VECTORS.get((d, t))
                    if v:
                        ax.arrow(x, y, v[0]*ARROW_LENGTH_RATIO*NODE_SCALE, v[1]*ARROW_LENGTH_RATIO*NODE_SCALE,
                                 head_width=0.3, head_length=0.4, fc='blue', ec='blue', zorder=2)

    def _draw_vehicles(self, ax, mapinfo, edge_traffics):
        w, h = mapinfo.width(), mapinfo.height()
        for (sid, eid), traffic in edge_traffics.items():
            edge = mapinfo.getEdgeBetween(sid, eid)
            if not edge or edge.length == 0: continue
            sx, sy = self._get_node_coords(sid, mapinfo)
            ex, ey = self._get_node_coords(eid, mapinfo)
            dx, dy = ex - sx, ey - sy

            # トーラス補正
            if abs(dx) > w * NODE_SCALE / 2: dx -= w * NODE_SCALE if dx > 0 else -w * NODE_SCALE
            if abs(dy) > h * NODE_SCALE / 2: dy -= h * NODE_SCALE if dy > 0 else -h * NODE_SCALE
            
            for pos in traffic.vehicles:
                r = pos / edge.length
                cx, cy = (sx + dx * r, sy + dy * r) if abs(dx) < w and abs(dy) < h else (0,0) # 簡易化
                # ラップしたエッジの描画
                if abs(ex-sx) > w*NODE_SCALE/2 or abs(ey-sy) > h*NODE_SCALE/2:
                    if r < 0.5: cx, cy = sx + dx * r, sy + dy * r
                    else: cx, cy = ex - dx * (1 - r), ey - dy * (1 - r)
                else:
                    cx, cy = sx + dx * r, sy + dy * r
                ax.plot(cx, cy, 'ro', markersize=3, zorder=5)