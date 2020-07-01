# ****************************************************************************** #
# Author: Ondrej Slama
# -------------------

# Zdrojovy kod vytvoreny v ramci projektu robotickeho vzdusneho hokeje - diplomova prace
#  na VUT FSI ustavu automatizace a informatiky v Brne.

# Source code created as a part of robotic air hockey table project - Diploma thesis
# at BUT FME institute of automation and computer sience.

# ****************************************************************************** #
from App.AirHockeyApp import AirHockeyApp
import os

def main():
	## Initialize objects -------------
	try:
		app = AirHockeyApp()
		app.run()
	except:
		print("Internal disater occured... restart application.")
	os._exit(1)

if __name__ == "__main__":
	main()

