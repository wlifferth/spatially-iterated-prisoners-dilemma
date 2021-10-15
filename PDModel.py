from abc import abstractclassmethod
from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
from mesa.batchrunner import BatchRunner
import abc
import random

from collections import deque, defaultdict

DEFECT = 'defect'
COOPERATE = 'cooperate'

PAYOFF_MATRIX = {
  (DEFECT, DEFECT): (1, 1),
  (COOPERATE, DEFECT): (0, 10),
  (DEFECT, COOPERATE): (10, 0),
  (COOPERATE, COOPERATE): (6, 6),
}

class Strategy:
  def __init__(self, player):
    self.player = PDAgent

  @abc.abstractclassmethod
  def play(self, opponent_id):
    pass

class AlwaysDefect(Strategy):
  color = (1, 0, 0)
  name = 'AlwaysDefect'
  abbreviation = 'AD'
  def play(
    player,
    opponent):
    return DEFECT

class AlwaysCooperate(Strategy):
  color = (0, 1, 0)
  name = 'AlwaysCooperate'
  abbreviation = 'AC'
  def play(
    player,
    opponent):
    return COOPERATE

class FiftyFifty(Strategy):
  color = (0.1, 0.1, 1)
  name = 'FiftyFifty'
  abbreviation = 'FF'
  def play(
    player,
    opponent):
    return random.choice([COOPERATE, DEFECT])

class FavorCooperate(Strategy):
  color = (0, 0.7, 0.7)
  name = 'FavorCooperate'
  abbreviation = 'FC'
  def play(
    player,
    opponent):
    if random.random() > 0.1:
      return COOPERATE
    else:
      return DEFECT

class FavorDefect(Strategy):
  color = (0.7, 0, 0.7)
  name = 'FavorDefect'
  abbreviation = 'FD'
  def play(
    player,
    opponent):
    if random.random() > 0.1:
      return DEFECT
    else:
      return COOPERATE

class TitForTat(Strategy):
  color = (1, .6, 0.5)
  name = 'TitForTat'
  abbreviation = 'TT'
  def __init__(self, player):
    self.player = player
  def play(
    self,
    opponent):
    if self.player.history and opponent.id == self.player.history[-1][0]:
      return self.player.history[-1][2]
    else:
      return COOPERATE

class LoseShift(Strategy):
  color = (1, 0.6, 0.6)
  name = 'LoseShift'
  abbreviation = 'LS'
  def __init__(self, player):
    self.player = player
    self.cooperate = True
  def play(
    self,
    opponent
  ):
    lost_last_game = self.player.history and PAYOFF_MATRIX[self.player.history[-1][1],self.player.history[-1][2]][0] <= 1
    if lost_last_game:
      self.cooperate = not self.cooperate

    if self.cooperate:
      return COOPERATE
    else:
      return DEFECT


class PDAgent(Agent):
  """An agent with fixed initial wealth."""
  def __init__(self, id, model, strategy):
    super().__init__(id, model)
    self.id = id
    self.epoch_winnings = 1
    self.history = deque(maxlen=3)
    self.strategy = strategy(self)

  def step(self):
    neighborhood = self.model.grid.get_neighborhood(
      self.pos,
      moore=True,
      include_center=False
    )
    neighbors = self.model.grid.get_cell_list_contents(neighborhood)
    if self.model.play_phase:
      for neighbor in neighbors:
        self.play_round(neighbor)
    else:
      best_strategy = self.strategy
      max_winnings = self.epoch_winnings
      for neighbor in neighbors:
        if neighbor.epoch_winnings > max_winnings:
          max_winnings = neighbor.epoch_winnings
          best_strategy = neighbor.strategy
      self.strategy = best_strategy
      # Reset epoch_winnings for next round
      self.epoch_winnings = 0

  def play_round(self, opponent):
    for i in range(self.model.games_per_round):
      self_action = self.strategy.play(opponent)
      opponent_action = opponent.strategy.play(self)
      if self_action == DEFECT:
        self.model.epoch_compete_count += 1
      else: 
        self.model.epoch_cooperate_count += 1
      if opponent_action == DEFECT:
        self.model.epoch_compete_count += 1
      else: 
        self.model.epoch_cooperate_count += 1
      self_payoff, opponent_payoff = PAYOFF_MATRIX[(self_action, opponent_action)]
      self.epoch_winnings += self_payoff
      opponent.epoch_winnings += opponent_payoff
      self.history.append((opponent.id, self_action, opponent_action))
      opponent.history.append((self.id, opponent_action, self_action))

equal_statics = [(AlwaysCooperate, 1), (AlwaysDefect, 1), (LoseShift, 5), (TitForTat, 5)]

def CooperationRatio(model):
  return model.epoch_cooperate_count / (model.epoch_cooperate_count + model.epoch_compete_count)

strategies = [
    AlwaysCooperate,
    AlwaysDefect,
    FavorCooperate,
    FavorDefect,
    TitForTat,
    LoseShift,
]

def get_strategy_by_name(name):
  for strategy in strategies:
    if strategy.name == name:
      return strategy

class PDModel(Model):
  """A model with some number of agents."""
  def __init__(self, width, height, games_per_round=10, **kwargs):
    self.num_agents = width * height
    self.games_per_round = games_per_round
    self.grid = MultiGrid(width, height, True)
    self.schedule = RandomActivation(self)
    self.running = True
    self.play_phase = True
    self.epoch_compete_count = 0
    self.epoch_cooperate_count = 0
    strategies = []
    weights = []
    for strategy_name in kwargs:
      strategy = get_strategy_by_name(strategy_name)
      if strategy is not None:
        strategies.append(strategy)
        weights.append(kwargs[strategy_name])
    # Create agents
    for i, row in enumerate(self.grid.grid):
      for j, column in enumerate(row):
        agent_id = (i * self.grid.width) + j
        agent = PDAgent(
          agent_id,
          self,
          strategy=random.choices(
          strategies,
          weights=weights
          )[0]
        )
        self.schedule.add(agent)
        self.grid.place_agent(agent, (i, j))
    model_reporters = {
        'CooperationRatio': CooperationRatio}
    model_reporters.update({
          strategy.name: strategy.name for strategy in strategies
        })
    self.datacollector = DataCollector(
      model_reporters=model_reporters
    )
    print(self.datacollector.model_reporters)

  def get_strategy_counts(self):
    counts = defaultdict(lambda: 0)
    for agent in self.schedule.agents:
      counts[agent.strategy.name] += 1
    print(counts)
    for strategy_name, count in counts.items():
      self.__setattr__(strategy_name, count)

  def step(self):
    """Advance the model by one step."""
    self.play_phase = True
    self.schedule.step()
    # Toggle play_phase so every other phase is a learn phase
    if self.play_phase:
      self.datacollector.collect(self)
      self.epoch_compete_count = 0
      self.epoch_cooperate_count = 0
    self.play_phase = False
    self.schedule.step()
    self.get_strategy_counts()