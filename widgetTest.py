from kivy.app import App
from kivy.garden.joystick import Joystick
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

class DemoApp(App):
  def build(self):
    self.root = BoxLayout()
    self.root.padding = 50
    joystick = Joystick()
    # joystick.bind(pad=self.update_coordinates)
    self.root.add_widget(joystick)
    self.label = Label()
    self.root.add_widget(self.label)
#   def update_coordinates(self, joystick, pad):
#     x = str(pad[0])[0:5]
#     y = str(pad[1])[0:5]
#     radians = str(joystick.radians)[0:5]
#     magnitude = str(joystick.magnitude)[0:5]
#     angle = str(joystick.angle)[0:5]
#     text = "x: {}\ny: {}\nradians: {}\nmagnitude: {}\nangle: {}"
#     self.label.text = text.format(x, y, radians, magnitude, angle)

DemoApp().run()