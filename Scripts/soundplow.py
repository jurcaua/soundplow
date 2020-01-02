import os
import re
import requests
import soundcloud

import mutagen
from mutagen.id3 import ID3, APIC
from mutagen.easyid3 import EasyID3

import controller
from log import Log

FORBIDDEN_CHARACTERS = ['/', '\\', '?', '%', '*', ':', '|', '"', '<', '>']

def format_title(track):
    """ We want a title format of: [artist name] - [song title].
        So if the song title does not already include the artist name or is not in the format we're looking for,
        then we format it like that ourselves.
    """
    if track.user['username'].lower() not in track.title.lower() and re.search(".* - .*", track.title.lower()) is None:
        song_title = '{user} - {title}'.format(user=track.user['username'], title=track.title)
    else:
        song_title = track.title

    # Clean up bad characters in names
    for c in FORBIDDEN_CHARACTERS:
        if c in song_title:
            song_title = song_title.replace(c, '')

    return song_title

def add_title_to_mp3(filepath, title):
    try:
        meta = EasyID3(filepath)
    except mutagen.id3.ID3NoHeaderError:
        meta = mutagen.File(filepath, easy=True)
        meta.add_tags()

    meta['title'] = title
    meta.save()

class Soundplow(object):
    def __init__(self, client_id):
        self.controller = None
        self.client_id = client_id
        self.current_user_id = None

        self.output_path = controller.DEFAULT_OUTPUT
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)

    def set_controller(self, controller):
        self.controller = controller

    def load(self):
        self.api = soundcloud.Client(client_id=self.client_id)

    def set_user(self, username):
        self.current_user_id = self.get_user(username).id

    def get_track(self, track_id):
        return self.api.get('/tracks/{track_id}'.format(track_id=track_id))

    def get_user(self, username):
        try:
            user = self.api.get('/resolve', url='http://soundcloud.com/' + username)
        except requests.exceptions.HTTPError as e:
            Log.instance().warning("Invalid user \"{username}\" entered! Please try again with a valid user.".format(username=username))
            user = None

        return user

    def get_track_name(self, track_id):
        return format_title(self.get_track(track_id))

    def download_by_url(self, track_url):
        # Gets track id from url and passes to below function
        try:
            html = requests.get(track_url)
        except requests.exceptions.MissingSchema:
            Log.instance().warning("Invalid url \"{url}\" entered. Please enter a valid soundcloud link.".format(url=track_url))
            return
        track_id = (re.search(r'soundcloud://sounds:(.+?)"', html.text).group(1))

        Log.instance().info("Got track id {track_id} from {url}!".format(track_id=track_id, url=track_url))

        self.download_by_id(track_id)

    def download_by_id(self, track_id):
        # Get track data
        track = self.get_track(track_id)

        # Proper formatted title according to the track data (username, song title, etc)
        formatted_song_title = format_title(track)

        if not os.path.isdir(self.output_path):
            Log.instance().error("Output path {path} does not exist! Aborting.".format(path=file_path))
            return

        # Build file path and and make sure the file does not already exist
        file_path = self.output_path + '\\' + formatted_song_title + '.mp3'
        if os.path.isfile(file_path):
            Log.instance().warning("File already exists at {path}! Aborting.".format(path=file_path))
            return

        # Request to get where they host the stream of the song
        stream_url = " https://api.soundcloud.com/i1/tracks/{0}/streams?client_id={1}".format(track_id, self.client_id)
        final_page = requests.get(stream_url)

        # Make the request to get the actual MP3 file of the song
        try:
            mp3_url = final_page.json()['http_mp3_128_url']
        except KeyError:
            Log.instance.error("KeyError with json: {}".format(final_page.json()))
            return
        mp3_request = requests.get(mp3_url)

        # Create MP3 file and add title metadata
        open(file_path, 'wb').write(mp3_request.content)
        add_title_to_mp3(file_path, formatted_song_title)

        Log.instance().success("Downloaded track: \"{title}\"".format(title=formatted_song_title))

    def search_for_songs(self, query):
        if query is None or query == "":
            Log.instance().warning("Please enter a non-empty search query.")
            return

        tracks = self.api.get('/tracks', q=query)
        if isinstance(tracks, soundcloud.resource.ResourceList):
            for i in range(len(tracks.data)):
                yield tracks.data[i]
        else:
            yield tracks

    def get_last_liked(self):
        if self.current_user_id is None:
            Log.instance().error("No user was entered! Please enter a username.")
            return
        try:
            liked_tracks = self.api.get('/users/{id}/favorites'.format(id=self.current_user_id))
        except requests.exceptions.HTTPError:
            Log.instance().warning("Unexpected Soundcloud API error. Will try again.")
            return
        if len(liked_tracks) > 0:
            return [track.id for track in liked_tracks]
        else:
            return []
