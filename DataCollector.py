
import os
import time
import shutil
from HelperClasses import FPSCounter
from threading import Thread
from Constants import *
from datetime import datetime
from collections import OrderedDict
from array2gif import write_gif
import cv2
# from imgarray import save_array_img, load_array_img
from PIL import Image
import uuid
import numpy as np

try:
    import cPickle as pickle
except ModuleNotFoundError:
    import pickle

class DataCollector():
	def __init__(self, game, camera, settings, pathToRecords="GameRecordings/"):
		self.game = game
		self.camera = camera
		self.settings = settings
		self.recordsPath = pathToRecords

		self._stopped = True
		self._lastCheck = 0

		self.saving = False
		self.loading = False
		self.newData = False
		

		self.reset()

	def reset(self):
		self.videoFrames = OrderedDict()
		self.gameData = GameData()
		self.loadedGames = []

	def start(self):
		if self._stopped:
			self.reset()

			self._stopped = False
			Thread(target=self._collectingData, args=()).start()
			print("Collecting data started.")

	def discard(self):
		self._stopped = True
		self.reset()

	def stop(self):
		self._stopped = True
		self.gameData.score = self.game.score.copy()
		self._collectData()
		# self.gameData.duration = self.game.gameTime
		Thread(target=self._saveRecord, args=(self.gameData.copy(), self.videoFrames.copy())).start()
		print("Collecting data stopped.")

	def loadRecords(self):
		Thread(target=self._loadRecords, args=()).start()

	def getMatchByTimestamp(self, timestamp):
		for match in self.loadedGames:
			if match.datetime.timestamp() == timestamp:
				return match
		return None

	def getNewestMatch(self):
		newestIndex = 0
		for i in range(len(self.loadedGames)):
			if self.loadedGames[i].datetime.timestamp() > self.loadedGames[newestIndex].datetime.timestamp():
				newestIndex = i
		if len(self.loadedGames) > 0:
			return self.loadedGames[newestIndex]
		return None
	
	def _collectingData(self):
		while True:
			
			self._collectData()

			sleepTime = 1/CLIP_FRAMERATE - (time.time() - self._lastCheck)
			if sleepTime > 0:
				time.sleep(sleepTime)

			if self._stopped:				
				return

	def _collectData(self):
		gameTime = self.game.gameTime

		self._lastCheck = time.time()
		self.gameData.duration = gameTime

		self.gameData.shotOnGoals = self.game.shotOnGoals.copy()
		self.gameData.puckControl = self.game.puckControl.copy()
		try:
			self.gameData.accuracy = [self.game.shotOnGoals[i]/self.game.lostPucks[i] for i in range(2)]
		except: pass

		if self.game.maxShotSpeed[0] > self.gameData.humanTopSpeed[1]:
			self.gameData.humanTopSpeed = [gameTime, self.game.maxShotSpeed[0]]

		if self.game.maxShotSpeed[1] > self.gameData.aiTopSpeed[1]:
			self.gameData.aiTopSpeed = [gameTime, self.game.maxShotSpeed[1]]


		self._checkScore(gameTime)
		self.videoFrames[gameTime] = self.camera.frame.copy()
		# print("Frame collected")

	def _checkScore(self, gameTime):
		score = self.game.score.copy()
		if not self.gameData.score == score: 
			self.gameData.score = score.copy()
			self.gameData.goals[gameTime] = score.copy()	

	def _saveRecord(self, gameData, videoFrames):
		while self.saving:
			time.sleep(.2)
		self.saving = True

		self._storeClips(gameData, videoFrames)
		with open(self.recordsPath + "AHgame_{}_{}-{}.obj".format(gameData.datetime.strftime('%d-%m-%Y-%H-%M'), *gameData.score), 'wb') as gameRecord:
			pickle.dump(gameData, gameRecord)	

		self.saving = False
		self.loadRecords()
			

	def _storeClips(self, gameData, videoFrames):
		for key in gameData.goals:
			while not self.game.stopped:
				time.sleep(.2)
			gameData.clips[key] = self._getCLip(key, videoFrames)
		
		key = gameData.aiTopSpeed[0]
		gameData.clips[key] = self._getCLip(key, videoFrames)

		key = gameData.humanTopSpeed[0]
		gameData.clips[key] = self._getCLip(key, videoFrames)

	def _getCLip(self, gameTime, videoFrames):
		clip = []
		# rgbClip = []
		id = uuid.uuid1()
		for key in videoFrames:
			if gameTime - CLIP_LENGTH * CLIP_BEFORE_AFTER_RATIO < key < gameTime + CLIP_LENGTH * (1 - CLIP_BEFORE_AFTER_RATIO):
				clip.append(cv2.cvtColor(np.uint8(videoFrames[key]), cv2.COLOR_BGR2RGB))
		try:
			os.mkdir(self.recordsPath)
		except: pass
		try:
			os.mkdir(self.recordsPath + "clips")
		except: pass
		try:
			# Create target Directory
			dirName = self.recordsPath + "clips/" + str(id)
			os.mkdir(dirName)
		except: pass

		for i in range(len(clip)):
			try:
				pth = "{:}/{:03}.jpeg".format(dirName, i)		
				# with open(pth, 'wb+') as fh:
				im = Image.fromarray(clip[i])
				im.save(pth)
			except:
				print("Could not save image: ", i)
			# time.sleep(1/100)

		try:
			shutil.make_archive(dirName, 'zip', dirName)	
			shutil.rmtree(dirName)
			print("Clip " , dirName ,  " saved.")	
		except:
			print("Could zip folder: ", dirName)	
		
		return id
		

	def _loadRecords(self):
		while self.loading or self.saving:
			time.sleep(.2)
		
		try:
			os.mkdir(self.recordsPath)
		except: pass
		try:
			os.mkdir(self.recordsPath + "clips")
		except: pass

		self.loading = True
		directory = os.fsencode(self.recordsPath)
		loaded = []
		for file in os.listdir(directory):
			filename = os.fsdecode(file)
			if filename.endswith(".obj"): 
				try:
					with open(self.recordsPath + filename, 'rb') as gameRecord:
						loaded.append(pickle.load(gameRecord))
				except: print("Could not load file: ", filename)
		self.loadedGames = loaded
		self.loading = False
		self.newData = True





class GameData():
	def __init__(self):
		self.datetime = datetime.now()
		self.score = [0,0]
		self.puckControl = [0,0]
		self.shotOnGoals = [0,0]
		self.accuracy = [0,0]
		self.duration = 0
		self.clips = {}
		self.goals = {}
		self.aiTopSpeed = [0,0]
		self.humanTopSpeed = [0,0]

	def getClipId(self, gametime):
		return self.clips[gametime]

	
	def copy(self):
		newInstance = GameData()
		newInstance.clips = self.clips.copy()
		newInstance.goals = self.goals.copy()
		newInstance.score = self.score.copy()
		newInstance.puckControl = self.puckControl.copy()
		newInstance.shotOnGoals = self.shotOnGoals.copy()
		newInstance.accuracy = self.accuracy.copy()
		newInstance.duration = self.duration
		newInstance.aiTopSpeed = self.aiTopSpeed.copy()
		newInstance.humanTopSpeed = self.humanTopSpeed.copy()
		return newInstance



		