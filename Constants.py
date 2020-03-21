from math import floor

# ----------- ENUM -------------
AI = 0
HUMAN = 1

# ------------- DIMENSIONS -------------
# Field dimensions in game units
FIELD_WIDTH = 1000
FIELD_HEIGHT = 600
GOAL_SPAN = 240

# Limits
YLIMIT = 230
XLIMIT = 70
STRIKER_AREA_WIDTH = 450

# Objects sizes in game units
PUCK_RADIUS = 32
STRIKER_RADIUS = 50

# -------------- STRATEGY --------------
DEFENSE_LINE = STRIKER_RADIUS + PUCK_RADIUS
STOPPING_LINE = 350
CLOSE_DISTANCE = PUCK_RADIUS # what is considered to be "close enough"

# -------------- LIMITS --------------
# Striker limitations
MAX_ACCELERATION = 10000
MAX_SPEED = 1000

