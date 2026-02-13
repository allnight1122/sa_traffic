from dataclasses import dataclass, field
from typing import List
from enum import Enum


UPDATE_STRATEGY_QUBO = 0
"""`SimulationParams.update_strategy`にて, quboによる最適化を選択する定数"""
UPDATE_STRATEGY_FIXED = 1
"""`SimulationParams.update_strategy`にて, 固定サイクルによる信号更新を選択する定数 (モードを+1ずつ)"""
UPDATE_STRATEGY_RANDOM = 2
"""`SimulationParams.update_strategy`にて, 完全ランダムによる信号更新を選択する定数 """
INITAL_SIGNAL_RANDOM = 0
"""`MapGenerationParam.inital_signal`にて, 完全ランダムな信号初期化を要求する定数"""


@dataclass
class Coefficient:
    lambda1: float=1.0
    """Q1 の係数"""
    lambda2: float=60.0
    """Q2 の係数"""
    lambda2t: float=0.3
    """Q2 の内部項係数 (プライム付きlambda_3)"""
    lambda2f: float=0.7
    """Q2 の内部項係数 (プライムなしlambda_3)"""
    lambda3: float=1e6
    """Q3 の内部項係数 (論文内lambda_4)"""
    tau_threshold:float = 2.0
    """元論文$t mod T approx 0$を判定するための許容範囲    """
    num_reads = 10
    """サンプリング数"""

@dataclass
class MapGenerationParam:
    edge_length: float=1000
    """道路長"""
    edge_speed_limit_array: List[float] = field(
        default_factory=lambda: [11.0, 17.0, 22.0, 28.0]
    )
    """道路制限速度. このリストからランダムにchoiceされる"""
    car_count: int=100
    """シミュレーション内の車の数"""
    inital_signal: int = INITAL_SIGNAL_RANDOM

@dataclass
class SimulationParams:
    update_strategy: int = UPDATE_STRATEGY_QUBO
    """
    信号更新の方針

    - 0: quboによる最適化
    - 1: 固定サイクルによる信号更新
    - 2: 完全ランダムによる信号更新
    """
    signal_update_span: int=10
    """信号の更新ステップ数"""
    simulation_time: int=100
    """シミュレーション時間設定"""
    show_mode_change: bool = False
    """SA実行後にモード変化をprintするか?"""



