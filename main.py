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

