from mesa.visualization.UserParam import UserSettableParameter
from mesa.visualization.modules import CanvasGrid, ChartModule
from mesa.visualization.ModularVisualization import ModularServer

import PDModel

def render_color(rgb_color_tuple):
    return f'rgb({rgb_color_tuple[0] * 255},{rgb_color_tuple[1] * 255},{rgb_color_tuple[2] * 255})'

def agent_portrayal(agent):
    portrayal = {"Shape": "rect",
                 "Filled": "true",
                 "w": 1,
                 "h": 1,
                 "Color": render_color(agent.strategy.color),
                 "Layer": 1,
                 "text": agent.strategy.abbreviation}
    return portrayal

height = 20
width  = 30

grid = CanvasGrid(agent_portrayal, width, height, 700, 500)

cooperation_chart = ChartModule([{
  'Label': 'CooperationRatio',
  'Color': 'Black'}],
  data_collector_name='datacollector')

strategies_chart = ChartModule([{
  'Label': strategy.name,
  'Color': render_color(strategy.color),
  } for strategy in PDModel.strategies],
  data_collector_name='datacollector')

params = {
    "width":width,
    "height":height,
}
for strategy in PDModel.strategies:
     params[strategy.name] = UserSettableParameter('slider', strategy.name, value=1, min_value=0, max_value=10, step=1)

server = ModularServer(PDModel.PDModel,
                       [grid, cooperation_chart, strategies_chart],
                       "Spatially Iterated Prisoner's Dilemma",
                       params)
server.port = 8521 # The default
server.launch()