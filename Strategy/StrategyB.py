from Strategy.BaseStrategy import BaseStrategy
from Strategy.StrategyStructs import *
from pygame.math import Vector2
from numpy import sign
from Constants import *

class StrategyB(BaseStrategy):
	def __init__(self):
		super().__init__()
		self.actionState = 0
		self.lineToGoal = Line()
		

	def _process(self):
		self.getPredictedPuckPosition(self.striker.desiredPosition)

		if self.isPuckBehingStriker():
			self.defendGoalLastLine()
		elif self.predictedPosition.x < STRIKER_AREA_WIDTH and not (self.willBounce and self.puck.state == ACURATE):			
			self.setDesiredPosition(self.predictedPosition)
		elif self.shouldIntercept():
			self.defendTrajectory()
		else:
			self.defendGoalLastLine()

		self.limitMovement()


		
		

		