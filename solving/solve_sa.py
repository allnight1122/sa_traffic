from graph import *
from traffic import *
from typing import Dict, Tuple, List, Any
import numpy as np
import dimod
from param import Coefficient, SAMPLER_DIMOD, SAMPLER_NEAL
import neal

MODE_KIND=6
"""
モードの種類の数を示す定数
"""


def get_flowable_count(node_traffic: NodeTraffic, mode: int):
    """
    指定された`node_traffics`にいる車のうち `mode` になったときに流出可能な車の合計台数を返す. 

    論文中の$C_{i j}$に対応する. 
    """

    allowed_flow = MODE_FLOW.get(mode, {})
    total_count = 0
    
    # ノード内の各進入方向の待ち状況をカウント
    for direction, allowed_turns in allowed_flow.items():
        if direction not in node_traffic.queues:
            continue
            
        # その方向のキューの中身（"straight", "right" など）を集計
        counts = Counter(node_traffic.queues[direction])
        
        # 許可されている各動作について、待ち台数を加算
        for turn_type in allowed_turns:
            total_count += counts.get(turn_type, 0)
            
    return total_count

def q1( edge_traffics: Dict, node_traffics: Dict, mapinfo: MapInfo, lambda_1:float) -> np.array:
    matrix_length=mapinfo.width()*mapinfo.height()*MODE_KIND
    q_matrix=np.zeros((matrix_length, matrix_length), dtype=float)

    for node_id in range(mapinfo.width()*mapinfo.height()):
        if node_id not in node_traffics:
            continue
        
        # 調査対象のノードの交通状況を参照するよ
        node_traffic=node_traffics[node_id]


        for j in range(MODE_KIND):
            # モードがj+1のとき(1-6)の想定をここからする
            mode = j + 1

            c_ij = get_flowable_count(node_traffic, mode)
            k=node_id*MODE_KIND+j
            q_matrix[k,k]=-lambda_1*c_ij

    return q_matrix


MODE_RELATIONS = {
    1: [("north", 1, False), ("north", 2, True), ("south", 1, False), ("south", 3, True)],
    2: [("north", 1, False), ("north", 2, True), ("east" , 4, False), ("east" , 5, True)],
    3: [("south", 1, False), ("south", 3, True), ("west" , 4, False), ("west" , 6, True)],
    4: [("east" , 4, False), ("east" , 5, True), ("west" , 4, False), ("west" , 6, True)],
    5: [("east" , 4, False), ("east" , 5, True), ("south", 1, False), ("south", 3, True)],
    6: [("west" , 4, False), ("west" , 6, True), ("north", 1, False), ("north", 2, True)],
}
"""
元論文における, {a', b', c', d'}と{a, b, c, d}のリスト
"""



def q2(time: int, edge_traffics: Dict, node_traffics: Dict, mapinfo: MapInfo,
        lambda_2: float, lambda2t: float, lambda2f: float, tau_threshold: float) -> np.array:
    """
    Q2(論文準拠)の計算をするメソッド
    """
    matrix_length=mapinfo.width()*mapinfo.height()*MODE_KIND
    
    q_matrix=np.zeros((matrix_length, matrix_length), dtype=float)
    
    # まずは各ノードの交差点状況を取得する
    for node_id in range(mapinfo.width()*mapinfo.height()):
        node_traffic = node_traffics.get(node_id)

        if not node_traffic: continue

        current_node = mapinfo.getNode(node_id)

        # 論文中のsum_j/ 各モードに関して考察を行う
        for j_idx in range(MODE_KIND):
            # 考察対象モード(1-6)
            mode_j = j_idx + 1

            c_ij=get_flowable_count(node_traffic, mode_j)
            # おおもとのC_ijが0なら項は消去される. 
            if c_ij==0: continue 

            # そのmode_jに対応する4つのターゲット交差点(a', b', c', d')についてループする. 
            targets = MODE_RELATIONS.get(mode_j, [])

            # directionは隣接する交差点の向きに, preferred_modeはその交差点の"おすすめの"モード
            # is_primeはlambda_3かlambda_3'のどっちを使うかの議論
            for direction, preferred_mode, is_prime in targets:
                neighbor_id=None
                # 隣接ノードのid特定
                if direction=="north":
                    neighbor_id=current_node.north_id()
                elif direction=="south":
                    neighbor_id=current_node.south_id()
                elif direction=="east":
                    neighbor_id=current_node.east_id()
                elif direction=="west":
                    neighbor_id=current_node.west_id()
                    

                if neighbor_id is None: 
                    raise RuntimeError("directionがどの方角でもない実装上の致命的なエラー. どっかで矛盾発声")

                edge = mapinfo.getEdgeBetween(node_id, neighbor_id)
                if not edge: continue

                # 隣接ノードまでの移動に要する時間(元論文T)
                time_need=edge.length / edge.speed_limit
                # 元論文 t mod T計算. approx 0か判定したい
                remainder = time % time_need
                # 実質的なtauの特定
                # 結果が偽であればtau=0なので, 以降の処理を省略して次ループへ
                if not((remainder <= tau_threshold) or (abs(time_need - remainder) <= tau_threshold)): continue

                c_neighbor=get_flowable_count(node_traffics[neighbor_id], preferred_mode)
                # 重み(元論文lambda3 or lambda3')
                weighting = lambda2t if is_prime else lambda2f

                k1=node_id * MODE_KIND + (mode_j - 1)
                k2 = neighbor_id * MODE_KIND + (preferred_mode - 1)

                val = -lambda_2 * c_ij * weighting * c_neighbor

                q_matrix[k1, k2] += val/2
                q_matrix[k2, k1] += val/2









    return q_matrix

def q3(edge_traffics: Dict, node_traffics: Dict, mapinfo: MapInfo, lambda_3) -> np.array:
    matrix_length=mapinfo.width()*mapinfo.height()*MODE_KIND
    
    q_matrix=np.zeros((matrix_length, matrix_length), dtype=float)
    for i in range(mapinfo.width()*mapinfo.height()):
        start_idx=i*MODE_KIND
        end_idx=(i+1)*MODE_KIND

        for j in range(start_idx, end_idx):
            for k in range(start_idx, end_idx):
                if(j == k):
                    q_matrix[j, k]+= -lambda_3
                else: 
                    q_matrix[j, k]+= lambda_3

    return q_matrix








def solve_main(coefficient: Coefficient, time: int, edge_traffics: Dict, node_traffics: Dict, mapinfo: MapInfo) -> Dict[int, int]:
    """
    SAで解くメイン実装
    QUBO matrixの生成, dimodによるSA求解, node-mode形式の辞書オブジェクト生成までをおこない, 
    各ノードidのキーと, そのノードのモードについての辞書を返す

    Parameters
    ----------
    coefficient: Coefficient
      QUBOのための係数群
    time : int
      シミュレーション内時間
    
    

    """

    matrix_length=mapinfo.width()*mapinfo.height()*MODE_KIND

    q_matrix=np.zeros((matrix_length, matrix_length), dtype=float)

    q_matrix+=q1(edge_traffics, node_traffics, mapinfo, coefficient.lambda1)
    q_matrix+=q2(time, edge_traffics, node_traffics, mapinfo, 
                 coefficient.lambda2, coefficient.lambda2t, coefficient.lambda2f, 
                 coefficient.tau_threshold)
    q_matrix+=q3(edge_traffics, node_traffics, mapinfo, coefficient.lambda3)

    qubo_dict={}
    rows, cols=np.nonzero(q_matrix)
    for i, j in zip(rows, cols):
        qubo_dict[(int(i), int(j))]=q_matrix[i,j]
    
    if coefficient.sampler == SAMPLER_NEAL: 
        sampler = neal.SimulatedAnnealingSampler()
        sampleset = sampler.sample_qubo(qubo_dict, num_reads=coefficient.num_reads, num_sweeps=coefficient.num_sweeps)

        best_sample=sampleset.first.sample
    else: 
            
        sampler = dimod.SimulatedAnnealingSampler()
        sampleset = sampler.sample_qubo(qubo_dict, num_reads=coefficient.num_reads, num_sweeps=coefficient.num_sweeps)

        best_sample=sampleset.first.sample

    # 5. 解の形式を変換: {node_id: mode_id}
    node_mode_map = {}

    total_violations=0
    for i in range(mapinfo.width()*mapinfo.height()):
        start = i * MODE_KIND
        end = (i + 1) * MODE_KIND
        
        # 当該ノードのビット列を取得
        node_bits = [best_sample[start + m] for m in range(MODE_KIND)]
        active_indices = [m for m, val in enumerate(node_bits) if val == 1]
        num_active = len(active_indices)

        # --- コンソール出力用：制約違反のチェック ---
        if num_active != 1:
            total_violations += 1
            print(f"[SA Warning] Node {i:2d} violated one-hot constraint: "
                  f"{num_active} bits active (Indices: {active_indices})")

        # 返り値用の暫定処理 (シミュレーション継続のため)
        # 1つ以上あれば最初の1つ、0個ならデフォルトでモード1を割り当て
        if num_active >= 1:
            selected_mode = active_indices[0] + 1
        else:
            selected_mode = active_indices[0] + 1
            
        node_mode_map[i] = selected_mode

    if total_violations > 0:
        print(f"--- Summary: {total_violations}/{mapinfo.width()*mapinfo.height()} nodes had one-hot violations. ---")
    else:
        print(f"--- SA Optimization Success: All nodes satisfied one-hot constraint. ---")

    return node_mode_map

    
