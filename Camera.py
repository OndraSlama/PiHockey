# ****************************************************************************** #
# Author: Ondrej Slama
# -------------------

# Zdrojovy kod vytvoreny v ramci projektu robotickeho vzdusneho hokeje - diplomova prace
#  na VUT FSI ustavu automatizace a informatiky v Brne.

# Source code created as a part of robotic air hockey table project - Diploma thesis
# at BUT FME institute of automation and computer sience.

# ****************************************************************************** #
import cv2
import numpy as np
from threading import Thread
try:
	from picamera.array import PiRGBArray
	from picamera import PiCamera
	from PiVideoStream import PiVideoStream
except:
	pass
from UniTools import Filter, FPSCounter, Repeater
from pygame.math import Vector2
from Constants import *
from Settings import Settings
import imutils
import time
import random

# Those settings are basically only for early stage debbuging
# MAX_PERFORMANCE should be always set to 1. Trust me, hell will be unleashed upon you otherwise.
MAX_PERFORMANCE = 1

PUCK_RADIUS = 20
RESOLUTION_SCALE = 1
DETECT_PUCK = 1
HSV_TRACKBARS = 0
WHITEBALANCE_TRACKBARS = 0
ENABLE_BLURRING = 0

SHOW_DETECTION = 1
SHOW_FPS = 1
SHOW_CAPTURE_INFO = 0
SHOW_MOUSE_HSV = 1
SHOW_MASK = 1
SHOW_FILTERED_MASK = 1


class Camera():

	def __init__(self, settings = None): # 320, 192
		if settings is None:
			settings = Settings('AirHockey_settings.obj')
			self.settings = settings.camera
		else:
			self.settings = settings

		self.piVideo = None
		self.camera = None

		self.detectionStopped = True
		self.analyzingStopped = True
		# self.findingFieldStopped = True
		self.lockingAwbStopped = True

		self.counter = FPSCounter(movingAverage=120).start()
		self.detectingCounter = FPSCounter(movingAverage=120)

		self.frame = None
		self.mask = None
		self.filteredMask = None
		self.cursorPosition = None
		self.frameCount = 0

		# self._determineColorIntervals()

		self.p2uTranformMatrix = None
		self.u2pTranformMatrix = None
		self.prevFieldCorners = None
		self._createTransformMatrices(self.settings["fieldCorners"].copy())
		
		self.newPosition = False
		self.pixelPuckPosition = Vector2(int(0), int(0))
		self.unitPuckPosition = Vector2(0, 0)
		self.unitFilteredPuckPosition = Vector2(0, 0)

		self.filter = Filter(*self.settings["filterConstants"])

		self.callback = self._nothing
	
	def lockCameraAwb(self):
		print("Calibrating...")

		# Get auto-set values		
		rg, bg = self.camera.awb_gains
		prevGains = (rg, bg)

		print("Warming up...")
		time.sleep(1.0)
		print("Done")

		frameCount = 0
		while frameCount < 300:
			if self.piVideo.newFrame:
				self.frame = self.piVideo.read()				
				frameCount += 1

				greenPart = np.repeat(self.frame[:,:,1], 3).reshape(self.frame.shape)
				diffToWhite = (self.frame.astype("int16") - greenPart.astype("int16"))

				if frameCount == 1:

					# Get reference pixels
					vectorized = diffToWhite.reshape((-1,3)).astype("float32")
					K = 8
					attempts = 10
					criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
					ret,label,center=cv2.kmeans(vectorized,K,None,criteria,attempts,cv2.KMEANS_PP_CENTERS)

					labels = label.flatten()
					mostFrequentLabel = np.argmax(np.bincount(labels))
					referenceIndexes = [random.choice(np.argwhere(labels==mostFrequentLabel))[0] for x in range(10)]

					mask = (labels == mostFrequentLabel).reshape(self.frame.shape[0], self.frame.shape[1]).astype("uint8")

				# Get reference pixel for current iteration
				referencePixel = diffToWhite.reshape((-1,3))[random.choice(referenceIndexes)] 
				if abs(referencePixel[0]) < 5 and abs(referencePixel[2]) < 5:
					break # If good enough -> break

				# Set white balance iterably
				rg -= referencePixel[2]/500
				bg -= referencePixel[0]/500
				
				self.settings["whiteBalance"] = [max(min(rg, 8), 0), max(min(bg, 8), 0)]
				self.setWhiteBalance()
				self.frame = cv2.bitwise_and(self.frame, self.frame, mask=mask)

				# cv2.imshow("Calibrating", self.frame)
				cv2.waitKey(1)
				time.sleep(0.2)

		rg, bg = self.camera.awb_gains
		if rg < 0.1 or bg < 0.1:
			results = "Failed to find sufficient gains.\nTry again."
			self.camera.awb_gains = prevGains
		else:
			results = "Set white balance:\nRed gain: {}\nBlue gain: {}".format(round(float(rg),1), round(float(bg),1))

		self.lockingAwbStopped = True
		self.callback(results)
		# print(results)
		return

		# cv2.destroyWindow("Calibrating")
		# cv2.waitKey(1)


	# def findField(self):
	# 	# TODO
	# 	self.settings["fieldCorners"] = self.settings["fieldCorners"]
	# 	self._calibrateField()
	# 	self.findingFieldStopped = True

	def analyzeColor(self):	
		started = time.time()
		secondLeft = 3
		print("Analyzing most domiant color...")
		print("Saving in: " + str(secondLeft))
		secondLeft -= 1
		while True:
			if self.piVideo.newFrame:
				self.frame = self.piVideo.read()		
				frame = self.frame[round(self.settings["resolution"][1]*0.2):round(self.settings["resolution"][1]*0.8), round(self.settings["resolution"][0]*0.2):round(self.settings["resolution"][0]*0.8)]
				frame = cv2.GaussianBlur(frame, (11, 11), 0)
				# cv2.imshow("Analyzing", frame)
				
				if time.time() - started > 1:
					print(secondLeft)
					secondLeft -= 1
					started = time.time()	

				vectorized = frame.reshape((-1,3)).astype("float32")
				K = 3
				attempts = 10
				criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
				ret,label,center = cv2.kmeans(vectorized,K,None,criteria,attempts,cv2.KMEANS_PP_CENTERS)

				labels = label.flatten()
				mostFrequentLabel = np.argmax(np.bincount(labels))

				self.settings["colorToDetect"] = detectedColor = cv2.cvtColor(np.uint8([[center[mostFrequentLabel]]]),cv2.COLOR_BGR2HSV)[0,0,:]
				self._determineColorIntervals()
				# Create a blank 300x300 black image
				foundColorFrame = np.zeros((100, 100 , 3), np.uint8)
				# Fill image with red color(set each pixel to red)
				foundColorFrame[:] = np.uint8([[center[mostFrequentLabel]]])[0,0,:]
				# cv2.imshow("FoundColor", foundColorFrame)

				cv2.waitKey(1)

				if secondLeft == 0:
					print("Saving found color...")
					self._determineColorIntervals()
					break

		# cv2.destroyWindow("Analyzing")
		# cv2.destroyWindow("FoundColor")
		# cv2.waitKey(1)

		results = "Found color: {}\n Set limits: {} {}".format(detectedColor, self.settings["lowerLimits"], self.settings["upperLimits"])
		self.callback(results)
		# print(results)
		self.analyzingStopped = True

	
	def detectPuck(self):	

		if not MAX_PERFORMANCE:
			cv2.namedWindow('Frame')
			if HSV_TRACKBARS:
				cv2.setMouseCallback('Frame', self._mouseHSV)
				cv2.namedWindow("Trackbars")	
				cv2.createTrackbar("Hl", "Trackbars", 0, 179, self._nothing)
				cv2.createTrackbar("Hh", "Trackbars", 0, 179, self._nothing)
				cv2.setTrackbarPos("Hl", "Trackbars", self.settings["lowerLimits"][0])
				cv2.setTrackbarPos("Hh", "Trackbars", self.settings["upperLimits"][0])
			
			if WHITEBALANCE_TRACKBARS:
				cv2.namedWindow("White balance")	
				cv2.createTrackbar("Red", "White balance", 0, 80, self._nothing)
				cv2.createTrackbar("Blue", "White balance", 0, 80, self._nothing)

		print("Detecting...")
		while True:
			if self.piVideo.newFrame:				
				self.frame = self.piVideo.read()				
				self.frameCount += 1
				self.counter.tick()

				self._createTransformMatrices(self.settings["fieldCorners"])

				if ENABLE_BLURRING and not MAX_PERFORMANCE:
					blurred = cv2.GaussianBlur(self.frame, (11, 11), 0)
					frameHSV = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV) # not worth
				else:
					frameHSV = cv2.cvtColor(self.frame, cv2.COLOR_BGR2HSV)

				if HSV_TRACKBARS and not MAX_PERFORMANCE:
					self.settings["lowerLimits"][0] = cv2.getTrackbarPos("Hl", "Trackbars")
					self.settings["upperLimits"][0] = cv2.getTrackbarPos("Hh", "Trackbars")

				# if DETECT_PUCK:
				if self.settings["lowerLimits"][0] > self.settings["upperLimits"][0]:
					lowerLimit1 = np.uint8(self.settings["lowerLimits"])
					higherLimit1 = np.uint8([179, self.settings["upperLimits"][1], self.settings["upperLimits"][2]])
					lowerLimit2 = np.uint8([0, self.settings["lowerLimits"][1], self.settings["lowerLimits"][2]])
					higherLimit2 = np.uint8(self.settings["upperLimits"])

					mask1 = cv2.inRange(frameHSV, lowerLimit1, higherLimit1)
					mask2 = cv2.inRange(frameHSV, lowerLimit2, higherLimit2)

					self.mask = cv2.bitwise_or(mask1, mask2)
				else:
					self.mask = cv2.inRange(frameHSV, self.settings["lowerLimits"], self.settings["upperLimits"])

				# perform a series of dilations and erosions to remove any small blobs left in the self.mask
				self.filteredMask = cv2.erode(self.mask, None, iterations=1)
				self.filteredMask = cv2.dilate(self.filteredMask, None, iterations=1)
				filtered = cv2.bitwise_and(self.frame, self.frame, mask=self.filteredMask)
				
				#----------------------------- DETECTION -----------------------------
				try:
					cnts = cv2.findContours(self.filteredMask.copy(), cv2.RETR_EXTERNAL,
					cv2.CHAIN_APPROX_SIMPLE)
					cnts = imutils.grab_contours(cnts)
					center = None

					# only proceed if at least one contour was found
					if len(cnts) > 0:
						# find the largest contour in the mask, then use it to compute the minimum enclosing circle and centroid
						c = max(cnts, key=cv2.contourArea)
						((x, y), radius) = cv2.minEnclosingCircle(c)

						# only proceed if the radius meets a minimum size
						if radius > self.settings["limitPuckRadius"]:
							self.detectingCounter.tick()

							pixelPos = Vector2(int(x + 1), int(y + 3))
							unitPos = self._pixelsToUnits(pixelPos)
							if self._isPuckInField(unitPos):
								self.pixelPuckPosition = pixelPos
								self.unitPuckPosition = unitPos
								self.unitFilteredPuckPosition = self.filter.filterData(Vector2(self.unitPuckPosition[0], self.unitPuckPosition[1]))
								self.newPosition = True						
				except:
					print("Error during puck detection.")

				
				if not MAX_PERFORMANCE:
					if SHOW_DETECTION:
						self._drawField(self.settings["fieldCorners"])
						self._drawPuck(self.pixelPuckPosition)
						filteredPixelPos = self._unitsToPixels(self.unitFilteredPuckPosition)
						self._drawPuck(filteredPixelPos, color=(0,255,0))
						# self._writeText(str(self.unitPuckPosition), (self.pixelPuckPosition[0] + 10, self.pixelPuckPosition[1] + 10), fontScale=0.5)
						self._writeText(str(self.unitFilteredPuckPosition), (filteredPixelPos[0] + 10, filteredPixelPos[1] + 10), fontScale=0.5)

						# min enclosing circle
						try:
							cv2.circle(self.frame, self.pixelPuckPosition, int(radius), (0, 255, 255), 2)
						except:
							pass

					# Write info to frame
					if SHOW_MOUSE_HSV:
						try:
							self._writeText("HSV: " + str(frameHSV[self.cursorPosition.y, self.cursorPosition.x]))
						except:
							pass			

					if SHOW_FPS:
						self._writeText("FPS: " + str(round(self.counter.movingAverageFps)), position=(10, 60), fontScale=0.6)
					if SHOW_CAPTURE_INFO:
						self._writeText("Exposure: " + str(self.piVideo.camera.exposure_speed), position=(10, 80), fontScale=0.6)
						r,g = self.camera.awb_gains
						self._writeText("AWB Gains: " + str((round(float(r),1), round(float(g),1))), position=(10, 100), fontScale=0.6)
						self._writeText("a/d Gains: " + str((round(float(self.camera.analog_gain),1), round(float(self.camera.digital_gain), 1))), position=(10, 120), fontScale=0.6)

					# Show image
					if SHOW_MASK and DETECT_PUCK:
						cv2.imshow("Mask", self.mask)

					if SHOW_FILTERED_MASK and DETECT_PUCK:
						cv2.imshow("Filtered mask", self.filteredMask)

					cv2.imshow("Frame", self.frame)

					if WHITEBALANCE_TRACKBARS:
						rg = cv2.getTrackbarPos("Red", "White balance")/10
						bg = cv2.getTrackbarPos("Blue", "White balance")/10
						self.camera.awb_gains = (rg, bg)

			key = cv2.waitKey(5)	

			if self.detectionStopped:
				print("Detecting stopped.")
				return

		self.piVideo.stop()
		cv2.destroyAllWindows()

	def startCamera(self):
		if self.piVideo is None:
			self.piVideo = PiVideoStream(self.settings["resolution"], self.settings["fps"], self.settings["whiteBalance"])
			self.camera = self.piVideo.camera

		self.piVideo.start()		

	def stopCamera(self):
		self.detectionStopped = True
		self.analyzingStopped = True
		self.findingFieldStopped = True
		self.lockingAwbStopped = True
		time.sleep(.1)
		
		self.piVideo.stop()
		self.piVideo = None
		self.camera = None

	def startDetecting(self):
		if self.detectionStopped:
			self.detectionStopped = False
			self.detectingCounter.start()
			Thread(target=self.detectPuck, args=()).start()
		else:
			print("Detecting thread already running.")

	def stopDetecting(self):
		self.detectingCounter.stop()
		self.detectionStopped = True	

	def startAnalyzing(self, callback = None):
		if callback is None:
			self.callback = self._nothing
		else:
			self.callback = callback
			
		if self.analyzingStopped:
			self.analyzingStopped = False
			Thread(target=self.analyzeColor, args=()).start()
		else:
			print("Analyzing thread already running.")

	def stopAnalyzing(self):
		self.analyzingStopped = True

	# def startFindingField(self, callback = None):
	# 	if callback is None:
	# 		self.callback = self._nothing
	# 	else:
	# 		self.callback = callback

	# 	if self.findingFieldStopped:
	# 		self.findingFieldStopped = False
	# 		Thread(target=self.findField, args=()).start()
	# 	else:
	# 		print("Finding field thread already running.")

	# def stopFindingField(self):
	# 	self.findingFieldStopped = True

	def startLockingAwb(self, callback = None):
		if callback is None:
			self.callback = self._nothing
		else:
			self.callback = callback

		if self.lockingAwbStopped:
			self.lockingAwbStopped = False
			Thread(target=self.lockCameraAwb, args=()).start()
		else:
			print("Locking AWB thread already running.")

	def stopLockingAwb(self):
		self.lockingAwbStopped = True

	def getPuckPosition(self):
		self.newPosition = False
		return self.unitFilteredPuckPosition

	def setWhiteBalance(self):
		if self.camera is not None:
			self.camera.awb_gains = (self.settings["whiteBalance"][0], self.settings["whiteBalance"][1])


	def _isPuckInField(self, pos):
		if not (0 < pos.x < FIELD_WIDTH):
			return False
		if not (-FIELD_HEIGHT/2 < pos.y < FIELD_HEIGHT/2): 
			return False
		return True
	
	# def _calibrateField(self):
	# 	# TODO: find the field

	# 	self._createTransformMatrices(self.settings["fieldCorners"])		

	def _determineColorIntervals(self):		

		Hl = self.settings["colorToDetect"][0] - round(self.settings["intervals"][0]/2)
		if Hl < 0: Hl += 179

		Hh = self.settings["colorToDetect"][0] + round(self.settings["intervals"][0]/2)
		if Hh > 179: Hh -= 179

		self.settings["lowerLimits"] = np.uint8([Hl, max(5, self.settings["colorToDetect"][1] - round(self.settings["intervals"][1])), max(5, self.settings["colorToDetect"][2] - round(self.settings["intervals"][2]))])
		self.settings["upperLimits"] = np.uint8([Hh, min(255, self.settings["colorToDetect"][1] + round(self.settings["intervals"][1]/2)), min(255, self.settings["colorToDetect"][2] + round(self.settings["intervals"][2]/2))])

	def _nothing(self, *args):
		pass

	def _pixelsToUnits(self, srcPos):	
		srcPos = self._toVector(srcPos)
		src = np.float32([[srcPos.x, srcPos.y]])	
		src = np.array([src])

		out = cv2.perspectiveTransform(src, self.p2uTranformMatrix)
		return Vector2(int(out[0][0][0]), int(out[0][0][1]))

	def _unitsToPixels(self, srcPos):	
		srcPos = self._toVector(srcPos)
		src = np.float32([[srcPos.x, srcPos.y]])	
		src = np.array([src])

		out = cv2.perspectiveTransform(src, self.u2pTranformMatrix)
		return Vector2(int(out[0][0][0]), int(out[0][0][1]))

	def _toTuple(self, vector):
		if isinstance(vector, Vector2):
			return (int(vector.x), int(vector.y))
		else:
			return (int(vector[0]), int(vector[1]))
	
	def _toVector(self, vector):
		if isinstance(vector, Vector2):
			return Vector2(int(vector.x), int(vector.y))
		else:
			return Vector2(int(vector[0]), int(vector[1]))	
		
	def _createTransformMatrices(self, fieldCorners):
		if self.prevFieldCorners is None or not (np.all(self.prevFieldCorners == fieldCorners)):
			# print("Calculating transform matrices.")
			self.prevFieldCorners = fieldCorners.copy()
			source = np.float32([[point[0] * self.settings["resolution"][0], point[1] * self.settings["resolution"][1]] for point in self.settings["fieldCorners"].tolist()])
			dst = np.float32([[0, -FIELD_HEIGHT/2], [FIELD_WIDTH, -FIELD_HEIGHT/2], [FIELD_WIDTH, FIELD_HEIGHT/2], [0, FIELD_HEIGHT/2]])
			dst = np.array([dst])

			self.p2uTranformMatrix = cv2.getPerspectiveTransform(source, dst)
			self.u2pTranformMatrix = cv2.getPerspectiveTransform(dst, source)

	def _writeText(self, text, position=(10, 30), fontScale=1, fontColor = (255,255,255)):
		font 		= cv2.FONT_HERSHEY_SIMPLEX
		lineType 	= 2

		cv2.putText(self.frame, text,
			self._toTuple(position), 
			font, 
			fontScale,
			fontColor,
			lineType)
	
	def _drawLine(self, startPoint = (0,10), endPoint = (250, 10), color = (0, 255, 0),  thickness = 2):		
		self.frame = cv2.line(self.frame, self._toTuple(startPoint), self._toTuple(endPoint), color, thickness)

	def _lineHalf(self, startPoint, endPoint):
		x = round((startPoint[0] + endPoint[0])/2)
		y = round((startPoint[1] + endPoint[1])/2)
		return (x, y)

	def _drawPoint(self, center, color = (0, 255, 255), size = 5):
		center = self._toTuple(center)
		cv2.circle(self.frame, center, size, color, -1)
	
	def _drawPuck(self, center, color = (0, 0, 255)):
		center = self._toTuple(center)
		cv2.circle(self.frame, center, PUCK_RADIUS, color, 1)
		cv2.circle(self.frame, center, 2, color, -1)

	def _drawField(self, npPoints, color = (0, 255, 0),  thickness = 3):
		points = [self._toTuple(p) for p in npPoints]

		for i in range(len(points)-1):
			self._drawLine(points[i], points[i + 1])

		self._drawLine(points[3], points[0])

		# Draw field center 
		self._drawLine(self._lineHalf(points[0], points[1]), self._lineHalf(points[2], points[3]), thickness=1)
		self._drawLine(self._lineHalf(points[1], points[2]), self._lineHalf(points[3], points[0]), thickness=1)

	def _mouseHSV(self, event,x,y,flags,param):
		self.cursorPosition = Vector2(x,y)




# piVideo.camera.awb_mode = 'off' # should see green picture.. instead seeing black. First should auto fing the gain vaules and then lock them.
# piVideo.camera.iso = 800 # still dont know
# piVideo.camera.shutter_speed = 567160     # Assign shutter speed to non-zero first. Looks like max is 1/fps * 100000 - makes sense.
# piVideo.camera.exposure_mode = 'off'    # Lock gains and disable auto exposure. if off, way blacker frame :/

if __name__ == "__main__":
	camera = Camera()
	camera.startCamera()

	# camera.startLockingAwb()
	# while not camera.lockingAwbStopped:
	# 	time.sleep(.5)
	
	# camera.startAnalyzing()

	# while not camera.analyzingStopped:
	# 	time.sleep(.5)
	
	repeater = Repeater(camera.detectingCounter.print).start()
	camera.startDetecting()
