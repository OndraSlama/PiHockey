from Constants import *
from Strategy import StrategyA, StrategyB, StrategyC, StrategyD
from HelperClasses import FPSCounter, Repeater
from pygame.math import Vector2
from threading import Thread
import time

class Game():
	def __init__(self, camera, settings):
		self.settings = settings
		self.camera = camera
		self.setStrategy()

		self.strikersPosition = [Vector2(0,0), Vector2(0,0)]
		self.puckPosition = Vector2(0,0)

		self.frequencyCounter = FPSCounter(60)
		self.infoRepeater = Repeater(self.printToConsole, 0.2)
		self.gameStartedAt = 0
		self.lastStepAt = 0
		self.paused = False
		self.stopped = True

		self.reset()

	def reset(self):
		self.gameTime = 0
		self.score = [0, 0]
		self.gameDone = False
		self.winner = -1
		self.paused = False

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

	def setStriker(self, pos):
		if isinstance(pos, Vector2):
			self.strikersPosition[0] = Vector2(pos)
		else:
			self.strikersPosition[0] = Vector2(*pos)

	def setOpponentStriker(self, pos):
		if isinstance(pos, Vector2):
			self.strikersPosition[1] = Vector2(pos)
		else:
			self.strikersPosition[1] = Vector2(*pos)

	def getDesiredPosition(self):
		return (round(self.strategy.striker.desiredPosition.x), round(self.strategy.striker.desiredPosition.y))

	def getDesiredVelocity(self):
		return (round(self.strategy.striker.desiredVelocity.x), round(self.strategy.striker.desiredVelocity.y))

	def update(self):
		print("Game started.")
		while True:
			stepTime = time.time() - self.lastStepAt
			self.lastStepAt = time.time()

			self.step(stepTime)
			self.checkEnd()

			sleepTime = 1/self.settings["frequency"] - (time.time() - self.lastStepAt)
			if sleepTime > 0:
				time.sleep(sleepTime)

			self.gameTime += time.time() - self.lastStepAt

			if self.stopped:				
				return

	def step(self, stepTime):
		if self.camera.newPosition:
			self.strategy.cameraInput(self.camera.getPuckPosition())
			self.strategy.setStriker(self.strikersPosition[0])
			self.strategy.setOpponentStriker(self.strikersPosition[1])
		try:
			self.strategy.process(stepTime)	
		except:
			print("Error during strategy evaluation.")
		self.frequencyCounter.tick()

	def goal(self, side):
		self.score[side] += 1

	def checkEnd(self):
		if (self.settings["applyMaxScore"] and (max(self.score) >= self.settings["maxScore"])) or (self.settings["applyMaxTime"] and (self.gameTime >= self.settings["maxTime"])):
			self.gameDone = True
			if self.score[0] == self.score[1]:
				self.winner = 2
			else:
				self.winner = self.score.index(max(self.score))

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

	def stop(self):
		self.frequencyCounter.resetState()
		self.frequencyCounter.stop()
		self.stopped = True
		self.paused = False
		self.gameDone = False
		self.gameTime = 0
		# self.reset()

	def printToConsole(self):
		print("Frequency:")
		print(self.frequencyCounter)
		print("Desired position: " + str(self.strategy.striker.desiredPosition))
