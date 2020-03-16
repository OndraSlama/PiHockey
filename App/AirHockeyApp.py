import kivy
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.button import Button
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
from kivy.graphics.texture import Texture
from kivy.properties import StringProperty, NumericProperty, ObjectProperty, ListProperty
from kivy.uix.screenmanager import ScreenManager, Screen

from Settings import Settings
from Camera import Camera
from Game import Game
from Serial import Serial

import numpy as np
import cv2
from datetime import datetime
from random import randint

import os
os.environ['KIVY_GL_BACKEND'] = 'gl'

from kivy.base import EventLoop
EventLoop.ensure_window()

Window.clearcolor = (1, 1, 1, 1)
Window.size = (938, 550)
# Window.fullscreen = True

class RoundedLook(Widget):
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
			exec('self.value = int(App.get_running_app().root.settings.' + self.parameter +')')

	def on_touch_move(self, touch):
		if self.collide_point(touch.x, touch.y):
			self.isDown = True

	def on_touch_up(self, touch):
		self.isDown = False


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
			setCorners[i] = [self.absoluteReferencePoint[0] + distVector[0]*self.calibratingGain, self.absoluteReferencePoint[1] + distVector[1]*self.calibratingGain]
			# print(self.absoluteReferencePoint)

class CustomPopup(Popup):
	pass

class WinnerPopup(Popup):
	pass


class RootWidget(BoxLayout):
	settings = Settings('AirHockey_settings.obj')
	camera = Camera(settings.camera)
	game = Game(camera, settings.game)
	serial = Serial()
	

	def __init__(self, **kwarks):
		super(RootWidget, self).__init__(**kwarks)		
		
		self.changeScreen("settingsScreen") # Initial screen
		self.changeSettingsScreen("cameraSettingsScreen")

		# self.ids.cameraScreen.dropDown = RoundedDropDown()

		Clock.schedule_interval(self.updateValues, 1/10)
		Clock.schedule_interval(self.updateCamera, 1/30)
		Clock.schedule_interval(self.updateCommunication, 1/200)

		self.settings.game["applyMaxTime"]  = True
		Clock.schedule_once(self.initializeSerial, 1)
		Clock.schedule_once(self.initializeCamera, 1)

		Clock.schedule_interval(self.debug, 5)
		Clock.schedule_interval(self.debug2, 7)

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

	def openPopup(self, title = "Title", text = "Content", buttonText = "Dismiss", buttonAction = lambda x: print("nothing"), autoDismiss = True):
		print(text)
		infoPopup = CustomPopup()
		infoPopup.title = title
		infoPopup.text = text
		infoPopup.buttonText = buttonText
		infoPopup.auto_dismiss = autoDismiss
		infoPopup.onPress = buttonAction

		infoPopup.separator_color = self.colorTheme
		infoPopup.open()
	
	def openWinnerPopup(self, text = "Content"):
		winnerPopup = WinnerPopup()
		winnerPopup.text = text
		winnerPopup.open()

	def showStatus(self, text, time=1):
		print(text)
		self.showingStatus = True
		self.currentStatusText = text
		Clock.schedule_once(self.resetStatus, time)

	def setStatus(self, text):
		self.state = text
		if not self.showingStatus:			
			self.currentStatusText = self.state

	def resetStatus(self, *args):
		self.showingStatus = False
		self.currentStatusText = self.state
	
	def changeSettingsScreen(self, screenName):
		self.settings.saveSettings()
		screens = ["gameSettingsScreen", "cameraSettingsScreen", "motorsSettingsScreen", "otherSettingsScreen"]
		if screens.index(self.ids.settingsScreenManager.current) < screens.index(screenName):
			direction = "left"
		else:
			direction = "right"

		self.ids.settingsScreenManager.transition.direction = direction
		self.ids.settingsScreenManager.current = screenName
		for button in self.ids.settingsNavigationPanel.children:
			Animation.cancel_all(button, 'roundedCorners', "posHint", "alpha")
			anim = Animation(roundedCorners=[1,1,1,1], posHint=0, alpha=1, duration=0.5, t="out_back")
			anim.start(button)

		anim = Animation(roundedCorners=[1,1,0,0], posHint=-.2, alpha=0, duration=0.5, t="out_back")
		anim.start(self.ids[screenName + "Button"])

	def changeScreen(self, screenName):
		# Changing screen logic (animation, direction of the slide animation etc.)
		self.settings.saveSettings()
		screens = ["playScreen", "settingsScreen", "cameraScreen", "infoScreen"]
		if screens.index(self.ids.screenManager.current) < screens.index(screenName):
			direction = "up"
		else:
			direction = "down"
			
		
		self.ids.screenManager.transition.direction = direction
		self.ids.screenManager.current = screenName
		for button in self.ids.navigationPanel.children:
			Animation.cancel_all(button, 'size_hint_y')
			anim = Animation(size_hint_y=1, duration=0.5, t="out_back")
			anim.start(button)

		anim = Animation(size_hint_y=1.3, duration=0.5, t="out_back")
		anim.start(self.ids[screenName + "Button"])

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

			self.ids.difficultyDropdown.setIndex(index)

		# if index == 1


	def updateStatus(self, *args):
		# Update everything in status bar		
		self.setStatus("Idle")
		if not self.game.stopped: self.setStatus("Game running...")
		if self.game.paused: self.setStatus("Game paused")
		if self.ids.cameraStream.calibratingField: self.setStatus("Calibrating field...")
		if not self.camera.analyzingStopped: self.setStatus("Analyzing most dominant color...")
		if not self.camera.lockingAwbStopped: self.setStatus("Adjusting white balance...")

		self.dateString = datetime.now().strftime('%d.%m.%Y')
		self.timeString = datetime.now().strftime('%H:%M:%S')


	def updateCommunication(self, *args):
		self.game.setStriker(self.serial.vector)
		if self.controlMode == 1:
			self.serial.writeVector(self.game.getDesiredPosition(), "p")
		elif self.controlMode == 2:
			self.serial.writeVector(self.game.getDesiredVelocity(), "v")
		elif self.controlMode == 3:
			self.serial.writeVector((0,0), "p")
		elif self.controlMode == 4:
			self.serial.writeVector((0,0), "v")
		elif self.controlMode == 5:
			self.serial.writeVector((0,0), "m")
		

	def updateValues(self, *args):
		# Debug
		# print(self.desiredPos)
		# Camera values
		self.cameraResolution = self.settings.camera["resolution"]
		self.cameraFps = round(self.camera.counter.movingAverageFps)
		self.detectionFps = round(self.camera.detectingCounter.movingAverageFps)
		self.colorToDetect = self.settings.camera["colorToDetect"].tolist()
		self.normalizedColorToDetect = [self.colorToDetect[0]/180,self.colorToDetect[1]/255,self.colorToDetect[2]/255]
		self.colorLimits = [self.camera.settings["lowerLimits"].tolist(), self.settings.camera["upperLimits"].tolist()]
		self.whiteBalance = self.settings.camera["whiteBalance"]
		self.puckPos = [round(self.camera.unitFilteredPuckPosition.x), round(self.camera.unitFilteredPuckPosition.y)]
		self.puckPixelPos = [*self.camera._toTuple(self.camera._unitsToPixels(self.puckPos))]
		
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

		# Communication
		self.strikerPos = self.serial.vector

		# Strategy stuff
		self.desiredPos 		= self.game.getDesiredPosition()
		self.desiredVel 		= self.game.getDesiredVelocity()
		self.pixelDesiredPos 	= self.camera._toTuple(self.camera._unitsToPixels(self.desiredPos)) 

		# Status
		self.updateStatus()

		# # Update editors in settings
		# self.ids.lowerS

		# Color theme
		self.colorThemeHsv = [self.normalizedColorToDetect[0], 1, 1]
		self.colorTheme = Color(*self.colorThemeHsv, mode='hsv').rgba

	def getScore(self):
		score = self.game.score.copy()
		if not self.score[0] == score[0]: self.addScore(self.ids.human, self.ids.ai, [score[0], score[1]])
		if not self.score[1] == score[1]: self.addScore(self.ids.ai, self.ids.human, [score[1], score[0]])
		self.checkGameEnd()
		return score

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

	def checkGameEnd(self):
		if self.game.gameDone:
			self.game.gameDone = False
			self.game.stop()
			winner = "You win" if self.game.winner == 0 else "AI win" if self.game.winner == 1 else "Draw"
			self.openWinnerPopup(winner)
	
	def updateDetectedColor(self):
		if self.settings.camera["lowerLimits"][0] > self.settings.camera["upperLimits"][0]:
			temp = (int(self.settings.camera["upperLimits"][0]) + 180 + int(self.settings.camera["lowerLimits"][0]))/2
			self.settings.camera["colorToDetect"][0] = round(temp if temp - 180 < 0 else temp - 180)
		else:
			self.settings.camera["colorToDetect"][0] = round((int(self.settings.camera["upperLimits"][0]) + int(self.settings.camera["lowerLimits"][0]))/2)

		self.settings.camera["colorToDetect"][1] = round((int(self.settings.camera["upperLimits"][1]) + int(self.settings.camera["lowerLimits"][1]))/2)
		self.settings.camera["colorToDetect"][2] = round((int(self.settings.camera["upperLimits"][2]) + int(self.settings.camera["lowerLimits"][2]))/2)

	def updateCamera(self, *args):
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
				kivyField = [cv2kivy(point) for point in self.settings.camera["fieldCorners"].tolist()]				
				image.fieldCorners = [item for sublist in kivyField for item in sublist]
				image.puckPos = cv2kivy(self.camera._toTuple(self.camera._unitsToPixels(self.camera.unitFilteredPuckPosition)))
				image.desiredPos = cv2kivy(self.camera._toTuple(self.camera._unitsToPixels(self.game.getDesiredPosition())))
				image.strikerPos = cv2kivy(self.camera._toTuple(self.camera._unitsToPixels(self.serial.vector)))
			
			else:
				image = Image(size=(192, 320), source="icons/no-video.png", allow_stretch = False)

	# Helper functions
	def imageToTexture(self, frame, frameFormat="bgr"):
		# Convert numpy array frame to kivy texture
		texture = None
		if frame is not None:
			texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt=frameFormat)
			texture.blit_buffer(frame.flatten(), colorfmt=frameFormat, bufferfmt='ubyte')
		return texture
		
	def startAnimation(self, parameter, value, duration, transition, widget):
		Animation.cancel_all(widget, parameter)
		anim = eval("Animation("+parameter+"=value, duration=duration, t='"+transition+"')")
		anim.start(widget)		

class AirHockeyApp(App):
	def build(self): 
		return RootWidget()


if __name__ == "__main__":
	AirHockeyApp().run()