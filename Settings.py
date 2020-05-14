import numpy as np
try:
    import cPickle as pickle
except ModuleNotFoundError:
    import pickle

class Settings():
	def __init__(self, pathToSettings = ""):
		self.path = pathToSettings
		self.camera = {}	
		self.motors = {}	
		self.game = {}	

		self.resetDefaultSettings()
		self.loadSettings()
		# print(self.camera["fieldCorners"])

	def resetDefaultSettings(self):
		self.resetCameraSettings()
		self.resetMotorsSettings()
		self.resetGameSettings()
	
	def resetCameraSettings(self):
		self.camera["fps"] = 80
		self.camera["resolution"] = (320, 192)
		self.camera["fieldCorners"] = np.float32([[0, 0], [1, 0], [1, 1], [0, 1]])
		self.camera["colorToDetect"] = np.uint8([0, 255, 120])
		self.camera["intervals"] = [30, 140, 140]
		self.camera["lowerLimits"] = np.uint8([165, 255-140, 0])
		self.camera["upperLimits"] = np.uint8([15, 255, 120+140])
		self.camera["whiteBalance"] = [1.5, 1.5]
		self.camera["filterConstants"] = [8, 2.2, 1.2]
		self.camera["limitPuckRadius"] = 10

	def resetMotorsSettings(self):
		self.motors["communicationFrequency"] = 200
		self.motors["velocity"] = 3000
		self.motors["acceleration"] = 30000
		self.motors["deceleration"] = 100000
		# self.motors["pGain"] = 21		

	def resetGameSettings(self):
		self.game["maxTime"] = 180
		self.game["maxScore"] = 5
		self.game["applyMaxScore"] = True
		self.game["applyMaxTime"] = False
		self.game["difficulty"] = 3
		self.game["strategy"] = 3
		self.game["robotSpeed"] = 3
		self.game["frequency"] = 270

	def saveSettings(self):
		with open(self.path, 'wb') as settingsFile:
			pickle.dump(self, settingsFile)	
			# print(self.game["difficulty"])
			
			# print(self.camera["fieldCorners"])

	def loadSettings(self):
		try:
			with open(self.path, 'rb') as settingsFile:
				settings = pickle.load(settingsFile)
				
			self.camera = settings.camera
			self.motors = settings.motors
			self.game = settings.game
			print("Settings loaded")
			print(self.game["difficulty"])
			# print(self.camera["fieldCorners"])
		except:
			self.saveSettings()

	def copy(self):
		newInstance = Settings(self.path)
		newInstance.camera = self.camera.copy()
		newInstance.motors = self.motors.copy()
		newInstance.game = self.game.copy()
		return newInstance