import sys
import configparser
from threading import Timer

import soundplow
from log import Log

DEFAULT_OUTPUT = r'D:\Music'
DEFAULT_LIKE_CHECK_INTERVAL = 1.0
DEFAULT_MAX_LIKE_CHECK = 10
DEFAULT_SEARCH_RESULTS = 5

CONFIG_FILE = 'resources/settings.ini'

class Repeater(object):
    def __init__(self, interval, event):
        self.interval = interval
        self.event = event
        self.timer = Timer(self.interval, self.handle_event)

    def handle_event(self):
        self.event()
        self.start()

    def start(self):
        del self.timer
        self.timer = Timer(self.interval, self.handle_event)
        self.timer.start()

    def stop(self):
        self.timer.cancel()

class Controller(object):
    def __init__(self):
        self.ui = None
        self.listening_for_likes = False
        self.previous_likes = None
        self.like_listener = Repeater(DEFAULT_LIKE_CHECK_INTERVAL, lambda: self.download_new_likes(self.model.get_last_liked()))

    def load(self):
        self.load_settings()

    def load_settings(self):
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)

        if 'general' in config:
            if 'output' in config['general']:
                self.ui.output_textbox.set_text(config['general']['output'])
            else:
                config['general']['output'] = DEFAULT_OUTPUT
        else:
            config['general'] = {}
            config['general']['output'] = DEFAULT_OUTPUT

        if 'like' in config and 'like' in self.ui.tabs:
            if 'user' in config['like']:
                self.ui.tabs['like'].textbox.set_text(config['like']['user'])
            else:
                config['like']['user'] = ''
        else:
            config['like'] = {}
            config['like']['user'] = ''

        if 'link' in config and 'link' in self.ui.tabs:
            if 'tracks' in config['link']:
                tracks = config['link']['tracks'].split(',')
                for track in tracks:
                    if track is not '':
                        self.ui.track_list.add_item(track)
            else:
                config['link']['tracks'] = ''
        else:
            config['link'] = {}
            config['link']['tracks'] = ''

        with open(CONFIG_FILE, 'w') as config_file:
            config.write(config_file)

    def save_settings(self):
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)

        config['general']['output'] = self.ui.output_textbox.get_text()

        if 'like' in self.ui.tabs:
            config['like']['user'] = self.ui.tabs['like'].textbox.get_text()

        if 'link' in self.ui.tabs:
            tracks = ''
            for track in self.ui.track_list.get_items():
                tracks = tracks + track + ','
            if len(tracks) > 0 and tracks[-1] is ',':
                tracks = tracks[:-1]
            config['link']['tracks'] = tracks

        with open(CONFIG_FILE, 'w') as config_file:
            config.write(config_file)

    def set_ui(self, ui):
        self.ui = ui

    def set_model(self, model):
        self.model = model

    def log(self, text):
        self.ui.log.log(text)

    def close_app(self, return_value=0):
        self.like_listener.stop()

        self.save_settings()

        sys.exit(return_value)

    def download_track_by_id(self, track_id):
        self.model.download_by_id(track_id)

    def batch_download_urls(self, urls):
        num_songs = 0
        for url in urls:
            num_songs += 1
            Log.instance().info("* Song {song_num}: {url}".format(song_num=num_songs, url=url))
            self.model.download_by_url(url)

        Log.instance().success("--- Operation complete, {num_songs} urls processed! ---".format(num_songs=num_songs))

    def toggle_listen_for_likes(self, user):
        if user is None or user is '':
            Log.instance().error("No user entered!")
            return

        if self.model.get_user(user) is None:
            return

        self.listening_for_likes = not self.listening_for_likes
        self.ui.tabs['like'].button.toggle_text()

        if self.listening_for_likes:
            self.model.set_user(user)
            self.like_listener.start()

            Log.instance().info("Started listening for likes from user: \"{user}\"".format(user=user))
        else:
            self.like_listener.stop()

            Log.instance().info("Stopped listening for likes from user: \"{user}\"".format(user=user))

    def download_new_likes(self, last_likes):
        if last_likes is None or last_likes is []:
            return

        if self.previous_likes is None:
            self.previous_likes = last_likes
        else:
            difference = [track_id for track_id in last_likes if track_id not in self.previous_likes and last_likes.index(track_id) < DEFAULT_MAX_LIKE_CHECK]
            if len(difference) > 0:
                for track_id in difference:
                    Log.instance().info("Liked song found: {name}, downloading now...".format(name=self.model.get_track_name(track_id)))
                    self.model.download_by_id(track_id)
            self.previous_likes = last_likes

    def get_search_results(self, query, num_results=DEFAULT_SEARCH_RESULTS):
        count = 0
        results = []
        for track in self.model.search_for_songs(query):
            if track is None:
                break
            results.append(track)
            count += 1
            if count > DEFAULT_SEARCH_RESULTS:
                break
        return results

    def get_track_name(self, track):
        return soundplow.format_title(track)
