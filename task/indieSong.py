import random
import time


def start(user, task={}):
    music = user.music

    resp = music.yunbei_distribution_recommend_song(0, 10)
    if resp['code'] != 200 or not resp.get('data'):
        user.taskInfo(task['taskName'], '获取推荐歌曲失败')
        return

    songs = resp['data']
    ids = [s['songId'] for s in songs]
    details = music.songs_detail(ids)
    album_map = {}
    for song in details.get('songs', []):
        album_map[song['id']] = song['al']['id']

    for song in songs:
        song_id = song['songId']
        album_id = album_map.get(song_id, 0)
        listen = music.trialsong_listen(song_id, album_id, 1)
        if listen['code'] == 200:
            user.taskInfo(task['taskName'], '听歌打卡', '歌曲ID:' + str(song_id))
        else:
            user.taskInfo(task['taskName'], '歌曲' + str(song_id) + '听歌上报失败:' + user.errMsg(listen))
        resp = music.yunbei_distribution_create(150)
        if resp['code'] == 200:
            user.taskInfo(task['taskName'], '云贝+150')
        time.sleep(random.randint(30, 40))

    user.taskInfo(task['taskName'], '探索小众歌曲打卡完毕')
