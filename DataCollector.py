
import time
from HelperClasses import FPSCounter
from threading import Thread

class DataCollector():
	def __init__(self, game, camera, settings):
		self.game = game
		self.camera = camera
		self.settings = settings

		self._stopped = True
		self._lastCheck = 0

		self.reset()

	def reset(self):
		self.score = [0,0]
		self.videoFrames = {}
		self.gameData = GameData()

	def start(self):
		if self._stopped:
			self.reset()

			self._stopped = False
			Thread(target=self._collectingData, args=()).start()
			print("Collecting data started.")

	def stop(self):
		self._stopped = True
		self._storeClips()
		print("Collecting data stopped.")
	
	def _collectingData(self):
		while True:
			gameTime = self.game.gameTime

			self._lastCheck = time.time()
			# -----------------------------

			self.videoFrames[gameTime] = self.camera.frame.copy()
			self._checkScore(gameTime)
			# print("Frame collected")



			

			# -----------------------------
			sleepTime = 1/10 - (time.time() - self._lastCheck)
			if sleepTime > 0:
				time.sleep(sleepTime)

			if self._stopped:				
				return

	def _checkScore(self, gameTime):
		score = self.game.score.copy()
		if not self.score == score: 
			self.score = score
			self.gameData.goals[gameTime] = score	

	def _storeClips(self):
		for key in self.gameData.goals:
			self.gameData.clips[key] = [self.videoFrames[key]]


class GameData():
	def __init__(self):
		self.clips = {}
		self.goals = {}
		self.aiTopSpeed = {}
		self.humanTopSpeed = {}



		