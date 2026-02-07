from graph import *
from simulator import simulation, simulation_init
import json
import os

from param import SimulationParams, Coefficient, MapGenerationParam

def main(simparams: SimulationParams, coefficient: Coefficient, mapgenparam: MapGenerationParam):
    
    mapinfo, edge_traffics, node_traffics = simulation_init(mapgenparam, width=6, height=6)
    

    history = simulation(simparams, coefficient , mapinfo, edge_traffics, node_traffics)
    savelog(history)
    return history 



def savelog(history):
    """
    `history`のJSON出力
    """
    os.makedirs("results", exist_ok=True)
    with open("results/simulation_log.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)
    print("Log saved to results/simulation_log.json")



if __name__ == "__main__":
    simparams = SimulationParams()
    coefficient=Coefficient()
    mapgenparam=MapGenerationParam()
    main(simparams, coefficient, mapgenparam)




