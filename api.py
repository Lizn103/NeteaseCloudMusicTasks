# -*- coding: utf-8 -*-
import platform
import json
import os
import time
import requests
from http.cookiejar import Cookie, LWPCookieJar
from encrypt import encrypted_request, eapi_encrypt, eapi_decrypt
import random
from hashlib import md5

DEFAULT_TIMEOUT = 10

BASE_URL = "https://music.163.com"


class NetEase(object):
    def __init__(self, username=''):
        self.header = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip,deflate,sdch",
            "Accept-Language": "zh-CN,zh;q=0.8,gl;q=0.6,zh-TW;q=0.4",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "music.163.com",
            "Referer": "https://music.163.com",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36",
        }
        username = str(username)
        self.username = username
        self.session = requests.Session()

        cookie_file = self.get_cookie_file(username)
        if username and cookie_file:
            cookie_jar = LWPCookieJar(cookie_file)
            cookie_jar.load()
        else:
            cookie_jar = LWPCookieJar()
        self.session.cookies = cookie_jar


    def get_cookie_file(self, filename):
        if len(filename) == 0:
            return None
        data_dir = os.path.join(os.path.expanduser("."), ".user_data")
        user_path = os.path.join(data_dir, filename)
        cookie_file = os.path.join(user_path, "cookie")
        if not os.path.exists(data_dir):
            try:
                os.makedirs(data_dir)
            except:
                return None
        if not os.path.exists(user_path):
            try:
                os.makedirs(user_path)
            except:
                return None

        if not os.path.exists(cookie_file):
            try:
                with open(cookie_file, "w", encoding="utf-8") as f:
                    f.write('#LWP-Cookies-2.0\nSet-Cookie3:')
                    f.close()
            except:
                return None

        return cookie_file

    def _raw_request(self, method, endpoint, data=None):
        if method == "GET":
            resp = self.session.get(
                endpoint, params=data, headers=self.header, timeout=DEFAULT_TIMEOUT
            )
        elif method == "POST":
            resp = self.session.post(
                endpoint, data=data, headers=self.header, timeout=DEFAULT_TIMEOUT
            )
        return resp

    # 生成Cookie对象
    def make_cookie(self, name, value):
        return Cookie(
            version=0,
            name=name,
            value=value,
            port=None,
            port_specified=False,
            domain="music.163.com",
            domain_specified=True,
            domain_initial_dot=False,
            path="/",
            path_specified=True,
            secure=False,
            expires=None,
            discard=False,
            comment=None,
            comment_url=None,
            rest={},
        )

    def request(self, method, path, params={}, base_url=BASE_URL, default={"code": -1}, custom_cookies={'os': 'pc'}):
        endpoint = "{}{}".format(BASE_URL, path)
        csrf_token = ""
        for cookie in self.session.cookies:
            if cookie.name == "__csrf":
                csrf_token = cookie.value
                break
        params.update({"csrf_token": csrf_token})
        data = default

        for key, value in custom_cookies.items():
            cookie = self.make_cookie(key, value)
            self.session.cookies.set_cookie(cookie)

        params = encrypted_request(params)
        try:
            resp = self._raw_request(method, endpoint, params)
            data = resp.json()
        except requests.exceptions.RequestException as e:
            print(e)
        except ValueError as e:
            print("Path: {}, response: {}".format(path, resp.text[:200]))
        finally:
            return data

    def login(self, username, password, countrycode='86'):
        username = str(username)
        cookie_file = self.get_cookie_file(username)
        if cookie_file:
            if self.username != username:
                cookie_jar = LWPCookieJar(cookie_file)
                cookie_jar.load()
                self.session.cookies = cookie_jar
                self.username = username
        if len(password) < 32:
            password = md5(password.encode(encoding='UTF-8')).hexdigest()
        if username.isdigit():
            path = "/weapi/login/cellphone"
            if len(countrycode) == 0:
                countrycode = '86'
            params = dict(phone=username, countrycode=countrycode,
                          password=password, rememberLogin="true")
        else:
            # magic token for login
            # see https://github.com/Binaryify/NeteaseCloudMusicApi/blob/master/router/login.js#L15
            client_token = (
                "1_jVUMqWEPke0/1/Vu56xCmJpo5vP1grjn_SOVVDzOc78w8OKLVZ2JH7IfkjSXqgfmh"
            )
            path = "/weapi/login"
            params = dict(username=username, password=password,
                          rememberLogin="true", clientToken=client_token)
        data = self.request("POST", path, params)

        if cookie_file:
            self.session.cookies.save()
        return data

    # 每日签到
    # type=1 为 PC/Web 端签到，网易云已关闭安卓端(type=0)签到接口，返回"功能暂不支持"
    def daily_task(self, type=1):
        path = "/weapi/point/dailyTask"
        params = dict(type=type)
        return self.request("POST", path, params)

    # 新版 eapi 请求 (网易云 2025+ 移动端接口), 参考 https://github.com/3899/ncmm
    # cookie 参数传原始 cookie 字符串时, 使用该 cookie 直接请求 (避免 session 附加 cookie 改变接口返回结构)
    def request_eapi(self, path, params={}, host="https://interface3.music.163.com", os="android", cookie=""):
        endpoint = host + "/eapi" + (path[4:] if path.startswith("/api/") else path)
        csrf_token = ""
        music_u = ""
        if cookie:
            for piece in cookie.split(";"):
                kv = piece.strip().split("=", 1)
                if len(kv) == 2:
                    if kv[0].strip() == "__csrf":
                        csrf_token = kv[1].strip()
                    if kv[0].strip() == "MUSIC_U":
                        music_u = kv[1].strip()
        else:
            for ck in self.session.cookies:
                if ck.name.strip() == "__csrf":
                    csrf_token = ck.value
                if ck.name.strip() == "MUSIC_U":
                    music_u = ck.value
        header = {
            "osver": "",
            "deviceId": "",
            "appver": "8.10.10",
            "versioncode": "140",
            "mobilename": "",
            "buildver": str(int(time.time())),
            "resolution": "1920x1080",
            "__csrf": csrf_token,
            "os": os,
            "channel": "",
            "requestId": "{}_{:04d}".format(
                int(time.time() * 1000), random.randint(0, 9999)),
        }
        if music_u:
            header["MUSIC_U"] = music_u
        params = dict(params)
        params["header"] = json.dumps(header)
        if "e_r" not in params:
            params["e_r"] = "true"
        data = eapi_encrypt(path, params)
        try:
            if cookie:
                resp = requests.post(endpoint, data=data, headers={
                    **self.header, "Cookie": cookie,
                    "Content-Type": "application/x-www-form-urlencoded"},
                    timeout=DEFAULT_TIMEOUT)
            else:
                resp = self._raw_request("POST", endpoint, data)
            raw = resp.content
            decrypted = eapi_decrypt(raw)
            return json.loads(decrypted)
        except requests.exceptions.RequestException as e:
            print(e)
            return {"code": -1}
        except ValueError as e:
            print("Path: {}, response: {}".format(path, resp.text[:200]))
            return {"code": -1}

    # 红心歌曲 (添加到"我喜欢的音乐")
    def song_like(self, song_id, user_id):
        path = "/api/song/like"
        params = dict(trackId=str(song_id), userid=str(user_id), like=True)
        return self.request_eapi(path, params, host="https://interface.music.163.com")

    # 红心歌曲 (ncmm 参数格式, 用于黑胶 VIP 任务"红心3首VIP单曲"; like="false" 取消红心)
    def vip_song_like(self, song_id, like="true"):
        path = "/api/song/like"
        params = dict(trackId=str(song_id), like=like, time="3", checkToken="")
        return self.request_eapi(path, params, host="https://interface.music.163.com")

    # 歌单详情 (v6 明文接口, 可获取完整 trackIds, 参考 ncmm PlaylistDetail)
    def playlist_detail_v6(self, playlist_id):
        url = "https://music.163.com/api/v6/playlist/detail"
        try:
            resp = self.session.get(url, params={"id": playlist_id, "n": "100000", "s": "8"}, timeout=DEFAULT_TIMEOUT)
            return resp.json()
        except requests.exceptions.RequestException as e:
            print(e)
            return {"code": -1}

    # 黑胶 VIP 任务列表 (每日任务: 红心3首/免费领福利/设置开机启动图等)
    def vip_task_list(self, cookie=""):
        path = "/api/vip-center-bff/task/list"
        params = dict(verifyId=1, isNew=1)
        return self.request_eapi(path, params, os="iOS", cookie=cookie)

    # 商家福利券列表 (category=1291816 为常驻商家福利)
    def vip_benefit_list(self, category="1291816"):
        path = "/api/vipnewcenter/app/benefitcenter/benefits/category/list"
        return self.request_eapi(path, params=dict(category=category))

    # 领取商家福利券
    def vip_benefit_get(self, benefit_id):
        path = "/api/vipcenter/benefits/get"
        return self.request_eapi(path, params=dict(id=str(benefit_id)))

    # 上报中台页面浏览 (模拟 App WebView, 用于"查看AI调音大师"等浏览类任务)
    def vip_page_view_report(self, data, webkit_context=""):
        csrf_token = ""
        for cookie in self.session.cookies:
            if cookie.name == "__csrf":
                csrf_token = cookie.value
                break
        url = "https://interface.music.163.com/weapi/middle/page/view/report"
        params = dict(data=json.dumps(data), csrf_token=csrf_token)
        params = encrypted_request(params)
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 CloudMusic/0.1.1 NeteaseMusic/9.4.95",
            "Host": "interface.music.163.com",
            "Origin": "https://music.163.com",
            "Referer": "https://music.163.com/",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        if webkit_context:
            headers["netease_webkit_context"] = webkit_context
        try:
            resp = self.session.post(url, data=params, headers=headers, timeout=DEFAULT_TIMEOUT)
            return resp.json()
        except requests.exceptions.RequestException as e:
            print(e)
            return {"code": -1}

    # 云贝任务点击上报 (浏览会员中心等)
    def yunbei_click_task(self, task_id, sub_action="", type_="", check_token=""):
        path = "/api/yunbei/click/task"
        params = dict(taskId=task_id, subAction=sub_action,
                      type=type_, checkToken=check_token)
        return self.request_eapi(path, params)

    # 上报听歌打卡 (探索小众歌曲)
    def trialsong_listen(self, song_id, album_id, scene=1):
        path = "/api/vipmall/interest/trialsong/listen"
        params = dict(songId=str(song_id), albumId=str(album_id), scene=scene)
        return self.request_eapi(path, params)

    # 探索小众歌曲推荐列表
    def yunbei_distribution_recommend_song(self, offset=0, limit=10):
        path = "/api/ad/power/yunbei/distribution/recommend/song"
        params = dict(offset=offset, limit=limit)
        return self.request_eapi(path, params)

    # 探索小众歌曲听歌完成申请云贝分配凭证
    def yunbei_distribution_create(self, amount=150):
        path = "/api/ad/power/yunbei/distribution/create"
        params = dict(yunbeiAmount=amount)
        return self.request_eapi(path, params)

    # 用户歌单
    def user_playlist(self, uid, offset=0, limit=50, includeVideo=True):
        path = "/weapi/user/playlist"
        params = dict(uid=uid, offset=offset, limit=limit,
                      includeVideo=includeVideo)
        return self.request("POST", path, params)

    # 创建歌单 privacy:0 为普通歌单，10 为隐私歌单；type:NORMAL正常|VIDEO视频|SHARED共享
    def playlist_create(self, name, privacy=0, ptype='NORMAL'):
        path = "/weapi/playlist/create"
        params = dict(name=name, privacy=privacy, type=ptype)
        return self.request("POST", path, params)

    # 添加/删除单曲到歌单
    # op:'add'|'del'
    def playlist_tracks(self, pid, ids, op='add'):
        path = "/weapi/playlist/manipulate/tracks"
        params = {'op': op, 'pid': pid,
                  'trackIds': json.dumps(ids), 'imme': 'true'}
        result = self.request("POST", path, params)
        if result['code'] == 512:
            ids.extend(ids)
            params = {'op': op, 'pid': pid,
                      'trackIds': json.dumps(ids), 'imme': 'true'}
            result = self.request("POST", path, params)
        return result

    # 更新歌单描述
    def playlist_desc_update(self, id, desc):
        path = "/weapi/playlist/desc/update"
        params = dict(id=id, desc=desc)
        return self.request("POST", path, params)

    # 每日推荐歌单
    def recommend_resource(self):
        path = "/weapi/v1/discovery/recommend/resource"
        return self.request("POST", path).get("recommend", [])

    # 推荐歌单
    def personalized_playlist(self, limit=9):
        path = "/weapi/personalized/playlist"
        params = dict(limit=limit)
        return self.request("POST", path, params).get("result", [])

    # 私人FM
    def personal_fm(self):
        path = "/weapi/v1/radio/get"
        return self.request("POST", path)  # .get("data", [])

    # 歌单详情
    def playlist_detail(self, playlist_id):
        path = "/weapi/v3/playlist/detail"
        params = dict(id=playlist_id, total="true",
                      limit=1000, n=1000, offest=0)
        # cookie添加os字段
        custom_cookies = dict(os=platform.system())
        return self.request("POST", path, params, {"code": -1}, custom_cookies)

    # 专辑详情
    def album(self, album_id):
        path = "/weapi/v1/album/{}".format(album_id)
        return self.request("POST", path)  # .get("songs", [])

    # 歌曲详情
    def songs_detail(self, ids):
        path = "/weapi/v3/song/detail"
        params = dict(c=json.dumps([{"id": _id}
                      for _id in ids]), ids=json.dumps(ids))
        return self.request("POST", path, params)

    # 关注用户
    def user_follow(self, id):
        path = "/weapi/user/follow/{}".format(id)
        return self.request("POST", path)

    # 听歌排行 type: 0 全部时间 1最近一周
    def play_record(self, uid, time_type=0, limit=1000, offset=0, total=True):
        path = "/weapi/v1/play/record"
        params = dict(uid=uid, type=time_type, limit=limit,
                      offset=offset, total=total)
        return self.request("POST", path, params)

    # 创建歌单 privacy:0 为普通歌单，10 为隐私歌单；type:NORMAL|VIDEO
    def playlist_creat(self, name, privacy=0, ptype='NORMAL'):
        path = "/weapi/playlist/create"
        params = dict(name=name, privacy=privacy, type=ptype)
        return self.request("POST", path, params)

    # 打卡
    def daka(self, song_datas):
        path = "/weapi/feedback/weblog"
        songs = []
        for i in range(len(song_datas)):
            song = {
                'action': 'play',
                'json': song_datas[i]
            }
            songs.append(song)
        params = {'logs': json.dumps(songs)}
        return self.request("POST", path, params)

    # 用户信息
    def user_detail(self, uid):
        path = "/weapi/v1/user/detail/{}".format(uid)
        return self.request("POST", path)

    def user_level(self):
        path = "/weapi/user/level"
        return self.request("POST", path)

    # 云贝所有任务
    def yunbei_task(self):
        path = "/weapi/usertool/task/list/all"
        return self.request("POST", path)  # .get("data", [])

    # 云贝todo任务
    def yunbei_task_todo(self):
        path = "/weapi/usertool/task/todo/query"
        return self.request("POST", path)  # .get("data", [])

    # 完成云贝任务
    def yunbei_task_finish(self, userTaskId, depositCode):
        path = "/weapi/usertool/task/point/receive"
        params = dict(userTaskId=userTaskId, depositCode=depositCode)
        return self.request("POST", path, params)

    def share_resource(self, type='playlist', msg='', id=''):
        path = "/weapi/share/friends/resource"
        params = dict(type=type, msg=msg, id=id)
        return self.request("POST", path, params)

    # 删除动态
    def event_delete(self, id):
        path = "/weapi/event/delete"
        params = dict(id=id)
        return self.request("POST", path, params)

    # 删除歌单
    def playlist_delete(self, ids):
        path = "/weapi/playlist/remove"
        params = dict(ids=ids)
        return self.request("POST", path, params)

    ###########################
    # 音乐人

    # 概况
    def musician_data(self):
        path = '/weapi/creator/musician/statistic/data/overview/get'
        return self.request("POST", path)

    # 获取任务
    def mission_cycle_get(self, actionType='', platform=''):
        path = '/weapi/nmusician/workbench/mission/cycle/list'
        if actionType == '' and platform == '':
            return self.request("POST", path)
        else:
            params = dict(actionType=actionType, platform=platform)
            return self.request("POST", path, params)

    # 获取任务
    def mission_stage_get(self):
        path = '/weapi/nmusician/workbench/mission/stage/list'
        return self.request("POST", path)           

    # 领取云豆
    def reward_obtain(self, userMissionId, period):
        path = '/weapi/nmusician/workbench/mission/reward/obtain/new'
        params = dict(userMissionId=userMissionId, period=period)
        return self.request("POST", path, params)

    # 账号云豆数
    def cloudbean(self):
        path = "/weapi/cloudbean/get"
        return self.request("POST", path)

    def user_access(self):
        path = '/weapi/creator/user/access'
        return self.request("POST", path)

    # 完成云贝任务: 访问商城
    def visit_mall(self):
        path = "/weapi/yunbei/task/visit/mall"
        return self.request("POST", path)

    # 对歌曲进行评论
    def comments_add(self, song_id, content):
        path = "/weapi/v1/resource/comments/add"
        params = dict(threadId='R_SO_4_'+str(song_id), content=content)
        return self.request("POST", path, params, custom_cookies={'os': 'android'})

    # 回复歌曲评论
    def comments_reply(self, song_id, commentId, content):
        path = "/weapi/v1/resource/comments/reply"
        params = dict(commentId=commentId, threadId='R_SO_4_' +
                      str(song_id), content=content)
        return self.request("POST", path, params, custom_cookies={'os': 'android'})

    # 删除评论
    def comments_delete(self, song_id, commentId):
        path = "/weapi/resource/comments/delete"
        params = dict(commentId=commentId, threadId='R_SO_4_'+str(song_id))
        return self.request("POST", path, params)

    # 发送私信
    def msg_send(self, msg, userIds, type='text'):
        path = "/weapi/msg/private/send"
        params = dict(type=type, msg=msg, userIds=userIds)
        return self.request("POST", path, params)

    def update_playcount(self, id):
        path = "/weapi/playlist/update/playcount"
        params = dict(id=id)
        return self.request("POST", path, params)

    # 云贝推歌
    def yunbei_rcmd_submit(self, songId, yunbeiNum=10, reason='有些美好会迟到，但音乐能带你找到', scene='', fromUserId=-1):
        path = "/weapi/yunbei/rcmd/song/submit"
        params = dict(songId=songId, reason=reason, scene=scene,
                      yunbeiNum=yunbeiNum, fromUserId=fromUserId)
        return self.request("POST", path, params)

    # vip level
    # 黑胶 VIP 乐签 (每日 VIP 成长值签到)
    def vip_sign(self):
        path = "/weapi/vip-center-bff/task/sign"
        return self.request("POST", path, {'isNew': ''})

    def vip_level(self):
        path = "/weapi/music-vip-membership/client/vip/info"
        return self.request("POST", path)

    # 领取会员成长值
    def vip_reward_get(self, taskIds):
        path = "/weapi/vipnewcenter/app/level/task/reward/get"
        params = dict(taskIds=','.join(taskIds))
        return self.request("POST", path, params)

    # 新vip任务列表
    def vip_task_newlist(self):
        path = "/weapi/vipnewcenter/app/level/task/newlist"
        return self.request("POST", path)

    # 领取所有会员成长值
    def vip_reward_getall(self):
        path = "/weapi/vipnewcenter/app/level/task/reward/getall"
        return self.request("POST", path)

    # 云贝过期提醒
    def expire_attention(self):
        path = "/weapi/usertool/yunbei/center/attention"
        return self.request("POST", path)

    # 签到进度
    def signin_progress(self, moduleId):
        path = "/weapi/act/modules/signin/v2/progress"
        params = dict(moduleId=moduleId)
        return self.request("POST", path, params)

    def mlog_nos_token(self, filepath):
        path = "/weapi/nos/token/whalealloc"
        bizKey = ''
        for i in range(8):
            bizKey += hex(random.randint(0, 15)).replace('0x', '')
        _, filename = os.path.split(filepath)
        with open(filepath, 'rb') as f:
            contents = f.read()
            file_md5 = md5(contents).hexdigest()
        params = dict(
            bizKey=bizKey,
            filename=filename,
            bucket='yyimgs',
            md5=file_md5,
            type='image',
            fileSize=os.path.getsize(filepath),
        )
        return self.request("POST", path, params)

    def upload_file(self, filepath, token):
        data = token['data']
        path = "http://45.127.129.8/{}/{}?offset=0&complete=true&version=1.0".format(
            data['bucket'], data['objectKey'])
        content_type = ''
        if filepath.endswith('jpg'):
            content_type = 'image/jpeg'
        elif filepath.endswith('png'):
            content_type = 'image/png'
        elif filepath.endswith('gif'):
            content_type = 'image/gif'
        elif filepath.endswith('mpg'):
            content_type = 'audio/mp3'
        elif filepath.endswith('flac'):
            content_type = 'audio/mpeg'
        headers = {
            'x-nos-token': data['token'],
            'Content-Type': content_type,
        }
        with open(filepath, 'rb') as f:
            res = requests.post(url=path, data=f, headers=headers)
        return res

    def mlog_pub(self, token, height, width, songId, songName='', text='share'):
        path = "/weapi/mlog/publish/v1"

        params = {
            'type': 1,
            'mlog': json.dumps({
                'content': {
                    'image': [{
                        'height': height,
                        'width': width,
                        'more': False,
                        'nosKey': token['data']['bucket'] + '/' + token['data']['objectKey'],
                        'picKey': token['data']['resourceId']

                    }],
                    'needAudio': False,
                    'song': {
                        'endTime': 0,
                        'name': songName,
                        'songId': songId,
                        'startTime': 30000
                    },
                    'text': text,
                },
                'from': 0,
                'type': 1,
            })
        }
        return self.request("POST", path, params)

    # 获取歌曲评论
    def song_comments(self, music_id, offset=0, total="false", limit=100):
        path = "/weapi/v1/resource/comments/R_SO_4_{}/".format(music_id)
        params = dict(rid=music_id, offset=offset, total=total, limit=limit)
        return self.request("POST", path, params)

    # 音乐人专辑列表
    def musician_album(self):
        path = "/weapi/nmusician/production/common/artist/album/item/list/get"
        return self.request("POST", path)

    def watch_college_lesson(self):
        path = "/weapi/nmusician/workbench/creator/watch/college/lesson"
        return self.request("POST", path)

    def artist_homepage(self, artistId):
        path = "/weapi/personal/home/page/artist"
        params = dict(artistId=artistId)
        return self.request("POST", path, params)

    def circle_get(self, circleId):
        path = "/weapi/circle/get"
        params = dict(circleId=circleId)
        return self.request("POST", path, params)        

    def vipcenter_task_external(self, type):
        path = "/weapi/vipnewcenter/app/level/task/external"
        params = dict(type=type)
        return self.request("POST", path, params)             
