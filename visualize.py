import matplotlib.pyplot as plt
import os
import io
from typing import List, Dict, Tuple, Any
from collections import Counter
from PIL import Image
import numpy as np
from traffic import FLOW_TO, MODE_FLOW
from collections import Counter

# --- ここでインポート ---
try:
    from IPython.display import display, Image as IPImage
    from IPython import get_ipython
    HAS_IPYTHON = True
except ImportError:
    HAS_IPYTHON = False
# ----------------------



# グラフ情報・交通情報のインポート（構造のみ必要）
from graph import MapInfo 
from traffic import MODE_FLOW 



# クラス外またはクラス内で定義
ARROW_LENGTH_MODE_FROM = 0.3
ARROW_LENGTH_MODE_TO = 0.4

QUEUE_TEXT_DISTANCE_NS = 0.2
QUEUE_TEXT_DISTANCE_EW = 0.2


# 方位ベクトル (描画座標系: Y軸は下が増加)
# 1:北, 2:南, 3:東, 4:西
DISPLAY_DIRECTION_VECTORS = {
    1: (0, -1),
    2: (0, +1),
    3: (+1, 0),
    4: (-1, 0)
}

class TrafficVisualizer:
    def __init__(self, fps: int = 10):
        self.frames = []
        self.fps = fps
        # self.fig は create_animation 内で毎回生成・破棄
    def _get_node_coords(self, node_id: int, mapinfo: MapInfo) -> tuple[float, float]:
        """
        ノードIDから(x, y)座標を計算する。
        左上(0,0)から右へ進み、端に到達したら下の行へ移動する仕様に対応。
        """
        x = node_id % mapinfo.width()
        y = node_id // mapinfo.width()
        return float(x), float(y)
    
    def _generate_frame(self, step_data: Dict[str, Any], mapinfo: MapInfo) -> Image.Image:
        """
        1ステップのデータから画像を生成して返す。
        """
        # Figureの設定
        fig = plt.figure(figsize=(8, 8))
        ax = fig.gca()

        W, H = mapinfo.width(), mapinfo.height()
        ax.set_xlim(-0.5, W - 0.5)
        ax.set_ylim(-0.5, H - 0.5)
        ax.set_aspect('equal')
        ax.invert_yaxis()
        ax.axis('off')

        # 1. edge(lightgray)と車両の描画
        edges_log = step_data.get("edges", {})
        for edge_id_str, vehicle_positions in edges_log.items():
            sid, eid = map(int, edge_id_str.split('_'))
            s_node = mapinfo.getNode(sid)
            e_node = mapinfo.getNode(eid)
            edge = mapinfo.getEdgeBetween(sid, eid)
            
            xs, ys = self._get_node_coords(sid, mapinfo)
            xe, ye = self._get_node_coords(eid, mapinfo)
            
            # 以下デバッグ用テキスト
            # print(f"{s_node.getId()}: E{s_node.east_id()} W{s_node.west_id()} N{s_node.north_id()} S{s_node.south_id()}")
            
            
            # 方角ベクトルの決定 (sidから見たeidの方向)
            if eid == s_node.north_id():   dx, dy = 0, -1
            elif eid == s_node.south_id(): dx, dy = 0, 1
            elif eid == s_node.east_id():  dx, dy = 1, 0
            elif eid == s_node.west_id():  dx, dy = -1, 0
            else: continue

            # エッジの線を描画 (2分割でワープに対応)
            # sidから0.5まで
            ax.plot([xs, xs + dx * 0.5], [ys, ys + dy * 0.5], color='lightgray', lw=1, zorder=1)
            # eidから-0.5まで (逆算)
            ax.plot([xe, xe - dx * 0.5], [ye, ye - dy * 0.5], color='lightgray', lw=1, zorder=1)

            # 車両のプロット
            # 進行度合いrで分岐する.
            for pos in vehicle_positions:
                r = pos / edge.length
                if r <= 0.5:
                    # sidから進む
                    dvx, dvy = xs + dx * r, ys + dy * r
                else:
                    # eidから戻る
                    dvx, dvy = xe - dx * (1 - r), ye - dy * (1 - r)
                
                # トーラス補正をかけて描画
                ax.plot(dvx, dvy, 'ro', markersize=4, zorder=10)
        nodes_log = step_data["nodes"]

        # 1. ノードとモードの描画
        for node_id_key, data in nodes_log.items():
            # JSON化の過程でキーが文字列になっている可能性があるためint変換
            node_id = int(node_id_key)
            x, y = self._get_node_coords(node_id, mapinfo)

            # ノード点 (交差点)
            ax.plot(x, y, 'ko', markersize=8, zorder=3)

            # モード番号の表示 (ノードのすぐ右上に小さく表示)
            mode = data.get("mode", "?")
            if mode in MODE_FLOW:
                allowed_entries = MODE_FLOW[mode] # 例: {1: ["straight", "right"]}
                
                for entry_dir, turns in allowed_entries.items():
                    # --- A. 進入元の表示 (矢印なし灰色直線) ---
                    # DISPLAY_DIRECTION_VECTORSを使って進入元(方角)のベクトルを取得
                    from_vec = DISPLAY_DIRECTION_VECTORS[entry_dir]
                    # 交差点から「進入元方位」へ伸びる線（車はここからやってくる）
                    ax.plot([x, x + from_vec[0] * ARROW_LENGTH_MODE_FROM],
                            [y, y + from_vec[1] * ARROW_LENGTH_MODE_FROM],
                            color='blue', linewidth=2, alpha=0.7, zorder=2)

                    # --- B. 進行先の表示 (矢印あり青色直線) ---
                    for turn in turns:
                        # FLOW_TOから進行先の方位コードを取得
                        to_dir_code = FLOW_TO.get((entry_dir, turn))
                        if to_dir_code:
                            to_vec = DISPLAY_DIRECTION_VECTORS[to_dir_code]
                            # 交差点から「進行先方位」へ向かう矢印
                            ax.arrow(x, y, 
                                     to_vec[0] * ARROW_LENGTH_MODE_TO, 
                                     to_vec[1] * ARROW_LENGTH_MODE_TO,
                                     head_width=0.1, head_length=0.12, 
                                     fc='blue', ec='blue', zorder=4,
                                     length_includes_head=True)
                            
            
            queues = data.get("queues", {})
            for entry_dir_str, turn_list in queues.items():
                if not turn_list:
                    continue
                
                entry_dir = int(entry_dir_str)
                counts = Counter(turn_list)
                
                # 各方向のカウント（存在しない場合は0）
                l_cnt = counts.get("left", 0)
                s_cnt = counts.get("straight", 0)
                r_cnt = counts.get("right", 0)

                # 方位に応じたフォーマットと配置
                if entry_dir == 1: # 北 (基準点から北へ)
                    q_text = f"{r_cnt}|{s_cnt}|{l_cnt}"
                    tx, ty = x, y - QUEUE_TEXT_DISTANCE_NS
                elif entry_dir == 2: # 南 (基準点から南へ)
                    q_text = f"{l_cnt}|{s_cnt}|{r_cnt}"
                    tx, ty = x, y + QUEUE_TEXT_DISTANCE_NS
                elif entry_dir == 3: # 東 (基準点から東へ)
                    q_text = f"{r_cnt}\n{s_cnt}\n{l_cnt}"
                    tx, ty = x + QUEUE_TEXT_DISTANCE_EW, y
                elif entry_dir == 4: # 西 (基準点から西へ)
                    q_text = f"{l_cnt}\n{s_cnt}\n{r_cnt}"
                    tx, ty = x - QUEUE_TEXT_DISTANCE_EW, y
                else:
                    continue

                # テキストの描画
                ax.text(tx, ty, q_text, 
                        color='darkgreen', fontsize=8, 
                        ha='center', va='center', 
                        fontweight='bold',
                        # 背景を白くして読みやすくする（任意）
                        bbox=dict(facecolor='white', alpha=0.6, edgecolor='none', pad=1))

        # 2. ステップ情報の表示
        ax.set_title(f"Time: {step_data['time']} (Waste: {step_data['timewasted']: .03f})", fontsize=12)

        # MatplotlibのFigureをPIL Imageに変換
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        buf.seek(0)
        img = Image.open(buf)
        
        plt.close(fig) # メモリ解放
        return img
    
    def create_animation(self, history: List[Dict[str, Any]], mapinfo: Any):
        """history全体を処理してGIFを保存し、Colabなら表示する"""
        


        frames = []
        print(f"Generating {len(history)} frames...")
        
        # 2. 各ステップの画像を生成
        for i, step_data in enumerate(history):
            frame = self._generate_frame(step_data, mapinfo)
            frames.append(frame)
            if (i + 1) % 10 == 0:
                print(f"Frame {i + 1}/{len(history)} done.")

        if not frames:
            print("No frames generated.")
            return
        
        self.frames= frames

    def save_animation(self, output_path: str="results/simulation.gif") -> str:
        if not self.frames:
            print("No frames to save.")
            return ""

        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        frame_duration = int(1000 / self.fps)
        self.frames[0].save(
            output_path,
            save_all=True,
            append_images=self.frames[1:],
            duration=frame_duration,
            loop=0
        )
        print(f"Animation saved to: {output_path}")
        return output_path
    
    def show_animation(self, file_path: str = "results/simulation.gif"):
        """
        Colab/Jupyter上で`file_path`で指定したGIFを表示する
        """
        if not (HAS_IPYTHON and get_ipython() is not None):
            print("Inline display is only available in Notebook environments.")
            return
        
        try:
            if file_path and os.path.exists(file_path):
                # ファイルから表示
                with open(file_path, "rb") as f:
                    display(IPImage(data=f.read(), format='png'))
            elif self.frames:
                # メモリ上の self.frames から直接GIFを生成して表示
                buf = io.BytesIO()
                frame_duration = int(1000 / self.fps)
                self.frames[0].save(
                    buf,
                    format='GIF',
                    save_all=True,
                    append_images=self.frames[1:],
                    duration=frame_duration,
                    loop=0
                )
                display(IPImage(data=buf.getvalue(), format='png'))
            else:
                print("No frames or file to display.")
        except Exception as e:
            print(f"Display error: {e}")

    def clear_frames(self):
        self.frames=[]