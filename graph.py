from __future__ import annotations
import random



class MapInfo:

    """
        マップ情報クラス
    """
    def __init__(self, width: int, height: int):
        """
        Args: 
            width: マップ横幅
            height: マップ縦幅
        """
        self._mapwidth=width
        self._mapheight=height
        self._nodes = [
            Node(x=i % width, y=i // width, mapref=self)
            for i in range(width * height)
        ]

        self._global_max_speed=0.0

        self._edges = {}  # key: (start_id, end_id), value: Edge

        for node in self._nodes:
            node_id = node.getId()
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:  # 西・東・北・南
                nx = (node._x + dx) % self._mapwidth
                ny = (node._y + dy) % self._mapheight
                neighbor_id = nx + ny * self._mapwidth

                # 重複登録を避けるため、(小さいID, 大きいID) の順で登録
                key = tuple(sorted((node_id, neighbor_id)))
                if key not in self._edges:
                    # 道路にランダムに制限速度を付す
                    # ここを偏向することで各エッジの制限速度を変更可能
                    speed=random.choice([11.0, 17.0, 22.0, 28.0])
                    
                    # マップ内最高速度の記録
                    if self._global_max_speed<speed: 
                        self._global_max_speed = speed
                    
                    # Edgeオブジェクト生成
                    self._edges[key] = Edge(
                        start_id=key[0],
                        end_id=key[1],
                        # 道路長設定
                        length=1000.0,
                        # 制限速度設定        
                        speed_limit=speed    
                    )


    
    def width(self):
        """
            マップ幅を返す
        """
        return self._mapwidth
    
    def height(self):
        """
            マップの高さを返す
        """
        return self._mapheight
    
    def getNode(self, nodeid:int) -> Node: 
        """
            nodeidで指定したノードオブジェクトを返す
        """
        return self._nodes[nodeid]
    
    def getEdgeBetween(self, id1: int, id2: int)->Edge|None:
        """
        2つのノードIDが隣接していれば、その間のEdgeを返す。
        隣接していなければ None を返す。
        """
        key = tuple(sorted((id1, id2)))
        return self._edges.get(key)
    
    def globalMaxSpeed(self) -> float:
        """
        マップ内における最高の制限速度を返す.
        """
        return self._global_max_speed
    




class Edge:
    """
        交差点間をつなぐエッジに関する情報クラス

        start_id (int): 始点ノードid
        
        end_id (int): 終点ノードid
        
        length (float): 区間の長さ[m]
        
        speed_limit (float): 制限速度[m/s]
    """
    def __init__(self, start_id: int, end_id: int, length: float, speed_limit: float):
        self.start_id = start_id
        self.end_id = end_id
        self.length = length
        self.speed_limit = speed_limit

class Node:
    """
        交差点のノードを表すクラス

        x: 格子状構造のxインデックス

        y: 格子状構造のyインデックス

        mapref: 親の`MapInfo`クラス
    """
    def __init__(self, x: int, y: int, mapref: MapInfo):
        self._x=x
        self._y=y
        self._mapref=mapref


    def getId(self):
        """
        ノードIdを返す. 
        """
        return self._x+self._y*self._mapref.width()

    def _wrap(self, x, y):
        w, h = self._mapref.width(), self._mapref.height()
        return x % w, y % h

    def north_id(self):
        x, y = self._wrap(self._x, self._y - 1)
        return x + y * self._mapref.width()

    def south_id(self):
        x, y = self._wrap(self._x, self._y + 1)
        return x + y * self._mapref.width()

    def west_id(self):
        x, y = self._wrap(self._x - 1, self._y)
        return x + y * self._mapref.width()

    def east_id(self):
        x, y = self._wrap(self._x + 1, self._y)
        return x + y * self._mapref.width()

    def north_node(self):
        return self._mapref.getNode(self.north_id())

    def south_node(self):
        return self._mapref.getNode(self.south_id())

    def west_node(self):
        return self._mapref.getNode(self.west_id())

    def east_node(self):
        return self._mapref.getNode(self.east_id())