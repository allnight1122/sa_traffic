# SA挙動メモ

QUBOに投げる$x$のインデックスは
$ i \times M+j $($M$はモードの種類)と定義する. 

## Q1

$\lambda_1$を`LAMBDA1`で与えている. 

$C_{ij}$は`get_flowable_count(i,j)`にて獲得可能. ただし, $i$は`traffic_node`で, $j$は1-6の`int`で与える. 

## Q2

$\lambda_2$を`LAMBDA2`で与えている. 
$\lambda_3, \lambda_3^\prime$に関しては, `LAMBDA2F, LAMBDA2T`で与える.

$C_{ij}$は`get_flowable_count(i,j)`にて獲得可能. ただし, $i$は`traffic_node`で, $j$は1-6の`int`で与える. 

$x_{ij}, x_{a' a}$の積の形であるため, 
$k_1=(i \times $`MODEKIND`$ + j -1)$, $k_2=(a' \times $`MODEKIND`$ + a -1)$について, 
$Q_{k_1, k_2} += -\lambda_2 \cdot C_{ij} \tau_{i a'} \cdot \lambda_3 \cdot C_{a' a}$ を入れる. 
dimodなどのSA solverの仕様の関係上, `val/2`を`[k1, k2]`と`[k2, k1]`に分けて与える. 

## Q3

$$ Q_3 =\lambda \sum_i (\sum_j x_{ij} -1)^2  $$

かっこを展開して,
$$(\sum_j x_{ij} -1)^2=\sum_j x^2_{ij} +\sum_{j \neq k} x_{ij}x_{ik}-2\sum_j x_{ij} $$
したがって, 
$$(\sum_j x_{ij} -1)^2=\sum_{j \neq k} x_{ij}x_{ik}-\sum_j x_{ij} $$
QUBO行列は, 同一$i$について 
$j \neq k$で, $\lambda$, 
$j = k$で, $-\lambda$, 