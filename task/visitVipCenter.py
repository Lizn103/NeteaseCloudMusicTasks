def start(user, task={}):
    music = user.music

    resp = music.yunbei_click_task(6758460, "weibo", "feizhu", "")
    if resp['code'] == 200:
        user.taskInfo(task['taskName'], '浏览成功')
    else:
        user.taskInfo(task['taskName'], user.errMsg(resp))
