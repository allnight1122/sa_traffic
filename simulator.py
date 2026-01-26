from traffic import *
from graph import *
import random
import matplotlib.pyplot as plt
import os
from typing import Dict, Tuple, List, Any
import pdb
import visualize
import solving.solve_sa




def determine_direction(from_id: int, to_id: int, mapinfo: MapInfo) -> int:
    """
    to_id の交差点への進入方向（進入元）を決定する。
    1:北から進入, 2:南から進入, 3:東から進入, 4:西から進入
    （トーラス構造に対応）
    """
    to_node = mapinfo.getNode(to_id)
    
    # to_nodeから見て、from_idがどの方向にあるかを判定する
    if to_node.north_id() == from_id:
        return 2 # from_idはto_nodeの南にある -> to_nodeへは南から進入 (方向2)
    elif to_node.south_id() == from_id:
        return 1 # from_idはto_nodeの北にある -> to_nodeへは北から進入 (方向1)
    elif to_node.east_id() == from_id:
        return 4 # from_idはto_nodeの西にある -> to_nodeへは西から進入 (方向4)
    elif to_node.west_id() == from_id:
        return 3 # from_idはto_nodeの東にある -> to_nodeへは東から進入 (方向3)
    
    return 0 


def get_next_node(current_node: Node, direction: int, turn: str) -> Node | None:
    """
    交差点（current_node）を通過後、次に車が進むノードを返す。
    """
    if direction == 1: # 北 (進入元)
        if turn == "straight":
            return current_node.south_node() # 直進 -> 南へ
        elif turn == "right":
            return current_node.east_node()  # 右折 -> 東へ
        elif turn == "left":
            return current_node.west_node()  # 左折 -> 西へ
    elif direction == 2: # 南 (進入元)
        if turn == "straight":
            return current_node.north_node() # 直進 -> 北へ
        elif turn == "right":
            return current_node.west_node()  # 右折 -> 西へ
        elif turn == "left":
            return current_node.east_node()  # 左折 -> 東へ
    elif direction == 3: # 東 (進入元)
        if turn == "straight":
            return current_node.west_node()  # 直進 -> 西へ
        elif turn == "right":
            return current_node.south_node() # 右折 -> 南へ
        elif turn == "left":
            return current_node.north_node() # 左折 -> 北へ
    elif direction == 4: # 西 (進入元)
        if turn == "straight":
            return current_node.east_node()  # 直進 -> 東へ
        elif turn == "right":
            return current_node.north_node() # 右折 -> 北へ
        elif turn == "left":
            return current_node.south_node() # 左折 -> 南へ
    return None

def calc_mode(time: int, edge_traffics: Dict, node_traffics: Dict) -> Dict[int, int]:
    """
    信号モード切り替えのロジック (固定サイクル)

    推奨される信号モードセットを返す
    """
    mode_dict = {}
    for node_id in node_traffics:
        # 10ステップごとにモードを切り替え (1〜6を順に繰り返す)
        # 次のステップはここの実装をSAをつかって実装する予定になる. 
        mode_dict[node_id] = (time // 10) % 6 + 1 
    return mode_dict

def calc_step_timewasted(mapinfo: MapInfo, node_traffics: Dict) -> float:
    """
    単位時間あたり(ステップごと)のTime Wasted合計値を計算する
    """
    # 計測されたTime Wasted
    waste = 0.0
    # マップ内最高速度
    max_speed=mapinfo.globalMaxSpeed()

    # すべてのノードについて調査
    for node_id, node_traffic in node_traffics.items():
        current_node= mapinfo.getNode(nodeid=node_id)
        # 各ノードのすべての待機(すべての行先キュー)について調査
        for direction, queue in node_traffic.queues.items():
            for turn in queue:
                # 行先ノードの取得
                next_node = get_next_node(current_node, direction, turn)

                if next_node: 
                    next_node_id=next_node.getId()
                    # 行先エッジの取得
                    edge=mapinfo.getEdgeBetween(node_id, next_node_id)
                    # Wasteの加算
                    if edge: 
                        waste += edge.speed_limit / max_speed
    return waste


# --- メインロジック ---

def simulation_init(width: int = 6, height: int = 6, car_count: int = 100) -> Tuple[MapInfo, Dict[Tuple[int, int], EdgeTraffic], Dict[int, NodeTraffic]]:
    """
    シミュレーションの初期設定: マップ、交通オブジェクトの生成、車両の初期配置
    """  
    mapinfo = MapInfo(width, height)

    node_traffics: Dict[int, NodeTraffic] = {} 
    edge_traffics: Dict[Tuple[int, int], EdgeTraffic] = {}

    for key, edge in mapinfo._edges.items():
        a, b = edge.start_id, edge.end_id

        # 正方向 (a -> b) と 逆方向 (b -> a) の有向エッジトラフィックを定義
        edge_traffics[(a, b)] = EdgeTraffic(start_id=a, end_id=b)
        edge_traffics[(b, a)] = EdgeTraffic(start_id=b, end_id=a)

    for node_id in range(width * height):
        node_traffics[node_id] = NodeTraffic()

    # 車をランダムに設置する
    for _ in range(car_count):
        edge_key = random.choice(list(edge_traffics.keys()))
        edge_traffic = edge_traffics[edge_key]

        edge = mapinfo.getEdgeBetween(edge_key[0], edge_key[1])
        if edge is None:
            continue

        # ランダムな位置（0〜length）に車両を配置
        position = random.uniform(0, edge.length)
        edge_traffic.vehicles.append(position)
    
    return mapinfo, edge_traffics, node_traffics

def update_edge_traffic(mapinfo: MapInfo, edge_traffics: Dict, node_traffics: Dict, dt: float = 1.0):
    """
    エッジ上の車両を移動させ、終点に到達した車両をキューに追加する。
    """
    for key, traffic in edge_traffics.items():
        # 無向グラフからエッジプロパティを取得
        edge = mapinfo.getEdgeBetween(key[0], key[1])
        if edge is None:
            continue

        new_positions = []
        for pos in traffic.vehicles:
            move_distance = edge.speed_limit * dt
            new_pos = pos + move_distance
            
            if new_pos < edge.length:
                # エッジ上に留まる
                new_positions.append(new_pos)
            else:
                # 車両が終端に到達 → Nodeへ移行（交差点待機状態）
                end_node_id = key[1]
                
                # 進入方向の決定
                direction = determine_direction(key[0], key[1], mapinfo)
                
                # 進行方向の決定（左折確率0）
                turn = random.choices(["straight", "right", "left"], weights=[0.8, 0.2, 0.0])[0]
                
                # 終点ノードのキューに追加
                node_traffics[end_node_id].add_vehicle(direction, turn)
                
        traffic.vehicles = new_positions

def update_node_traffic(mapinfo: MapInfo, edge_traffics: Dict, node_traffics: Dict):
    """
    交差点キューの車両を信号とフローリミットに従って次エッジへ流出させる。
    """
    for node_id, node_traffic in node_traffics.items():
        # 現在の信号モードで通過許可された車両群を取得
        flow_result = node_traffic.flow_by_mode()

        for (direction, turn), count in flow_result.items():
            for _ in range(count):
                current_node = mapinfo.getNode(node_id)
                # 次に進むノード（流出先）を取得
                next_node = get_next_node(current_node, direction, turn)
                
                if next_node is None:
                    continue

                start_id = node_id
                end_id = next_node.getId()
                edge_key = (start_id, end_id)

                # 次のエッジが存在するか確認（有向エッジ）
                if edge_key not in edge_traffics:
                    continue

                # 新たにエッジに車両を追加（位置 x=0.0）
                edge_traffics[edge_key].vehicles.append(0.0)

def update_signal_modes(time: int, edge_traffics: Dict, node_traffics: Dict, mapinfo: MapInfo):
    """
    信号モードを更新する。
    """
    # new_modes = calc_mode(time, edge_traffics, node_traffics)


    print(f"\n[Time {time}] Starting SA Optimization...")
        
    # solve_main を実行して新しいモード配置を取得
    # (solve_main 内で q1, q2, q3 が呼び出され、dimod で解かれる)
    new_modes = solving.solve_sa.solve_main(time, edge_traffics, node_traffics, mapinfo)
        
        # 取得した辞書 {node_id: mode_id} を実際のノード状態に反映
    for node_id, mode_id in new_modes.items():
        if node_id in node_traffics:
            old_mode = node_traffics[node_id].mode
            node_traffics[node_id].mode = mode_id
                
            # モードが変わった場合のみログを出す（任意）
            if old_mode != mode_id:
                print(f"  Node {node_id:2d}: Mode {old_mode} -> {mode_id}")
        
    print(f"[Time {time}] Optimization complete.\n")


def simulation(car_count: int = 100):
    """
    シミュレーションのメインループを実行する。
    """
    # 初期化
    mapinfo, edge_traffics, node_traffics = simulation_init(width=6, height=6, car_count=car_count)

    # Time Wastedの記録リスト
    time_wasted=[]
    
    # シミュレーション時間設定
    simulationtime = 100


    print(f"--- Simulation Started (T={simulationtime}) ---")
    # メインループ開始
    for time in range(simulationtime):
        
        # 車両の移動と交差点への移動
        update_edge_traffic(mapinfo, edge_traffics, node_traffics, dt=1.0)
        
        # 信号モードの更新 (10ステップごと)
        if time % 10 == 0: 
            update_signal_modes(time, edge_traffics, node_traffics, mapinfo)
        
        # 交差点での車両の通過
        update_node_traffic(mapinfo, edge_traffics, node_traffics)

        # Time Wastedの計算. 
        step_time_wasted=calc_step_timewasted(mapinfo, node_traffics)

        print(f"\n[Time {time}] TIme Waste: {step_time_wasted}")
        time_wasted.append(step_time_wasted)

        # 視覚化
        visualize.visualize_simulation_step(mapinfo, edge_traffics, node_traffics, time)



    print("--- Simulation Finished ---")

