import random


def start(user, task={}):
    music = user.music

    if len(task['songId']) == 0:
        user.taskInfo(task['taskName'], '请填写歌曲id')
        return

    songId = random.choice(task['songId'])
    resp = music.song_like(songId, user.uid)
    if resp['code'] == 200:
        user.taskInfo(task['taskName'], '红心成功，歌曲ID为'+str(songId))
    else:
        user.taskInfo(task['taskName'], '歌曲' + str(songId) + '红心失败:' + user.errMsg(resp))
