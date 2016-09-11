# -*- coding:utf-8 -*-
REDIS_CONN = {
    'host': '192.168.43.86',
    'port': 80,
    'db': 8,
}

WECHAT_CONN = {
    'username': 'cuihaoyangbohan',
    'password': '241205gongzhonghao',
}

NOTIFY_IDS = [
    'cuiyangdeweixin',  # k
]

MSG_SIGNATURE = 'AutoSend by Python'


try:
    from local_settings import *
except Exception as e:
    pass
