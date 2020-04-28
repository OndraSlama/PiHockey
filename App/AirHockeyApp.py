import kivy
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.dropdown  import DropDown
from kivy.graphics import Color, Ellipse
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.image import Image
from kivy.uix.image import AsyncImage
from kivy.graphics.texture import Texture
from kivy.properties import StringProperty, NumericProperty, ObjectProperty, ListProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.garden.joystick import Joystick

from Settings import Settings
from Camera import Camera
from Game import Game
from DataCollector import DataCollector
from Serial import Serial
from Constants import *
from Functions import getValueInXYdir

import numpy as np
import cv2
import os
from datetime import datetime
from random import randint
from functools import partial
from pygame.math import Vector2
import json

import os
os.environ['KIVY_GL_BACKEND'] = 'gl'

from kivy.base import EventLoop
EventLoop.ensure_window()

Window.clearcolor = (1, 1, 1, 1)
Window.size = (938, 550)
Window.fullscreen = True
#----------------------------- Widget definitions -----------------------------
class RoundedLook(Widget):
	pass

class RoundedButtonLook(Widget):
	pass

class RoundedButton(Button,RoundedButtonLook):
	__events__ = ('on_long_press', )
	long_press_time = NumericProperty(1)
    
	def on_state(self, instance, value):
		if value == 'down':
			lpt = self.long_press_time
			self._clockev = Clock.schedule_once(self._do_long_press, lpt)
		else:
			self._clockev.cancel()

	def _do_long_press(self, dt):
		self.dispatch('on_long_press')
		
	def on_long_press(self, *largs):
		pass

class RoundedLabel(Label,RoundedLook):
	pass

class SliderEditor(BoxLayout,RoundedLook):
	pass
	# def on_touch_down(self, touch):
	# 	self.isDown = True

	# def updateValue(self, value):
	# 	self.ids.slider.value = value
	def __init__(self, **kwarks):
		super(SliderEditor, self).__init__(**kwarks)		
		self.updateScheduler = Clock.schedule_interval(self.updateValue, 1/5)

	def updateValue(self, *args):
		if not self.parameter == "":
			exec('self.value = float(App.get_running_app().root.settings.' + self.parameter +')*1/'+ str(self.valueGain))

	def on_touch_move(self, touch):
		if self.collide_point(touch.x, touch.y):
			self.isDown = True

	def on_touch_up(self, touch):
		self.isDown = False

class ControlField(Image):
	def on_touch_down(self, touch):
		self.mode = 0
		fieldPos = self.getFieldPos([touch.x, touch.y])
		app = App.get_running_app()

		if XLIMIT < fieldPos[0] < STRIKER_AREA_WIDTH and abs(fieldPos[1]) < YLIMIT:
			self.mode = 3
			app.root.controlMode = 3
			app.root.desiredPos = fieldPos.copy()
		# print(app.root.controlMode)

		return super(ControlField, self).on_touch_down(touch) # propagate further

	def on_touch_move(self, touch):
		if self.mode == 3:
			fieldPos = self.getFieldPos([touch.x,  touch.y])

			app = App.get_running_app()
			app.root.desiredPos = [max(XLIMIT, min(STRIKER_AREA_WIDTH, fieldPos[0])), max(-YLIMIT, min(YLIMIT,fieldPos[1])) ]
		return super(ControlField, self).on_touch_move(touch) # propagate further

	def on_touch_up(self, touch):
		self.mode = 0
		app = App.get_running_app()
		return super(ControlField, self).on_touch_up(touch) # propagate further

	def getFieldPos(self, pos):
		return[int((pos[0] - (self.x + self.width * 131/1296))*1000/(self.width*(1034/1296))), 
				int((pos[1] - (self.y + self.height/2))*300/(self.height/2*(621/800)))]

	def joystickControl(self, dir, magnitude):
		app = App.get_running_app()
		app.root.controlMode = 4
		app.root.desiredVel = getValueInXYdir(dir[0], dir[1], magnitude * app.root.settings.motors["velocity"])
		
class ImageViewer(Image):
	def on_touch_down(self, touch):
		# Find closest corner
		minDist = float("inf")
		for i in range(4):
			distVector = [touch.x - self.fieldCorners[2*i], touch.y - self.fieldCorners[2*i+1]]
			dist = (distVector[0]**2 + distVector[1]**2)
			if dist < minDist:
				minDist = dist
				self.closestCorner = i
			
		app = App.get_running_app()
		setCorners = app.root.settings.camera["fieldCorners"]
		self.relativeReferencePoint = [touch.x, touch.y]
		self.absoluteReferencePoint = setCorners[self.closestCorner].copy()

	def on_touch_move(self, touch):
		if self.calibratingField:
			app = App.get_running_app()
			setCorners = app.root.settings.camera["fieldCorners"]
			i = self.closestCorner

			distVector = [touch.x - self.relativeReferencePoint[0], touch.y - self.relativeReferencePoint[1]]
			setCorners[i] = [self.absoluteReferencePoint[0] + distVector[0]*self.calibratingGain/app.root.settings.camera["resolution"][0], self.absoluteReferencePoint[1] + distVector[1]*self.calibratingGain/app.root.settings.camera["resolution"][1]]
			# print(self.absoluteReferencePoint)

#----------------------------- Popups -----------------------------
class CustomPopup(Popup):
	pass

class WinnerPopup(Popup):
	pass

class ImagePopup(Popup):
	def __init__(self, path="icons/no-video.png", **kwargs):
		super(ImagePopup, self).__init__(**kwargs)

		im = EnlargedViewer(source=path, allow_stretch=True)
		im.anim_delay = 1/CLIP_FRAMERATE
		im.animDelay = 1/CLIP_FRAMERATE
		# im.color=(0,0,0,.6)
		self.add_widget(im)

class HistoryPopup(Popup):
	def __init__(self, title, history, **kwargs):
		super(HistoryPopup, self).__init__(**kwargs)

		self.title = title
		self.historyText = "\n".join(history)


class GameRecord(RoundedButton):
	pass

class HighlightRecord(RoundedButton):
	pass

class ClipViewer(ButtonBehavior, AsyncImage):
	pass
	# def on_release(self):
	# 	App.get_running_app().root.openPopup("ClipViewer")

class EnlargedViewer(ButtonBehavior, AsyncImage):
	pass



#----------------------------- Root Widget -----------------------------
class RootWidget(BoxLayout):
	settings = Settings('ah_settings.obj')
	camera = Camera(settings.camera)
	game = Game(camera, settings.game)
	records = []
	dataCollector = DataCollector(game, camera, settings, "GameRecordings/")
	serial = Serial(settings.motors)
	

 #----------------------------- Init functions -----------------------------
	def __init__(self, **kwarks):
		super(RootWidget, self).__init__(**kwarks)		
		
		self.changeScreen("settingsScreen") # Initial screen
		self.changeSettingsScreen("motorsSettingsScreen")
		self.changeInfoScreen("matchesInfoScreen")
		# self.ids.cameraScreen.dropDown = RoundedDropDown()

		Clock.schedule_interval(self.updateValues, 1/10)
		Clock.schedule_interval(self.updateCameraScreen, 1/30)
		Clock.schedule_interval(self.updateArduino, 1/200)
		Clock.schedule_interval(self.updateInfoScreen, 1/5)
		Clock.schedule_interval(self.updateRecording, 1/100)

		self.settings.game["applyMaxTime"]  = True
		Clock.schedule_once(self.initializeSerial, 1)
		Clock.schedule_once(self.initializeCamera, 1)

		# Clock.schedule_once(self.debug3, 20)

		# Clock.schedule_interval(self.debug, 5)
		# Clock.schedule_interval(self.debug2, 7)

		self.statusScheduler = None
		self.showStatus("Oh, hi Mark!", 6)

	def initializeSerial(self, *args):
		try:
			self.serial.start()
			self.motorsConnected = True
		except:
			self.motorsConnected = False
			self.openPopup("Serial connection not working", "Connection to motors not established.\nCheck if everything is turned on and try again or restart the table.", "Try again", lambda x: Clock.schedule_once(self.initializeSerial, 1))

	def initializeCamera(self, *args):
		try:
			self.camera.startCamera()
			self.camera.startDetecting()
			self.cameraConnected = True		
		except:
			self.cameraConnected = False
			self.openPopup("Camera not working", "Camera not working, check if connected properly and try again or restart the table.", "Try again", lambda x: Clock.schedule_once(self.initializeCamera, 1))
 
 #----------------------------- Screen managers -----------------------------
	def changeInfoScreen(self, nextScreen):
		current = self.ids.infoScreenManager.current
		screens = ["matchesInfoScreen", "statsInfoScreen", "recordsInfoScreen"]
		if screens.index(current) < screens.index(nextScreen):
			direction = "left"
		else:
			direction = "right"

		# print(self.controlMode)

		self.ids.infoScreenManager.transition.direction = direction
		self.ids.infoScreenManager.current = nextScreen

		for button in self.ids.infoNavigationPanel.children:
			Animation.cancel_all(button, 'roundedCorners', "posHint", "alpha")
			anim = Animation(roundedCorners=[1,1,1,1], posHint=0, alpha=1, duration=0.5, t="out_back")
			anim.start(button)

		anim = Animation(roundedCorners=[1,1,0,0], posHint=-.2, alpha=0, duration=0.5, t="out_back")
		anim.start(self.ids[nextScreen + "Button"])

	def changeSettingsScreen(self, nextScreen):
		self.settings.saveSettings()
		current = self.ids.settingsScreenManager.current
		screens = ["gameSettingsScreen", "cameraSettingsScreen", "motorsSettingsScreen", "controlSettingsScreen"]
		if screens.index(current) < screens.index(nextScreen):
			direction = "left"
		else:
			direction = "right"

		if nextScreen == "controlSettingsScreen":
			self.ids.controlSettingsScreen.prevMode = self.controlMode

		if current == "controlSettingsScreen":
			self.controlMode = self.ids.controlSettingsScreen.prevMode

		# print(self.controlMode)

		self.ids.settingsScreenManager.transition.direction = direction
		self.ids.settingsScreenManager.current = nextScreen
		for button in self.ids.settingsNavigationPanel.children:
			Animation.cancel_all(button, 'roundedCorners', "posHint", "alpha")
			anim = Animation(roundedCorners=[1,1,1,1], posHint=0, alpha=1, duration=0.5, t="out_back")
			anim.start(button)

		anim = Animation(roundedCorners=[1,1,0,0], posHint=-.2, alpha=0, duration=0.5, t="out_back")
		anim.start(self.ids[nextScreen + "Button"])

	def changeScreen(self, screenName):
		# Changing screen logic (animation, direction of the slide animation etc.)
		self.settings.saveSettings()
		screens = ["playScreen", "settingsScreen", "cameraScreen", "infoScreen"]
		if screens.index(self.ids.screenManager.current) < screens.index(screenName):
			direction = "up"
		else:
			direction = "down"
		
		self.controlMode = self.ids.controlSettingsScreen.prevMode

		if screenName == "infoScreen":
			self.dataCollector.loadRecords()
		else:
			self.dataCollector.reset()
		
		self.ids.screenManager.transition.direction = direction
		self.ids.screenManager.current = screenName
		for button in self.ids.navigationPanel.children:
			Animation.cancel_all(button, 'size_hint_y')
			anim = Animation(size_hint_y=1, duration=0.5, t="out_back")
			anim.start(button)

		anim = Animation(size_hint_y=1.3, duration=0.5, t="out_back")
		anim.start(self.ids[screenName + "Button"])
 
 #----------------------------- Play screen management -----------------------------
	def addScore(self, player, opponent, score):
		Animation.cancel_all(player, 'portion')
		if self.settings.game["applyMaxScore"]:
			anim = Animation(portion=score[0]/self.settings.game["maxScore"], duration=0.5, t="out_back")
			anim.start(player)
		else:
			Animation.cancel_all(opponent, 'portion')
			anim1 = Animation(portion=min(1,max(0, score[0] - score[1])), duration=0.5, t="out_back")
			anim2 = Animation(portion=min(1,max(0, score[1] - score[0])), duration=0.5, t="out_back")
			anim1.start(player)
			anim2.start(opponent)
 
 #----------------------------- Settings screen management -----------------------------
	def changeDifficulty(self, index):
		self.settings.game["difficulty"] = index

		if not index == 0: 
			self.settings.game["robotSpeed"] = index
			self.settings.game["strategy"] = index
			self.settings.game["frequency"] = index * 90

			# self.ids.frequencySlider.updateValue(self.settings.game["frequency"])

			self.ids.frequencySlider.value = self.settings.game["frequency"]
			self.ids.robotSpeedDropdown.setIndex(self.settings.game["robotSpeed"]) 
			self.ids.strategyDropdown.setIndex(self.settings.game["strategy"])

			Clock.schedule_once(partial(self.executeString, 'self.ids.difficultyDropdown.setIndex(' + str(index) + ')'), .25)

		# if index == 1
	
	def changeSpeed(self, index):
		self.settings.game["robotSpeed"] = index
		if not index == 0: 
			self.settings.motors["velocity"] = (3000/3) * index
			self.settings.motors["acceleration"] = (30000/3) * index
			self.settings.motors["pGain"] = 21			
			Clock.schedule_once(partial(self.executeString, 'self.ids.robotSpeedDropdown.setIndex(' + str(index) + ')'), .25)

 #----------------------------- Camera screen management -----------------------------
	def updateCameraScreen(self, *args):
		# Update settings screen
		if self.ids.settingsScreenManager.current == "cameraSettingsScreen":
			image = self.ids.maskSettingsStream
			texture = self.imageToTexture(self.camera.filteredMask, "luminance")
			if texture is not None:
				self.cameraConnected = True
				image.texture = texture
			else:
				self.cameraConnected = False
				image = Image(size=(192, 320), source="icons/no-video.png", allow_stretch = False)

			image = self.ids.frameSettingsStream
			texture = self.imageToTexture(self.camera.frame, "bgr")
			if texture is not None:
				image.texture = texture
			else:
				image = Image(size=(192, 320), source="icons/no-video.png", allow_stretch = False)
			
		# Update camera screen
		def cv2kivy(point):
			return (image.x + point[0]/self.cameraResolution[0] * image.width, image.y + point[1]/self.cameraResolution[1] * image.height)
			
		# Update camera frame and everything camera can see in cameraScreen
		image = self.ids.cameraStream

		if self.ids.screenManager.current == "cameraScreen":
			if image.showing == "Frame":
				frame = self.camera.frame
				frameFormat = "bgr"
			elif image.showing == "Mask":
				frame = self.camera.mask
				frameFormat = "luminance"
			elif image.showing == "Filtered mask":
				frame = self.camera.filteredMask
				frameFormat = "luminance"

			texture = self.imageToTexture(frame, frameFormat)
			if texture is not None:
				image.texture = texture				
				kivyField = [cv2kivy((point[0] * self.settings.camera["resolution"][0], point[1] * self.settings.camera["resolution"][1])) for point in self.settings.camera["fieldCorners"].tolist()]	
				# print(kivyField)			
				image.fieldCorners = [item for sublist in kivyField for item in sublist]
				image.puckPos = cv2kivy(self.camera._toTuple(self.camera._unitsToPixels(self.camera.unitFilteredPuckPosition)))
				image.desiredPos = cv2kivy(self.camera._toTuple(self.camera._unitsToPixels(self.game.getDesiredPosition())))
				image.strikerPos = cv2kivy(self.camera._toTuple(self.camera._unitsToPixels(self.serial.vectors[0])))
			
			else:
				image = Image(size=(192, 320), source="icons/no-video.png", allow_stretch = False)

	def imageToTexture(self, frame, frameFormat="bgr"):
		# Convert numpy array frame to kivy texture
		texture = None
		if frame is not None:
			texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt=frameFormat)
			texture.blit_buffer(frame.flatten(), colorfmt=frameFormat, bufferfmt='ubyte')
		return texture	
 
	def updateRecording(self, *args):
		if self.recording:
			self.records.append([
				datetime.now().strftime('%Y-%m-%d_%H-%M-%S'),
				round(self.game.gameTime),
				[round(self.game.strategy.puck.position.x), round(self.game.strategy.puck.position.y)],
				[round(self.game.strategy.puck.velocity.x), round(self.game.strategy.puck.velocity.y)],
				self.game.strategy.puck.trajectory.copy(),
				[round(self.game.strategy.striker.position.x), round(self.game.strategy.striker.position.y)],
				[round(self.game.strategy.striker.velocity.x), round(self.game.strategy.striker.velocity.y)]
			])

	def saveRecord(self):
		datetimestr = datetime.now().strftime('Recording_%Y-%m-%d_%H-%M-%S')
		try:
			os.mkdir("CameraRecordings")
		except: pass

		with open("CameraRecordings/" + datetimestr + '.txt', 'w') as outfile:
			json.dump(self.records, outfile)

		print("recording saved")
		self.records = []

 #----------------------------- Info screen management ----------------------------- 
	def updateInfoScreen(self, *args):

		if self.dataCollector.newData:
			self.dataCollector.newData = False			
			for game in self.dataCollector.loadedGames:
				gameTimestamp = game.datetime.timestamp()
				# Check if record is alredy in list
				exist = False
				index = 0
				for child in self.ids.gameSrollView.children:
					if child.timestamp == gameTimestamp:
						exist = True	
						break					
					elif gameTimestamp > child.timestamp:
						index += 1
				if exist: continue

				gr = GameRecord()
				gr.timestamp = gameTimestamp
				winnerIcon = "icons/monitor.png" if game.score[0] > game.score[1] else "icons/human.png" if game.score[0] < game.score[1] else "icons/tie2.png"
				gr.iconSource = winnerIcon
				gr.text= "       ({3:})  {1:2} -{0:2}    {2:}".format(*game.score, game.datetime.strftime('%d.%m.%y %H:%M'), game.difficulty)

				self.ids.gameSrollView.add_widget(gr, index=index)
		
		if not self.dataCollector.saving and not self.dataCollector.loading and self.ids.matchesInfoScreen.timestamp == 0:
			if len(self.dataCollector.loadedGames) > 0:
				self.changeMatch((self.dataCollector.getNewestMatch().datetime.timestamp()))

	def changeMatch(self, timestamp):
		for child in self.ids.gameSrollView.children:
			child.disabled = False


		# for child in self.ids.highlightsSrollView.children:
		self.ids.highlightsSrollView.clear_widgets()

		match = self.dataCollector.getMatchByTimestamp(timestamp)
		if match == None: return

		self.ids.matchesInfoScreen.timestamp = timestamp
		self.ids.matchesInfoScreen.score = match.score
		self.ids.matchesInfoScreen.duration = match.duration
		self.ids.matchesInfoScreen.shotOnGoals = match.shotOnGoals
		self.ids.matchesInfoScreen.puckControl = match.puckControl
		self.ids.matchesInfoScreen.accuracy = match.accuracy
		self.ids.matchesInfoScreen.topSpeed = [match.humanTopSpeed[1], match.aiTopSpeed[1]]

		# Goal highlights
		prevScore = [0,0]
		for gameTime in match.goals:	
			# Insert highlight at the right place
			diff = [x - y for x, y in zip(match.goals[gameTime], prevScore)]
			goalFrom = diff.index(max(diff))
			prevScore = match.goals[gameTime]

			index = 0
			for child in self.ids.highlightsSrollView.children:				
				if gameTime < child.gameTime:
					index += 1

			hr = HighlightRecord()
			hr.gameTime = gameTime
			hr.uuid = str(match.clips[gameTime])
			hr.text = "                          {1:2} -{0:2}             at {2:02.0f}:{3:02.0f}".format(*match.goals[gameTime], gameTime//60, gameTime%60)
			hr.iconSource = "icons/human_goal.png" if goalFrom == 1 else "icons/robot_goal.png"
			hr.iconXSize = 2.5
			self.ids.highlightsSrollView.add_widget(hr, index=index)

		# Top speed ai highlight
		gameTime = match.aiTopSpeed[0]
		index = 0
		for child in self.ids.highlightsSrollView.children:				
			if gameTime < child.gameTime:
				index += 1

		hr = HighlightRecord()
		hr.gameTime = gameTime
		hr.uuid = str(match.clips[gameTime])
		hr.text = "                         {:.1f} m/s        at {:02.0f}:{:02.0f}".format(match.aiTopSpeed[1]/1000, gameTime//60, gameTime%60)
		hr.iconSource = "icons/robot_speed.png"
		hr.iconXSize = 2.5
		self.ids.highlightsSrollView.add_widget(hr, index=index)

		# Top speed human highlight
		gameTime = match.humanTopSpeed[0]
		index = 0
		for child in self.ids.highlightsSrollView.children:				
			if gameTime < child.gameTime:
				index += 1

		hr = HighlightRecord()
		hr.gameTime = gameTime
		hr.uuid = str(match.clips[gameTime])
		hr.text = "                         {:.1f} m/s        at {:02.0f}:{:02.0f}".format(match.humanTopSpeed[1]/1000, gameTime//60, gameTime%60)
		hr.iconSource = "icons/human_speed.png"
		hr.iconXSize = 2.5
		self.ids.highlightsSrollView.add_widget(hr, index=index)

		self.ids.clipViewer.clear_widgets()		
		im = Image(source="icons/no-video.png")
		im.color = (0, 0, 0, .6)
		self.ids.clipViewer.add_widget(im)

	def changeHighlight(self, id):
		for child in self.ids.highlightsSrollView.children:
			child.disabled = False

		self.ids.clipViewer.clear_widgets()		
		im = ClipViewer(source=self.dataCollector.recordsPath + 'clips/' + str(id) + '.zip')
		im.uuid = str(id)
		im.anim_delay = self.ids.matchesInfoScreen.clipFramerate
		self.ids.clipViewer.add_widget(im)

		# im.source(self.dataCollector.recordsPath + 'clips/' + str(id) + '.zip')
		# self.ids.matchesInfoScreen.timestamp = timestamp
		# print(self.ids.matchesInfoScreen.timestamp)

 #----------------------------- Values updation -----------------------------

	def updateValues(self, *args):
		# Debug
		# print(self.serial._readingCounter.print())
		# Camera values
		self.cameraResolution = self.settings.camera["resolution"]
		self.cameraFps = round(self.camera.counter.movingAverageFps)
		self.setCameraFps = self.settings.camera["fps"]
		self.minPuckRad = self.settings.camera["limitPuckRadius"]
		self.detectionFps = round(self.camera.detectingCounter.movingAverageFps)
		self.colorToDetect = self.settings.camera["colorToDetect"].tolist()
		self.normalizedColorToDetect = [self.colorToDetect[0]/180,self.colorToDetect[1]/255,self.colorToDetect[2]/255]
		self.colorLimits = [self.camera.settings["lowerLimits"].tolist(), self.settings.camera["upperLimits"].tolist()]
		self.whiteBalance = self.settings.camera["whiteBalance"]
		self.puckPos = [round(self.camera.unitFilteredPuckPosition.x), round(self.camera.unitFilteredPuckPosition.y)]
		# print(self.puckPos)
		self.puckPixelPos = [*self.camera._toTuple(self.camera._unitsToPixels(self.puckPos))]
		self.trajectory = []
		for line in self.game.strategy.puck.trajectory:
			[self.trajectory.append(i) for i in [line.start.x, line.start.y, line.end.x, line.end.y]] 
		
		# print(self.trajectory)
		# Game stuff
		self.playing = not self.game.stopped
		self.paused = self.game.paused
		self.gameTime = round(self.game.gameTime)
		self.gameTimeRemaining = self.settings.game["maxTime"] - self.gameTime if self.settings.game["applyMaxTime"] else -1		
		self.gameFrequency = self.game.frequencyCounter.movingAverageFps 
		self.score = self.getScore()
		self.maxScore = self.settings.game["maxScore"]
		self.maxTime = self.settings.game["maxTime"]		
		self.frequency = self.settings.game["frequency"]
		self.strategyDescription = self.game.strategy.description

		# Motors
		self.readingLine = self.serial._readingLine
		self.writingLine = self.serial._prevWrite
		self.strikerPos = self.serial.vectors[0]
		self.strikerVel = self.serial.vectors[1]
		self.motorStatus = self.serial.status if self.serial.status is not None else ""
		# if self.serial.status is not None: self.homed = False
		self.homed = self.serial.homed
		if self.serial.homed:
			self.homing = False
		self.comFrequency = self.settings.motors["communicationFrequency"]
		self.setVelocity = self.settings.motors["velocity"]
		self.setAcceleration = self.settings.motors["acceleration"]
		self.setPGain = self.settings.motors["pGain"]

		# Strategy stuff
		self.pixelDesiredPos = self.camera._toTuple(self.camera._unitsToPixels(self.desiredPos)) 

		# Status
		self.updateStatus()

		# Color theme
		self.colorThemeHsv = [self.normalizedColorToDetect[0], 1, 1]
		self.colorTheme = Color(*self.colorThemeHsv, mode='hsv').rgba
  	
	def updateDetectedColor(self):
		if self.settings.camera["lowerLimits"][0] > self.settings.camera["upperLimits"][0]:
			temp = (int(self.settings.camera["upperLimits"][0]) + 180 + int(self.settings.camera["lowerLimits"][0]))/2
			self.settings.camera["colorToDetect"][0] = round(temp if temp - 180 < 0 else temp - 180)
		else:
			self.settings.camera["colorToDetect"][0] = round((int(self.settings.camera["upperLimits"][0]) + int(self.settings.camera["lowerLimits"][0]))/2)

		self.settings.camera["colorToDetect"][1] = round((int(self.settings.camera["upperLimits"][1]) + int(self.settings.camera["lowerLimits"][1]))/2)
		self.settings.camera["colorToDetect"][2] = round((int(self.settings.camera["upperLimits"][2]) + int(self.settings.camera["lowerLimits"][2]))/2)
	
 #----------------------------- Communication with arduino -----------------------------
	def updateArduino(self, *args):
	 #----------------------------- Read -----------------------------
		if self.serial.readStatus() == "e1":
			self.changeSettingsScreen("motorsSettingsScreen")
			self.openPopup("End switch", "Safety end-switch has been activated. Either robot or someting else pressed it. Check robot table side and home motors to contine.", "Go to settings", lambda *args: self.changeScreen("settingsScreen"))
			self.homed = False

		if self.serial.readStatus() == "e2":
			self.changeSettingsScreen("motorsSettingsScreen")
			self.openPopup("Driver error", "Error occured in one of the motor drivers. Most likely due to missed steps. Try lowering motors movement parameters and restart drivers to contine", "Go to settings", lambda *args: self.changeScreen("settingsScreen"))
			self.homed = False

		# if self..readStatus() == "homed":
		# 	self.showStatus("Homing finished")
		# 	self.homed = True

		self.game.setStriker(self.serial.vectors[0], self.serial.vectors[1])
		if self.serial.goal == "gr": # goal on robot side
			self.game.goal(1)
			Clock.schedule_once(partial(self.serial.queueLine, "solenoid"), 1)

		if self.serial.goal == "gh": # goal on human side
			self.game.goal(0)
		self.serial.goal = None

	 #----------------------------- Write -----------------------------
		if self.controlMode == 1:
			if self.playing:
				self.desiredPos = [*self.game.getDesiredPosition()]
				self.serial.writeVector(self.desiredPos, "p")
		elif self.controlMode == 2:
			if self.playing:
				self.desiredVel = [*self.game.getDesiredVelocity()]
				self.serial.writeVector(self.desiredVel, "v")
		elif self.controlMode == 3:
			self.serial.writeVector(self.desiredPos, "p")
		elif self.controlMode == 4:
			self.serial.writeVector(self.desiredVel, "v")
		elif self.controlMode == 5:
			self.serial.writeVector(self.desiredMot, "m")
		
		# print(self.desiredPos)
	
	def setFans(self, value, *args):
		self.serial.queueLine("fans,"+str(int(value)))
		self.fansOn = value
		self.ids.fansToggle.state = "down" if value else "normal"
	
	def setLeds(self, value, *args):
		self.serial.queueLine("leds,"+str(int(value)))
		self.ledsOn = value
		self.ids.ledsToggle.state = "down" if value else "normal"
 
 #----------------------------- Notifications & info -----------------------------
	def openPopup(self, title = "Title", text = "Content", buttonText = "Dismiss", buttonAction = lambda x: print("nothing"), autoDismiss = True):
		# print(text)
		infoPopup = CustomPopup()
		infoPopup.title = title
		infoPopup.text = text
		infoPopup.buttonText = buttonText
		infoPopup.auto_dismiss = autoDismiss
		infoPopup.onPress = buttonAction

		infoPopup.separator_color = self.colorTheme
		infoPopup.open()
	
	def openImage(self, path):
		popup = ImagePopup(path)
		popup.open()
	
	def openHistory(self, title = "Title", history = ["log1", "log2", "log3"]):
		popup = HistoryPopup(title, history)
		popup.open()

	def openWinnerPopup(self, text = "Content"):
		winnerPopup = WinnerPopup()
		winnerPopup.text = text
		winnerPopup.open()

	def showStatus(self, text, time=1):
		if self.statusScheduler is not None:
			Clock.unschedule(self.statusScheduler)
		self.showingStatus = True
		self.currentStatusText = text
		self.statusScheduler = Clock.schedule_once(self.resetStatus, time)

	def setStatus(self, text):
		self.state = text
		if not self.showingStatus:			
			self.currentStatusText = self.state

	def resetStatus(self, *args):
		self.showingStatus = False
		self.currentStatusText = self.state
	
	def updateStatus(self, *args):
		# Update everything in status bar		
		self.setStatus("Idle")
		if self.dataCollector.loading: self.setStatus("Loading saved clips and game stats...")
		if self.dataCollector.saving: self.setStatus("Saving game clips and stats...")
		if not self.homed: self.setStatus("Homing required!")
		if self.homing: self.setStatus("Homing...")
		if not self.game.stopped: self.setStatus("Game running...")
		if self.game.paused: self.setStatus("Game paused")
		if not self.game.stopped and self.game.waitForPuck: self.setStatus("Waiting for puck...")
		if self.ids.cameraStream.calibratingField: self.setStatus("Calibrating field...")
		if not self.camera.analyzingStopped: self.setStatus("Analyzing most dominant color...")
		if not self.camera.lockingAwbStopped: self.setStatus("Adjusting white balance...")

		self.dateString = datetime.now().strftime('%d.%m.%Y')
		self.timeString = datetime.now().strftime('%H:%M:%S')
 
 #----------------------------- Game management -----------------------------
	def getScore(self):
		score = self.game.score.copy()
		if not self.score[1] == score[1]: self.addScore(self.ids.human, self.ids.ai, [score[1], score[0]])
		if not self.score[0] == score[0]: self.addScore(self.ids.ai, self.ids.human, [score[0], score[1]])
		self.checkGameEnd()
		return score

	def checkGameEnd(self):
		if self.game.gameDone:
			self.stopGame()
			winner = "You win" if self.game.winner == 0 else "AI win" if self.game.winner == 1 else "Draw"
			self.openWinnerPopup(winner)
	
	def startGame(self):
		self.game.start()	
		self.dataCollector.start()
		self.setFans(True)
		self.setLeds(True)

	def stopGame(self):
		self.game.gameDone = False
		self.game.stop()
		self.dataCollector.stop()
		self.setFans(False)
		self.setLeds(False)
 
 #----------------------------- Helper functions -----------------------------
	def setControlMode(self, mode, *args):
		self.controlMode = mode
	def setDesiredPos(self, vector, *args):
		self.desiredPos = vector.copy()
	def setDesiredVel(self, vector, *args):
		self.desiredVel = vector.copy()
	def setDesiredMot(self, vector, *args):
		self.desiredMot = vector.copy()
	def executeString(self, string, *args):
		exec(string)
	
  #----------------------------- Others -----------------------------		
	def startAnimation(self, parameter, value, duration, transition, widget):
		Animation.cancel_all(widget, parameter)
		anim = eval("Animation("+parameter+"=value, duration=duration, t='"+transition+"')")
		anim.start(widget)
 
 #----------------------------- Debug -----------------------------
	def testMotors(self):
		targetPositions = [
			[50, -250],
			[450, 250],
			[50, -250],
			[450, 250],
			[50,   250],
			[450, -250],
			[50,   250],
			[450, -250]
		]

		prevMode = self.controlMode
		self.controlMode = 3
		for i in range(len(targetPositions)):
			Clock.schedule_once(partial(self.setDesiredPos, targetPositions[i]), i)
		
		Clock.schedule_once(partial(self.setControlMode, prevMode), i+1)

	def debug(self, *args):
		if self.playing:
			self.game.score[0] = self.game.score[0] + 1
			# self.game.score[1] = self.game.score[1] + 3
			# if self.game.score[0] > self.settings.game["maxScore"]:
			# 	self.game.score[0] = 0
			pass
	def debug2(self, *args):
		if self.playing:
			# self.game.score[0] = self.game.score[0] + 1
			self.game.score[1] = self.game.score[1] + 3
			# if self.game.score[0] > self.settings.game["maxScore"]:
			# 	self.game.score[0] = 0
			pass

	def debug3(self, *args):
		self.serial.status = "e1"

#----------------------------- App widget -----------------------------
class AirHockeyApp(App):
	def build(self): 
		return RootWidget()


if __name__ == "__main__":
	AirHockeyApp().run()