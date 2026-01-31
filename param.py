from dataclasses import dataclass, field
from typing import List

@dataclass
class SimulationParams:
    lambda1: float=1
    """Q1 の係数"""
    lambda2: float=60
    """Q2 の係数"""
    lambda2t: float=0.3
    """Q2 の内部項係数 (プライム付きlambda_3)"""
    lambda2f: float=0.7
    """Q2 の内部項係数 (プライムなしlambda_3)"""
    lambda3: float=1e6
    """Q3 の内部項係数 (論文内lambda_4)"""
    edge_length: float=1000
    """道路長"""
    edge_speed_limit_array: List[float] = field(
        default_factory=lambda: [11.0, 17.0, 22.0, 28.0]
    )
    """道路制限速度. このリストからランダムにchoiceされる"""
    signal_update_span: int=10
    """信号の更新ステップ数"""
    simulation_time: int=100
    """シミュレーション時間設定"""
    show_mode_change: bool = False
    """SA実行後にモード変化をprintするか?"""
    car_count=100
    """シミュレーション内の車の数"""
