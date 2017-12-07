#! user/bin/env python
# -*- coding: utf-8 -*-
import uuid
import json
import tornado.web
import tornado.ioloop
import tornado.websocket


class IndexHandler(tornado.web.RequestHandler):
    """处理客户端的http请求"""
    def get(self):
        self.render('index.html')


class ChatHandler(tornado.websocket.WebSocketHandler):
    """处理websocket请求"""
    waiters = set()  # 存储当前聊天室用户
    messages = []  # 存储历史消息

    def open(self):
        print('连接建立')
        ChatHandler.waiters.add(self)
        uid = str(uuid.uuid4()) # 生成用户标识
        self.write_message(uid)

        # 将历史信息传入模板渲染，并将结果返回给客户端
        for msg in ChatHandler.messages:
            content = self.render_string('message.html', **msg)
            self.write_message(content)

    def on_message(self, message):
        msg = json.loads(message)
        ChatHandler.messages.append(msg)

        # 给聊天室的所有用户返回刚收到的信息
        for client in ChatHandler.waiters:
            content = client.render_string('message.html', **msg)
            client.write_message(content)

    def on_close(self):
        # 客户端断开连接后，移除该对象
        ChatHandler.waiters.remove(self)


def main():
    settings = {
         'template_path': 'templates',
    }
    application = tornado.web.Application([
        (r'/', IndexHandler),
        (r'/chat', ChatHandler),
    ], **settings)

    application.listen(8000)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()



