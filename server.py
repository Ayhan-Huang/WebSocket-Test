#! user/bin/env python
# -*- coding: utf-8 -*-
import socket
import base64
import hashlib
import struct


def get_headers(data):
    """将请求头转化为字典"""
    header_dict = {}
    data = str(data, encoding='utf-8')
    header, body = data.split('\r\n\r\n', 1)
    header_list = header.split('\r\n')

    for i in range(0, len(header_list)):
        if i == 0:
            if len(header_list[i].split(' ')) == 3:  # 分离请求头首行信息
                header_dict['method'], header_dict['uri'], header_dict['protocol'] = header_list[i].split(' ')

        else:  # 首部字段
            k, v = header_list[i].split(':', 1)
            header_dict[k] = v.strip()

    return header_dict


def handshaking_response(data):
    """
    响应客户端websocket握手：1.提取请求头 2.计算Sec-WebSocket-Key 3.返回携带Sec-WebSocket-Accept的响应
    :param data: 客户端握手请求数据
    :return: 
    """
    headers = get_headers(data)  # 提取请求头
    # 从请求头提取Sec-WebSocket-Key
    # 将magic_string和Sec-WebSocket-Key先进行SHA-1
    # 摘要计算，
    # 之后进行BASE - 64
    # 编码，编码结果作为响应头Sec-WebSocket-Accept字段的值，返回给客户端
    magic_string = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'  # 协议规定的魔法字符串
    value = headers['Sec-WebSocket-Key'] + magic_string
    res = base64.b64encode(hashlib.sha1(value.encode('utf-8')).digest())

    response_tpl = "HTTP/1.1 101 Switching Protocols\r\n" \
                   "Upgrade:websocket\r\n" \
                   "Connection: Upgrade\r\n" \
                   "Sec-WebSocket-Accept: %s\r\n" \
                   "WebSocket-Location: ws://%s%s\r\n\r\n"
    # 响应
    response = response_tpl % (res.decode('utf-8'), headers['Host'], headers['uri'])
    return response


def get_msg(data):
    """
    服务端手动解包客户端发来的数据
    :param data: 客户端发来的原始bytes数据
    :return: msg 解包后的请求体数据
    """
    payload_len = data[1] & 127
    if payload_len == 126:
        extend_payload_len = msg[2:4]
        mask = data[4:8]
        decoded = data[8:]  # decoded 是请求体数据
    elif payload_len == 127:
        extend_payload_len = data[2:10]
        mask = data[10:14]
        decoded = data[14:]
    else:
        extend_payload_len = None
        mask = data[2:6]
        decoded = data[6:]

    bytes_list = bytearray()
    for i in range(len(decoded)):
        chunk = decoded[i] ^ mask[i % 4]
        bytes_list.append(chunk)

    msg = str(bytes_list, encoding='utf-8')
    return msg


def send_msg(conn, msg_bytes):
    """
    服务端向客户端发送消息
    :param conn: 客户端连接到服务器的socket对象
    :param msg_bytes: 向客户端发送的字节
    :return: 
    """
    token = b'\x81'
    length = len(msg_bytes)
    if length < 126:
        token += struct.pack('B', length)
    elif length <= 0xFFFF:
        token += struct.pack('!BH', 126, length)
    else:
        token += struct.pack("!BQ", 127, length)

    msg = token + msg_bytes
    conn.send(msg)

    return True


def main():
    # 创建TCP套接字
    tcpsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcpsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcpsock.bind(('127.0.0.1', 8000))
    tcpsock.listen(5)

    while True: # 连接循环
        print('waitting for connection...')
        # 收到握手请求
        conn, addr = tcpsock.accept()
        data = conn.recv(1024)
        print('connected from', addr)

        # 返回握手响应
        response = handshaking_response(data)
        conn.send(bytes(response, encoding='utf-8'))

        # 通讯循环
        while True:
            try:
                data = conn.recv(8096)
                if not data:
                    break
                msg = get_msg(data) # 解包收到的数据
                print('收到信息：',msg)
                send_msg(conn, ('服务端响应：'+ msg).encode('utf-8')) # 封包，发送数据
            except Exception as e:
                print('客户端异常断开')

        conn.close()

    tcpsock.close()

if __name__ == '__main__':
    main()
