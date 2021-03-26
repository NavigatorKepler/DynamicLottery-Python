import json
import math
import random
from hashlib import md5
from time import sleep, time

import requests as req

import config
from timestamp import time_stamp

headers = {
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.104 Safari/537.36',
    'Referer': 'https://www.bilibili.com/'
}

def n_get_reply_raw(oid, type_, pn, root=None, sort=0):       # 获取原始评论区
    url_start = 'https://api.bilibili.com/x/v2/reply'
    if isinstance(root, int):                               # 指定楼中楼
        url_start += '/reply'                               # 要爬取楼中楼
    elif root is None:                                      #
        pass                                                # 要爬取主楼
    else:                                                   #
        raise BaseException('### root属性不正确!')           #

    resp = req.get(url_start,
                   params={'oid':oid, 'root':root, 'pn':pn, 'type':type_, 'sort':sort},
                   headers=headers)                         # 调用API获取原始评论

    if resp.status_code != 200:                             # 状态不正常
        return {'status':resp.status_code, 'content':None}
    else:                                                   # 状态正常
        return {'status':resp.status_code, 'content':json.loads(resp.text)}

def n_get_reply_main(oid, oidtype=11, root=None):
    page_max = 1            # 最大页码
    count = 1               # 当前页码
    reply_container = []    # 存放评论区的列表

    while True:
        sleep(0.5 + random.random())    # 休眠, 减少412可能
        response = n_get_reply_raw(oid, oidtype, count, root=root)

        if response['status'] != 200:               # 一般是412了, 一小时后解封
            sleeptime = random.random() * 120       # 随机休眠
            print(f'### 状态异常, 错误代码为{response["status"]};')
            print(f'### 当前页码为{count}, 程序休眠{sleeptime}秒后继续;')
            sleep(sleeptime)
            continue

        else:
            pre_content = response['content']
            data = pre_content['data']

            # current_page = data['page']['num']
            current_size = data['page']['size']             # 以下皆为评论信息提取
            current_count = data['page']['count']
            # current_acount = data['page']['acount'] if root is None else None
            
            page_max = math.ceil(current_count/current_size)

            replies = data['replies'] if data['replies'] else []

            for reply in replies:
                rpid = reply['rpid']
                _root = reply['root'] if reply['root'] else None        # 如果root是零直接置空，否则取root
                parent = reply['parent'] if reply['parent'] else None   # 如果parent是零直接置空，否则取parent
                uname = reply['member']['uname']
                mid = reply['member']['mid']
                level = reply['member']['level_info']['current_level']
                avatar = reply['member']['avatar']

                content = reply['content']['message']
                device = reply['content']['device']
                rtimestamp = reply['ctime']

                true_reply = {
                    'rpid':rpid,
                    # 'root':_root,
                    # 'parent':parent,
                    'uname':uname,
                    'mid':mid,
                    'level':level,
                    'content':content,
                    'avatar':avatar,
                    'rtimestamp':rtimestamp,
                    'type':'reply'
                }

                same_counts=0                               # 这里负责评论不重复
                for i in reply_container:                   #
                    if rpid == i['rpid']:                   #
                        same_counts += 1                    #
                if same_counts:                             #
                    pass                                    #
                else:                                       #
                    reply_container.append(true_reply)      #

                if reply['replies'] != None:                # 递归调用获取楼中楼
                    n_get_reply_main(oid=oid, oidtype=oidtype, root=rpid)

        if count >= page_max:
            break
        else:
            count += 1

    return reply_container

def n_get_dynamic_repost_raw(dynamic_id):                   # 此处逻辑感谢 @疯狂小瑞瑞
    has_more = 1
    offset = ''
    url_start = f'https://api.vc.bilibili.com/dynamic_repost/v1/dynamic_repost/repost_detail?dynamic_id={dynamic_id}'
    reposts = []

    while has_more == 1:
        sleep(0.5 + random.random())           # 休眠, 减少412可能
        resp = req.get(url_start+offset, headers=headers)

        if resp.status_code != 200:               # 一般是412了, 一小时后解封
            sleeptime = random.random() * 120       # 随机休眠
            print(f'### 状态异常, 错误代码为{resp.status_code};')
            print(f'### 当前正在获取{dynamic_id}, 程序休眠{sleeptime}秒后继续;')
            sleep(sleeptime)
            continue

        content = json.loads(resp.text)
        has_more = content['data']['has_more']
        if has_more:
            offset=f'&offset={content["data"]["offset"]}'

        reposts.append(content)

    return reposts

def n_get_dynamic_repost_main(dynamic_id):
    reposts = n_get_dynamic_repost_raw(dynamic_id=dynamic_id) # 获取转发列表
    repost_container = []                                   # 用于存储提取后的转发信息

    for j in reposts:
        if j['code'] == 0:
            for i in j['data']['items']:
                true_repost = {
                    'rid':i['desc']['rid'],                                             # 转发编号, 是一个非常大的整数
                    'uname':i['desc']['user_profile']['info']['uname'],                 # 用户名
                    'mid':str(i['desc']['user_profile']['info']['uid']),                # 用户id
                    'level':i['desc']['user_profile']['level_info']['current_level'],   # 用户等级
                    'content':json.loads(i['card'])['item']['content'],                 # 转发内容
                    'avatar':i['desc']['user_profile']['info']['avatar'],               # 头像
                    'rtimestamp':i['desc']['timestamp'],                                # 转发时间
                    'type':'repost'
                }
                repost_container.append(true_repost)
        else:
            print('### 有失败请求。')

    return repost_container

def n_get_dynamic_like_raw(dynamic_id):
    url_start = 'http://api.vc.bilibili.com/dynamic_like/v1/dynamic_like/spec_item_likes'
    likes = []
    count = 0
    countmax = None
    page = 1
    pagemax = 1

    while page <= pagemax+1:
        sleep(0.5 + random.random())           # 休眠, 减少412可能
        resp = req.get(url_start, headers=headers, params={
            'dynamic_id':dynamic_id,
            'pn':page
            })

        if resp.status_code != 200:               # 一般是412了, 一小时后解封
            sleeptime = random.random() * 120       # 随机休眠
            print(f'### 状态异常, 错误代码为{resp.status_code};')
            print(f'### 当前正在获取{dynamic_id}, 程序休眠{sleeptime}秒后继续;')
            sleep(sleeptime)
            continue

        content = json.loads(resp.text)
        data = content['data']
        if content['code'] != 0:
            print('### 数据有误。')
            return
        
        countmax = data['total_count']
        pagemax = countmax / 20.0
        item_likes = data['item_likes']
        for i in item_likes:
            if count < countmax:
                likes.append(i)
                count+=1
        page+=1

    return likes

def n_get_dynamic_like_main(dynamic_id):
    likes = n_get_dynamic_like_raw(dynamic_id=dynamic_id) # 获取点赞列表
    likes_container = []                                  # 用于存储提取后的点赞信息

    for i in likes:
        true_like = {
            'liketime':i['time'],                                   # 点赞没有ID, 用点赞时间戳代替
            'uname':i['uname'],                                     # 用户名
            'mid':str(i['uid']),                                    # 用户id
            'level':i['user_info']['level_info']['current_level'],  # 用户等级
            'content':i['user_info']['sign'],                       # 点赞没有内容, 用用户签名代替
            'avatar':i['face_url'],                                 # 头像
            'rtimestamp':i['time'],                    # 转发时间
            'type':'like'
        }
        likes_container.append(true_like)

    return likes_container

'''
def n_filter(reply_container):                          # 包括将评论/转发按时间排序和去除单一用户的重复评论/转发
                                                        # 这一层只做数据的筛选, 可以暴力的将三个返回值接起来送到此处
    mid_earliest = {}                                   # 键值对, 用于排序
    __reply_container = []                              # 用于存储筛选后的评论/转发

    for i in reply_container:
        if i['mid'] not in mid_earliest.keys():         # 如果没有记录此人的评论/转发时间
            mid_earliest[i['mid']] = i['rtimestamp']
        else:
            if mid_earliest[i['mid']] < i['rtimestamp']:# 虽然记录了时间, 但找到了同一个人更早的评论/转发
                mid_earliest[i['mid']] = i['rtimestamp']

    mid_earliest_sorted = sorted(mid_earliest.items(), key = lambda kv:(kv[1], kv[0]))
    # 将评论/转发按照时间排序, 获取每个人最早的评论/转发时间

    for i in mid_earliest_sorted:
        for j in reply_container:
            if i[0] == str(j['mid']) and i[1] == j['rtimestamp']:
                __reply_container.append(j)    # 按照最早时间提取出对应的评论/转发

    return __reply_container
'''

