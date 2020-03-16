from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image

class MyApp(App):

    def build(self):
        bl = BoxLayout()
        for i in range(5000):
            bl.add_widget(Image(source="icons/no-video.png"))
        return bl

MyApp().run()