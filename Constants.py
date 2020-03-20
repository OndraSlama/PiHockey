from math import floor

# ----------- ENUM -------------
AI = 0
HUMAN = 1

# ------------- DIMENSIONS -------------
# Field dimensions in game units
FIELD_WIDTH = 1000
FIELD_HEIGHT = 600
GOAL_SPAN = 240
STRIKER_AREA_WIDTH = 445

# Objects sizes in game units
PUCK_RADIUS = 32
STRIKER_RADIUS = 120

# -------------- STRATEGY --------------
DEFENSE_LINE = STRIKER_RADIUS + PUCK_RADIUS
STOPPING_LINE = FIELD_WIDTH/6
CLOSE_DISTANCE = PUCK_RADIUS # what is considered to be "close enough"

# -------------- LIMITS --------------
# Striker limitations
MAX_ACCELERATION = 10000
MAX_SPEED = 1000

# -------------- RULES --------------
GOAL_LIMIT = 3
TIME_LIMIT = 120 #seconds
