import os
import random

import vlc
from flask import Flask, render_template, send_file, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room

from configdict import ConfigDict
from utils import safe_name, check_file, find, run_task_later

config = ConfigDict("config.json", defaults={"volume": 100, "status": 0, "position": 0, "playing": None, "flags": {"repeat_all": False, "repeat_one": False, "random": False}})
app = Flask(__name__)
websocket = SocketIO(app, async_mode=None, manage_session=False)
player: vlc.MediaPlayer = vlc.MediaPlayer()
player.audio_set_volume(config.volume)
player_events: vlc.EventManager = player.event_manager()
ws_namespace = "/websocket"
music_folder = "music"
images_folder = "images"


class Status:
    stopped = 0
    playing = 1
    paused = 2


def ws_bc(*args, **kwargs):
    websocket.emit(*args, broadcast=True, namespace=ws_namespace, **kwargs)


def set_volume(vol):
    config.volume = vol
    player.audio_set_volume(vol)
    ws_bc("volume_set", vol)


def set_status(status):
    config.status = status
    config.save()
    ws_bc("status", {"status": config.status, "playing": config.playing})


def set_position(pos, save=True):
    if save:
        config.position = pos
        config.save()
    media = player.get_media()
    ws_bc("position_set", {"position": config.position, "duration": None if media is None else round(media.get_duration() / 1000)})


def play_media(music_name, save=True, start_playing=True):
    if save:
        config.playing = music_name
    player.set_media(vlc.Media(os.path.join(music_folder, music_name)))
    if start_playing:
        player.play()
        set_status(Status.playing)
    else:
        set_status(Status.paused)
    player.audio_set_volume(config.volume)


def pause_resume():
    if config.status == Status.playing:
        player.set_pause(True)
        set_status(Status.paused)
    elif config.status == Status.paused:
        if player.can_pause() == 0:
            player.play()
            player.set_position(config.position)
        player.set_pause(False)
        player.audio_set_volume(config.volume)
        set_status(Status.playing)


def stop():
    set_position(0)
    set_status(Status.stopped)


def on_end_reached(event: vlc.Event):
    flags = config.flags
    if flags["repeat_one"]:
        run_task_later(0.5, play_media, (config.playing, False))
    elif flags["repeat_all"]:
        all_musics = get_ordered_musics()
        if len(all_musics) < 3:
            change_flag("random", False)
        if flags["random"]:
            other_musics = all_musics.copy()
            other_musics.remove(config.playing)
            new_music = random.choice(other_musics)
        else:
            new_music = all_musics[(find(all_musics, config.playing) + 1) % len(all_musics)]
        run_task_later(0.5, play_media, (new_music,))
    else:
        stop()


def on_position_change(event: vlc.Event):
    set_position(player.get_position())


def get_music_data(music_file):
    return {"name": music_file, "image": find_image_for_music(music_file)}


def find_image_for_music(music):
    for i in os.listdir(images_folder):
        if i.startswith(music):
            return i
    return None


def get_ordered_musics():
    musics = os.listdir(music_folder)
    musics.sort()
    return musics


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/favicon.ico")
def favicon():
    return send_file("favicon.ico")


@app.route("/raspi")
def raspi():
    return render_template("raspi.html")


@app.get("/assets/<path:path>")
def get_asset(path):
    try:
        return send_file(f"assets/{path}")
    except OSError as e:
        return "File not found", 404


@websocket.on("connect", namespace=ws_namespace)
def on_connect():
    emit("volume_set", config.volume)
    emit("status", {"status": config.status, "playing": config.playing})
    media = player.get_media()
    emit("position_set", {"position": config.position, "duration": None if media is None else round(media.get_duration() / 1000)})
    emit("flags", config.flags)
    join_room("index", namespace=ws_namespace)


@websocket.on("disconnect", namespace=ws_namespace)
def on_disconnect():
    leave_room("index")
    leave_room("raspi")


@websocket.on("play", namespace=ws_namespace)
def on_play(message):
    if message is None:
        playing = config.playing
        if playing is not None:
            play_media(playing)
    else:
        play_media(message)


@websocket.on("pause", namespace=ws_namespace)
def on_pause():
    pause_resume()


@websocket.on("stop", namespace=ws_namespace)
def on_stop():
    player.stop()
    stop()


@websocket.on("volume_add", namespace=ws_namespace)
def on_volume_add(message):
    set = config.volume + message
    if set > 100:
        set = 100
    elif set < 0:
        set = 0
    set_volume(set)


@websocket.on("raspi", namespace=ws_namespace)
def on_raspi():
    join_room("raspi", namespace=ws_namespace)
    leave_room("index", namespace=ws_namespace)


@websocket.on("refreshpi", namespace=ws_namespace)
def refreshpi():
    ws_bc("refreshpi", to="raspi")


@websocket.on("position_set", namespace=ws_namespace)
def position_set(message):
    if message < 0:
        message = 0
    elif message > 1:
        message = 1
    player.set_position(message)
    set_position(message)


@websocket.on("position_add", namespace=ws_namespace)
def position_add(message):
    media: vlc.Media = player.get_media()
    if media is not None:
        duration = media.get_duration()
        new_pos = ((player.get_position() * duration) + message) / duration
        if new_pos < 0:
            new_pos = 0
        elif new_pos > 1:
            new_pos = 1
        player.set_position(new_pos)


def change_flag(flag, value, save=True):
    config_flags = config.flags
    if config_flags[flag] != value:
        config_flags[flag] = value
        if flag == "repeat_all":
            if value:
                change_flag("repeat_one", False, False)
            else:
                change_flag("random", False, False)
        elif flag == "repeat_one":
            if value:
                change_flag("repeat_all", False, False)
        elif flag == "random":
            if value:
                if not config_flags["repeat_all"]:
                    config_flags["random"] = False

    if save:
        config.save()
        ws_bc("flags", config_flags, to="index")


@websocket.on("set_flag", namespace=ws_namespace)
def set_flags(message):
    change_flag(message["flag"], message["value"])


@websocket.on("change_song", namespace=ws_namespace)
def change_song(add_index):
    all_musics = get_ordered_musics()
    new_music = all_musics[(find(all_musics, config.playing) + add_index) % len(all_musics)]
    play_media(new_music)


@app.post("/api/music")
def post_music():
    if 'file' not in request.files:
        return "Merci de sélectionner un fichier", 400
    file = request.files['file']
    if not file:
        return "Merci de sélectionner un fichier", 400
    if file.filename == '':
        return "Merci de sélectionner un fichier", 400
    if check_file(file.filename, "audio/*"):
        filename = safe_name(file.filename)
        file.save(os.path.join(music_folder, filename))
        ws_bc("music_add", get_music_data(filename), to="index")
        return "", 204
    else:
        return "Merci de sélectionner un fichier musical", 400


@app.delete("/api/music")
def delete_music():
    if 'file' not in request.args:
        return "Merci de spécifier un fichier", 400

    file = request.args['file']
    file_path = os.path.join(music_folder, file)
    if not os.path.exists(file_path):
        return "Music non trouvée", 404
    image = find_image_for_music(file)
    os.remove(file_path)
    if image:
        os.remove(os.path.join(images_folder, image))

    ws_bc("music_delete", file, to="index")

    return "", 204


@app.get("/api/music")
def get_music():
    files = []
    for f in get_ordered_musics():
        files.append(get_music_data(f))

    return jsonify(files)


@app.get("/api/music/image")
def get_music_image():
    if 'music' in request.args:
        music = request.args["music"]
        if not os.path.exists(os.path.join(music_folder, music)):
            return "Merci de spécifier une musique existante", 400
        file = find_image_for_music(music)
        if not file:
            return "La musique n'a pas d'image", 404
    else:
        if 'file' not in request.args:
            return "Merci de spécifier l'image à obtenir", 400
        file = request.args['file']
    try:
        return send_file(os.path.join(images_folder, file))
    except OSError:
        return "Image non trouvée", 404


@app.post("/api/music/image")
def post_music_image():
    if 'file' not in request.args:
        return "Merci de spécifier la musique à modifier", 400
    music_file = request.args['file']
    if not os.path.exists(os.path.join(music_folder, music_file)):
        return "Merci de spécifier une musique existante", 400
    if 'file' not in request.files:
        return "Merci de sélectionner un fichier", 400
    file = request.files['file']
    if not file:
        return "Merci de sélectionner un fichier", 400
    if file.filename == '':
        return "Merci de sélectionner un fichier", 400
    if check_file(file.filename, "image/*"):
        extension = file.filename.split(".")[-1]
        file.save(os.path.join(images_folder, music_file + "." + extension))
        ws_bc("music_add", get_music_data(music_file), to="index")
        return "", 204
    else:
        return "Merci de sélectionner un fichier image", 400


@app.delete("/api/music/image")
def delete_music_image():
    if 'file' not in request.args:
        return "Merci de spécifier la musique à modifier"
    music_file = request.args['file']
    if not os.path.exists(os.path.join(music_folder, music_file)):
        return "Merci de spécifier une musique existante"
    image = find_image_for_music(music_file)
    if image:
        os.remove(os.path.join(images_folder, image))

    ws_bc("music_add", get_music_data(music_file), to="index")
    return "", 204


player_events.event_attach(vlc.EventType.MediaPlayerEndReached, on_end_reached)
player_events.event_attach(vlc.EventType.MediaPlayerPositionChanged, on_position_change)

if __name__ == '__main__':
    status = config.status
    if status != Status.stopped:
        if status == Status.playing:
            play_media(config.playing, False)
        elif status == Status.paused:
            play_media(config.playing, False, False)
        set_position(config.position, False)
        player.set_position(config.position)

    websocket.run(app, port=8000, host="0.0.0.0", debug=True, use_reloader=False)
