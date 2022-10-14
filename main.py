import json
import os
import threading
import time
import datetime
import cv2
from random import random
from urllib.parse import urlparse
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.switch import Switch
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.config import Config
from kivy.core.window import Window

APP_FOLDER = os.path.realpath(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(APP_FOLDER, 'config.json')

Window.minimum_height = 480
Window.minimum_width = 640
Window.size = (800, 600)

Config.set('input', 'mouse', 'mouse, multitouch_on_demand')
config = {
    'images_folder': '',
    'sources': {}
}


def update_config():
    with open('config.json', 'w') as file:
        json.dump(config, file)


class AppLayout(Widget):
    active_captures = []

    def switch_widget_state(self, widgets: tuple, state: bool):
        for w in widgets:
            w.disabled = state

    def start_capture(self, switch):
        if not switch.parent.id in self.active_captures:
            self.active_captures.append(switch.parent.id)
        else:
            return

        for child in switch.parent.children:
            try:
                match child.id:
                    case 'source': source = child.text
                    case 'interval': interval = int(child.text)
                    case 'quality': quality = int(child.text)
            except:
                pass

        video_src = cv2.VideoCapture(source)
        capture_folder = os.path.join(config['images_folder'], switch.parent.id,
                                      datetime.datetime.now().strftime("%d%m%y-%H%M%S-%f"))

        if video_src.isOpened():
            switch.disabled = False
            start_capture_time = time.time()
            os.makedirs(capture_folder)

        while (switch.active):
            current_time = time.time()
            file_name = f'{datetime.datetime.now().strftime("%d%m%y-%H%M%S-%f")}.jpg'
            path = os.path.join(capture_folder, file_name)
            retrieve, frame = video_src.read()

            if not video_src or not video_src.isOpened() or not retrieve:
                break

            if current_time - start_capture_time > interval:
                start_capture_time = current_time
                if retrieve:
                    cv2.imwrite(path, frame,
                                [cv2.IMWRITE_JPEG_QUALITY, quality])
        self.active_captures.remove(switch.parent.id)
        switch.active = False
        switch.disabled = False
        video_src.release()

    def switch_capture(self, switch, value):
        src_wrapper = switch.parent

        for child in src_wrapper.children:
            try:
                match child.id:
                    case 'source': source = child
                    case 'interval': interval = child
                    case 'quality': quality = child
                    case 'remove': remove = child
            except:
                pass

        user_url = urlparse(source.text)

        if switch.active and user_url.scheme == 'rtsp' and os.path.exists(config['images_folder']):
            self.switch_widget_state(
                (source, interval, quality, switch, remove), True)
            t = threading.Thread(target=self.start_capture, args=(switch,))
            t.daemon = True
            t.start()
        else:
            switch.active = False
            self.switch_widget_state(
                (source, interval, quality, remove), False)

    def check_source(self, instance, value):
        config['sources'][instance.parent.id]['source'] = value
        update_config()

    def check_interval(self, instance, focus):
        if focus:
            return

        value = instance.text
        if value and 0 < int(value):
            config['sources'][instance.parent.id]['interval'] = value
            update_config()

        instance.text = config['sources'][instance.parent.id]['interval']

    def check_quality(self, instance, focus):
        if focus:
            return

        value = instance.text
        if value and 0 < int(value) < 101:
            config['sources'][instance.parent.id]['quality'] = value
            update_config()

        instance.text = config['sources'][instance.parent.id]['quality']

    def dir_only(self, _, filename):
        return os.path.isdir(filename)

    def get_images_dir(self):
        return config['images_folder'] if config['images_folder'] else APP_FOLDER

    def set_images_dir(self, path):
        config['images_folder'] = path
        self.ids.images_folder.text = path
        update_config()

    def remove_capture(self, instance):
        capture_list = self.ids.capture_list
        capture_list.remove_widget(instance.parent)
        del config['sources'][instance.parent.id]
        update_config()

    def add_capture(self, source_id=None, source_info=None):
        capture_list = self.ids.capture_list
        if not source_id and not source_info:
            source_id = str(random())[2:8]
            source_info = {
                'source': '',
                'interval': '1',
                'quality': '100'
            }
            config['sources'][source_id] = source_info
            update_config()

        capture_wrapper = BoxLayout()
        id_label = Label(
            text=f'[ref=id]{source_id}[/ref]', size_hint=(.35, 1), markup=True)
        source_input = TextInput(text=source_info['source'],
                                 hint_text='rtsp://user:password@address:port',
                                 multiline=False, size_hint=(1, 1))
        interval_input = TextInput(text=source_info['interval'], input_filter='int',
                                   multiline=False, size_hint=(.25, 1))
        quality_input = TextInput(text=source_info['quality'], input_filter='int',
                                  multiline=False, size_hint=(.25, 1))
        switch_widget = Switch(size_hint=(.5, 1))
        remove_button = Button(text='X', size_hint=(.15, 1))

        capture_wrapper.id = source_id
        source_input.id = 'source'
        interval_input.id = 'interval'
        quality_input.id = 'quality'
        remove_button.id = 'remove'

        source_input.bind(text=self.check_source)
        interval_input.bind(focus=self.check_interval)
        quality_input.bind(focus=self.check_quality)
        switch_widget.bind(active=self.switch_capture)
        remove_button.bind(on_press=self.remove_capture)

        for widget in (id_label, source_input, interval_input,
                       quality_input, switch_widget, remove_button):
            capture_wrapper.add_widget(widget)
        capture_list.add_widget(capture_wrapper)


class RtsptimelapseApp(App):

    def open_settings(self, *args):
        pass

    def build(self):
        self.title = 'RTSP Timelapse'
        self.icon = 'icon.png'
        return AppLayout()

    def on_start(self):
        path_label = self.root.ids.images_folder

        if not os.path.exists(config['images_folder']):
            config['images_folder'] = APP_FOLDER
            update_config()

        path_label.text = config['images_folder']

        for id in config['sources']:
            self.root.add_capture(id, config['sources'][id])


if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, 'r') as file:
        config = json.load(file)
else:
    update_config()

RtsptimelapseApp().run()
