import kivy
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.uix.image import Image
from kivy.uix.image import AsyncImage
from kivy.properties import StringProperty, NumericProperty, ObjectProperty, ListProperty
from kivy.animation import Animation


from Constants import *
from Functions import getSpeedInXYdir
from UniTools import toList, toTuple, toVector

import os
import pickle

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
		app.root.desiredVel = getSpeedInXYdir(dir[0], dir[1], magnitude * app.root.settings.motors["velocity"])
		
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

class CircularInfoRange(Label):
	def changePortion(self, portion):
		Animation.cancel_all(self, 'portion')
		anim = Animation(portion=portion, duration=0.5, t="out_back")
		anim.start(self)
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