from graph import *
from simulator import simulation

from param import SimulationParams

def main(params: SimulationParams):
    print("Running simulation with:")
    simulation(params)





if __name__ == "__main__":
    params = SimulationParams()   # ← 引数なしでOK
    main(params)




