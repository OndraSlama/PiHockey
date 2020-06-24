# ****************************************************************************** #
# Author: Ondrej Slama
# -------------------

# Zdrojovy kod vytvoreny v ramci projektu robotickeho vzdusneho hokeje - diplomova prace
#  na VUT FSI ustavu automatizace a informatiky v Brne.

# Source code created as a part of robotic air hockey table project - Diploma thesis
# at BUT FME institute of automation and computer sience.

# ****************************************************************************** #
from Constants import *
from Strategy import StrategyA, StrategyB, StrategyC, StrategyD
from UniTools import FPSCounter, Repeater
from pygame.math import Vector2
from threading import Thread
import time

class Game():
	def __init__(self, camera, settings):
		self.settings = settings
		self.camera = camera
		self.setStrategy()

		self.strikersPosition = [Vector2(0,0), Vector2(0,0)]
		self.strikersVelocity = [Vector2(0,0), Vector2(0,0)]
		self.puckPosition = Vector2(0,0)

		self.frequencyCounter = FPSCounter(60)
		self.infoRepeater = Repeater(self.printToConsole, 0.2)
		self.gameStartedAt = 0
		self.lastStepAt = 0
		self.lastGoalAt = 0		
		self.clearRobotGoal = 0
		self.paused = False
		self.stopped = True
		self.waitForPuck = True

		self.reset()

	def reset(self):
		self.gameTime = 0
		self.score = [0, 0]
		self.lastGoalOnSide = -1
		self.gameDone = False
		self.winner = -1
		self.paused = False

		# Statistic data
		self.onSide = 0
		self.maxShotSpeed = [0, 0]
		self.puckControl = [0, 0]
		self.shotOnGoals = [0, 0]
		self.lostPucks = [0, 0]

	def setStrategy(self):
		if self.settings["strategy"] == 0:
			self.strategy = StrategyA.StrategyA()
		if self.settings["strategy"] == 1:
			self.strategy = StrategyB.StrategyB()
		if self.settings["strategy"] == 2:
			self.strategy = StrategyC.StrategyC()
		if self.settings["strategy"] == 3:
			self.strategy = StrategyD.StrategyD()
		
		print(self.strategy.description)

	def setStriker(self, pos, vel = None):
		if isinstance(pos, Vector2):
			self.strikersPosition[0] = Vector2(pos)
		else:
			self.strikersPosition[0] = Vector2(*pos)

		if vel is not None:
			if isinstance(vel, Vector2):
				self.strikersVelocity[0] = Vector2(vel)
			else:
				self.strikersVelocity[0] = Vector2(*vel)

	def setOpponentStriker(self, pos, vel = None):
		if isinstance(pos, Vector2):
			self.strikersPosition[1] = Vector2(pos)
		else:
			self.strikersPosition[1] = Vector2(*pos)

		if vel is not None:
			if isinstance(vel, Vector2):
				self.strikersVelocity[1] = Vector2(vel)
			else:
				self.strikersVelocity[1] = Vector2(*vel)

	def getDesiredPosition(self):
		return (round(self.strategy.striker.desiredPosition.x), round(self.strategy.striker.desiredPosition.y))

	def getDesiredVelocity(self):
		return (round(self.strategy.striker.desiredVelocity.x), round(self.strategy.striker.desiredVelocity.y))

	def update(self):
		print("Game started.")
		while True:
			stepTime = time.time() - self.lastStepAt

			if not self.waitForPuck:
				self.gameTime += time.time() - self.lastStepAt

			self.lastStepAt = time.time()

			self.step(stepTime)
			self.checkData(stepTime)
			self.checkEnd()

			sleepTime = 1/self.settings["frequency"] - (time.time() - self.lastStepAt)
			if sleepTime > 0:
				time.sleep(sleepTime)

			if self.stopped:				
				return

	def step(self, stepTime):
		if self.camera.newPosition:
			pos = self.camera.getPuckPosition()
			if pos.x > STRIKER_RADIUS * 1.5:
				self.waitForPuck = False
			self.strategy.cameraInput(pos)

		self.strategy.setStriker(self.strikersPosition[0], self.strikersVelocity[0])
		self.strategy.setOpponentStriker(self.strikersPosition[1], self.strikersVelocity[1])
		if not self.waitForPuck:
			try:
				self.strategy.process(stepTime)	
			except Exception as e:
				# print("Strategy: " + str(e))
				pass
			self.frequencyCounter.tick()

	def goal(self, side):
		if time.time() - self.lastGoalAt > 2 and not self.waitForPuck:
			self.lastGoalAt = time.time()
			self.lastGoalOnSide = side
			self.score[side] += 1
			self.onSide = 0
			self.waitForPuck = True

	def checkEnd(self):
		if (self.settings["applyMaxScore"] and (max(self.score) >= self.settings["maxScore"])) or (self.settings["applyMaxTime"] and (self.gameTime >= self.settings["maxTime"])):
			self.gameDone = True
			if self.score[0] == self.score[1]:
				self.winner = 2
			else:
				self.winner = self.score.index(max(self.score))

	def checkData(self, stepTime):
		if not self.waitForPuck:
			puck = self.strategy.puck
			puckPos = puck.position
			if puckPos.x > FIELD_WIDTH - (STRIKER_AREA_WIDTH) and not self.onSide == -1:
				self.onSide = -1
				self.lostPucks[1] += 1
				self.checkShot(1)
				
			elif puckPos.x < STRIKER_AREA_WIDTH and not self.onSide == 1:
				self.onSide = 1
				self.lostPucks[0] += 1
				self.checkShot(-1)

			elif abs(puckPos.x - FIELD_WIDTH/2) < (FIELD_WIDTH - 2*(STRIKER_AREA_WIDTH))/2:
				self.onSide = 0

			if not self.onSide == 0:
				self.puckControl[max(0, self.onSide)] += stepTime

	def checkShot(self, dir):
		print("Puck Control:", self.puckControl)

		puck = self.strategy.puck
		if puck.speedMagnitude > 700 and abs(puck.vector.y) < .9:
			# print("good shot, dir:", dir)
			if len(puck.trajectory) > 0 and abs(puck.trajectory[-1].end.y) < GOAL_SPAN/2 * .9:
				self.shotOnGoals[max(0, dir)] += 1
				print("Shots on goal: ", self.shotOnGoals)
			if self.maxShotSpeed[max(0, dir)] < puck.speedMagnitude < 10000:
				self.maxShotSpeed[max(0, dir)] = puck.speedMagnitude
				print("Max shot speed:", self.maxShotSpeed)

	def start(self):
		if self.stopped:
			self.gameStartedAt = time.time()
			self.lastStepAt = time.time()
			self.frequencyCounter.start()
			# self.infoRepeater.start()
			self.stopped = False
			if not self.paused: self.reset()
			self.paused = False
			
			Thread(target=self.update, args=()).start()
		return self
	
	def resume(self):
		if self.stopped:
			self.frequencyCounter.start()
			self.lastStepAt = time.time()
			# self.infoRepeater.start()
			self.stopped = False
			Thread(target=self.update, args=()).start()

	def pause(self):
		# self.infoRepeater.stop()
		self.paused = True
		self.stopped = True
		self.onSide = 0

	def stop(self):
		self.frequencyCounter.resetState()
		self.frequencyCounter.stop()
		self.stopped = True
		self.paused = False
		self.gameDone = False
		# self.gameTime = 0
		# self.reset()

	def printToConsole(self):
		print("Frequency:")
		print(self.frequencyCounter)
		print("Desired position: " + str(self.strategy.striker.desiredPosition))
