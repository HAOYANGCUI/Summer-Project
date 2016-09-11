#!/usr/bin/env python
# coding: utf-8

from wxbot import *


class MyWXBot(WXBot):
    def handle_msg_all(self, msg):
            self.send_msg_by_uid(u'hi', msg[cuihao]['wxid_6czbv7b9uq1m22'])
            #self.send_img_msg_by_uid("img/1.png", msg['user']['id'])
            #self.send_file_msg_by_uid("img/1.png", msg['user']['id'])

    def schedule(self):
        self.send_msg(u'cuihao', u'DANGER')
        time.sleep(1)



def main():
    bot = MyWXBot()
    bot.DEBUG = True
    bot.run()


if __name__ == '__main__':
    main()
