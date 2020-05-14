from math import floor

# ----------- ENUM -------------
AI = 0
HUMAN = 1

# ------------- DIMENSIONS -------------
# Field dimensions in game units
FIELD_WIDTH = 1000
FIELD_HEIGHT = 600
GOAL_SPAN = 240
CHAMBER_SIZE = 30 # on both size - eg: 30 = 30mm x 30mm

# Limits
YLIMIT = 230
XLIMIT = 70
STRIKER_AREA_WIDTH = 450

# Objects sizes in game units
PUCK_RADIUS = 32
STRIKER_RADIUS = 50

# -------------- STRATEGY --------------
DEFENSE_LINE = STRIKER_RADIUS + PUCK_RADIUS
STOPPING_LINE = 200
CLOSE_DISTANCE = PUCK_RADIUS # what is considered to be "close enough"

# -------------- MOTORS --------------
# Striker limitations
MAX_ACCELERATION = 30000
MAX_DECELERATION = 100000
MAX_SPEED = 3000
KP_GAIN = MAX_DECELERATION/(MAX_SPEED*2)

# -------------- Data collector --------------
CLIP_LENGTH = 5 #seconds
CLIP_BEFORE_AFTER_RATIO = 7/10 # cant be zero
CLIP_FRAMERATE = 10

