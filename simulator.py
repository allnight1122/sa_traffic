from traffic import *
from graph import *
import random
import matplotlib.pyplot as plt
import os
from typing import Dict, Tuple, List, Any
import pdb
import visualize
import solving.solve_sa
from param import *





def determine_direction(from_id: int, to_id: int, mapinfo: MapInfo) -> int:
    """
    to_id の交差点への進入方向（進入元）を決定する. 

    1:北から進入, 2:南から進入, 3:東から進入, 4:西から進入
    （トーラス構造に対応）

    to_idノードに対するfrom_idノードの位置を返す
    """
    to_node = mapinfo.getNode(to_id)

    if   to_node.north_id() == from_id:
        return 1
    elif to_node.south_id() == from_id:
        return 2
    elif to_node.east_id()  == from_id:
        return 3
    elif to_node.west_id()  == from_id:
        return 4
    
    return None
    




def get_next_node(current_node: Node, direction: int, turn: str) -> Node | None:
    """
    交差点（current_node）を通過後、次に車が進むノードを返す。
    """

    next_direction = FLOW_TO.get((direction, turn))

    if next_direction is None:
        return None

    if   next_direction == 1:
        return current_node.north_node()
    elif next_direction == 2:
        return current_node.south_node()
    elif next_direction == 3:
        return current_node.east_node()
    elif next_direction == 4:
        return current_node.west_node()
    return None

def calc_mode_fixedcycle(time: int, edge_traffics: Dict, node_traffics: Dict) -> Dict[int, int]:
    """
    信号モード切り替えのロジック (固定サイクル)

    固定サイクルによる信号モードを返す
    """
    mode_dict = {}
    for node_id in node_traffics:
        # 呼び出しごとにモードを切り替え (1〜6を順に繰り返す) 
        mode_dict[node_id] = (time // 10) % 6 + 1 
    return mode_dict

def calc_mode_randomcycle(time: int, edge_traffics: Dict, node_Traffics: Dict) -> Dict[int, int]:
    """
    信号モード切り替えのロジック (完全ランダム制)

    ランダムサイクルによる信号モードを返す
    """
    
    mode_dict = {}
    for node_id in node_Traffics:
        # 呼び出しごとにモードをランダムに割り当て
        mode_dict[node_id]= random.randint(1, 6)
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

def simulation_init(mapgenparam :MapGenerationParam, width: int = 6, height: int = 6, ) -> Tuple[MapInfo, Dict[Tuple[int, int], EdgeTraffic], Dict[int, NodeTraffic]]:
    """
    シミュレーションの初期設定: マップ、交通オブジェクトの生成、車両の初期配置
    """  
    mapinfo = MapInfo(width, height, mapgenparam.edge_length, mapgenparam.edge_speed_limit_array)

    node_traffics: Dict[int, NodeTraffic] = {} 
    edge_traffics: Dict[Tuple[int, int], EdgeTraffic] = {}

    for key, edge in mapinfo._edges.items():
        a, b = edge.start_id, edge.end_id

        # 正方向 (a -> b) と 逆方向 (b -> a) の有向エッジトラフィックを定義
        edge_traffics[(a, b)] = EdgeTraffic(start_id=a, end_id=b)
        edge_traffics[(b, a)] = EdgeTraffic(start_id=b, end_id=a)

    for node_id in range(width * height):
        node_traffics[node_id] = NodeTraffic()
        if mapgenparam.inital_signal==INITAL_SIGNAL_RANDOM: 
            node_traffics[node_id].mode=random.randint(1, 6)
        else:
            node_traffics[node_id].mode=mapgenparam.inital_signal

    # 車をランダムに設置する
    for _ in range(mapgenparam.car_count):
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

    流出した車の総数を返す
    """
    # 流出した車総数
    total_flow_out=0

    for node_id, node_traffic in node_traffics.items():
        # 現在の信号モードで通過許可された車両群を取得
        flow_result = node_traffic.flow_by_mode()

        for (direction, turn), count in flow_result.items():
            total_flow_out += count
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
    return total_flow_out

def update_signal_modes(simparams: SimulationParams,coefficient:Coefficient ,time: int,  edge_traffics: Dict, node_traffics: Dict, mapinfo: MapInfo):
    """
    信号モードを更新する。
    """
    # new_modes = calc_mode(time, edge_traffics, node_traffics)

    if simparams.update_strategy==UPDATE_STRATEGY_FIXED: 
        new_modes = calc_mode_fixedcycle(time, edge_traffics, node_traffics)
    elif simparams.update_strategy==UPDATE_STRATEGY_QUBO:
        print(f"\n[Time {time}] Starting SA Optimization...")
        
        # solve_main を実行して新しいモード配置を取得
        # (solve_main 内で q1, q2, q3 が呼び出され、dimod で解かれる)
        new_modes = solving.solve_sa.solve_main(coefficient, time, edge_traffics, node_traffics, mapinfo)
        

            
        print(f"[Time {time}] Optimization complete.")
    else: 
        new_modes=calc_mode_randomcycle(time,edge_traffics,node_traffics)
    
    # 取得した辞書 new_modes={node_id: mode_id} を実際のノード状態に反映
    for node_id, mode_id in new_modes.items():
        if node_id in node_traffics:
            old_mode = node_traffics[node_id].mode
            node_traffics[node_id].mode = mode_id
            if(simparams.show_mode_change):
                # モードが変わった場合のみログを出す (show_mode_change=True時のみ)
                if old_mode != mode_id:
                    print(f"  Node {node_id:2d}: Mode {old_mode} -> {mode_id}")



from visualize import TrafficVisualizer

def simulation(simparams: SimulationParams, coefficient :Coefficient , mapinfo: MapInfo, edge_traffics: Dict[Tuple[int, int], EdgeTraffic], node_traffics: Dict[int, NodeTraffic]) -> List:
    """
    シミュレーションのメインループを実行し、ログ保存とGIF生成を行う。
    """
    

    # 記録用リソースの準備
    history = []

    total_time_wasted=0.0
    # シミュレーション時間と信号更新周期設定
    simulationtime = simparams.simulation_time
    signal_update=simparams.signal_update_span

    print(f"--- Simulation Started (T={simulationtime}) ---")

    # メインループ
    for time in range(simulationtime):
        
        # --- 物理演算・ロジック ---
        # 車両の移動
        update_edge_traffic(mapinfo, edge_traffics, node_traffics, dt=1.0)
        
        # 流出前の待機車両総数を計測
        # timewastedと異なり速度で重みづけされない
        pre_outflow_waiting = sum(len(q) for nt in node_traffics.values() for q in nt.queues.values())

        # 信号モードの更新 
        if time % signal_update == 0 and time>0: 
            update_signal_modes(simparams, coefficient ,time, edge_traffics, node_traffics, mapinfo)
        
        # 交差点での車両の通過
        step_flow_out = update_node_traffic(mapinfo, edge_traffics, node_traffics)
        # 処理後の待機車両総数を計測
        post_outflow_waiting = sum(len(q) for nt in node_traffics.values() for q in nt.queues.values())
        # 指標計測
        step_time_wasted = calc_step_timewasted(mapinfo, node_traffics)

        flowout_ratio = step_flow_out / pre_outflow_waiting if pre_outflow_waiting > 0 else 0.0
        remain_ratio = post_outflow_waiting / pre_outflow_waiting if pre_outflow_waiting > 0 else 0.0
        print(f"\r[Time {time}] Time Waste: {step_time_wasted: 8.3f} Outflow Ratio: {flowout_ratio: 4.2f} Remain Ratio: {remain_ratio: 4.2f}", end="")
        total_time_wasted+=step_time_wasted

        # ログ用オブジェクト
        step_data = {
            "time": time,
            "timewasted": step_time_wasted,
            "step_flow_out": step_flow_out,
            "pre_outflow_waiting": pre_outflow_waiting, 
            "flowout_ratio": flowout_ratio, 
            "remain_ratio": remain_ratio,
            "nodes": {
                node_id: {
                    "mode": nt.mode,
                    "queues": {dir_key: list(q) for dir_key, q in nt.queues.items()}
                } for node_id, nt in node_traffics.items()
            },
            "edges": {
                f"{k[0]}_{k[1]}": [round(v, 2) for v in et.vehicles]
                for k, et in edge_traffics.items()
            }
        }
        history.append(step_data)

        # 可視化フレームのキャプチャ
        # 毎フレームキャプチャしてGIFの滑らかさを確保
        # viz.capture(mapinfo, edge_traffics, node_traffics, time)

    print("\n--- Simulation Finished ---\n")
    print(f"Total Time Waste: {total_time_wasted:10.2f}")



    return history