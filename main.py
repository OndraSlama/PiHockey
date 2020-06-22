from App.AirHockeyApp import AirHockeyApp
import os

def main():
	## Initialize objects -------------
	app = AirHockeyApp()
	app.run()
	os._exit(1)

if __name__ == "__main__":
	main()

