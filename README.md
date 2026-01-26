# Optimal control of traffic signals using quantum annealing

## 文献情報

タイトル: Optimal control of traffic signals using quantum annealing

著者: Hasham Hussaln, Muhammad Bln Javald 他

書誌情報: https://doi.org/10.1007/s11128-020-02815-1

参考: https://github.com/mbinjavaid/traffic_signals_qubo (著者によるもの)


## 実装

主なシミュレーション実装部は`simulator.py`に記述されている

### simulator.py



### graph.py

マップ情報のグラフ構造を保持するためのクラスが記述されている

`MapInfo`クラス, `Node`クラス(交差点に対応), `Edge`(道路に対応)クラスが与えられる. 

#### Edge

結ぶノード2点のid(`start_id`<`end_id`)と, 
道路長(`length`), 
制限速度(`speed_limit`)を所持する

#### Node 

`__init__`にて, 格子状構造の`x`, `y`を要求し, それに応じて東西南北関係を認識する. 

`getId()`にて自身のノードidを取得可能である. この実装は, 親のMapInfoに依存する.
MapInfoに改変が入るとこのメソッドの戻り値は保証を失う. 

`north_id()`, `south_id()`などで, 各方角に隣接するノードのIdを取得可能. 
また, `north_node()`などで各方向に隣接する`Node`を獲得可能

#### MapInfo

`__init__`にて, 格子状マップのサイズ`width, height`を要求し, それに応じて必要ノードとエッジを自動生成する. 
各エッジはノードの東西南北の関係のみに生成される. 

`width()`, `height()`で最初に設定したマップサイズを取得可能である. 

`getNode(nodeid)`で`nodeid`で指定した`Node`を取得可能である

`getEdgeBetween(id1, id2)`で, ノード`id1`, ノード`id2`が隣接している場合に限りしかるべき`Edge`を返す(非隣接の場合`None`が返される). `id1`と`id2`の大小関係は不問である. 

`globalMaxSpeed()`でマップ内の最高の制限速度を返す. これは`__init__`にて計算されたものをそのまま返すため, `__init__`後に`Edge`を直接操作した場合は動作の保証がされない. 



### traffic.py

### solving/solve_sa.py


