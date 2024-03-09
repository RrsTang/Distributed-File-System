import sqlite3
from xmlrpc.server import SimpleXMLRPCServer
import base64
from config import database_info


def init_user_table():
    cursor.execute('drop table if exists users;')
    connection.commit()
    cursor.execute('create table users (\
username text primary key,\
password text,\
salt text);')
    connection.commit()

def init_server_table():
    cursor.execute('drop table if exists servers;')
    connection.commit()
    cursor.execute('create table servers (\
serverid integer primary key,\
address text);')
    connection.commit()

def init_file_table():
    cursor.execute('drop table if exists files;')
    connection.commit()
    cursor.execute('create table files (\
filename text,\
serverid integer,\
lastmodified float,\
filehash text,\
S_lock integer check (S_lock >= 0),\
X_lock integer check (X_lock = 0 or X_lock = 1),\
primary key (filename, serverid));')
    connection.commit()

def init_db():
    init_user_table()
    init_server_table()
    init_file_table()
    connection.commit()

def add_user(username, hash_password, salt):  # 添加一个用户
    try:
        cursor.execute('insert into users (username, password, salt) values (?, ?, ?);',
                       (username, str(base64.b64decode(hash_password), 'utf-8'), str(base64.b64decode(salt), 'utf-8')))
        connection.commit()
        return True
    except sqlite3.Error:
        return False

def add_server(server_id, address):  # 添加新的服务器
    try:
        cursor.execute('insert into servers (serverid, address) values (?, ?);', (server_id, address))
        connection.commit()
        return True
    except sqlite3.Error:
        return False

def delete_server(server_id):  # 删除服务器，一并删除其存的文件信息
    cursor.execute('delete from servers where serverid = ?;', (server_id, ))
    cursor.execute('delete from files where serverid = ?;', (server_id, ))
    connection.commit()

def add_file(file_list):  # 添加新文件，如果已存在则覆盖
    try:
        cursor.executemany('insert or replace into files (filename, serverid, lastmodified, filehash, S_lock, X_lock)\
                              values (?, ?, ?, ?, ?, ?)', file_list)
        connection.commit()
        return True
    except sqlite3.Error:
        return False

def lock_S(serverid, filename):  # 给定文件名和所在服务器，获取共享锁
    try:
        cursor.execute('update files set S_lock = S_lock + 1 where serverid = ? and filename = ?;', (serverid, filename))
        connection.commit()
        return True
    except sqlite3.Error:
        return False

def unlock_S(serverid, filename):  # 给定文件名和所在服务器，归还共享锁
    try:
        cursor.execute('update files set S_lock = S_lock - 1 where serverid = ? and filename = ?;', (serverid, filename))
        connection.commit()
        return True
    except sqlite3.Error:
        return False
    
def lock_X(serverid, filename):  # 给定文件名和所在服务器，获取排他锁
    try:
        cursor.execute('update files set X_lock = X_lock + 1 where serverid = ? and filename = ?;', (serverid, filename))
        connection.commit()
        return True
    except sqlite3.Error:
        return False

def unlock_X(serverid, filename):  # 给定文件名和所在服务器，归还排他锁
    try:
        cursor.execute('update files set X_lock = X_lock - 1 where serverid = ? and filename = ?;', (serverid, filename))
        connection.commit()
        return True
    except sqlite3.Error:
        return False

def get_lock(serverid, filename):  # 给定文件名和所在服务器，返回共享锁和排他锁的情况
    try:
        cursor.execute('select S_lock, X_lock from files where serverid = ? and filename = ?;', (serverid, filename))
        res = cursor.fetchone()
        return res
    except sqlite3.Error:
        return None

def get_user_info(username):  # 获取用户信息
    try:
        cursor.execute('select password, salt from users where username = ?;', (username, ))
        res = cursor.fetchone()
        return res
    except sqlite3.Error:
        return None

def get_server_info():  # 获取所有服务器信息
    try:
        cursor.execute('select serverid, address from servers;')
        res = cursor.fetchall()
        return res
    except sqlite3.Error:
        return []

def get_server_id(address):  # 输入服务器地址，返回服务器id
    try:
        cursor.execute('select serverid from servers where address = ?', (address, ))
        res = cursor.fetchone()
        return res
    except sqlite3.Error:
        return []
    
def get_server_address(serverid):  # 输入服务器id，返回服务器地址
    try:
        cursor.execute('select address from servers where serverid = ?;', (serverid, ))
        res = cursor.fetchone()
        return res
    except sqlite3.Error:
        return []

def get_all_server_addresses():  # 获取所有服务器的地址
    try:
        cursor.execute('select address from servers')
        res = cursor.fetchall()
        return [address for (address, ) in res]
    except sqlite3.Error:
        return []

def get_file_infos(serverid):  # 输入服务器id，获取该服务器的所有文件信息
    try:
        cursor.execute('select filename, serverid, lastmodified, filehash from files\
                        where serverid = ?;', (serverid, ))
        res = cursor.fetchall()
        return res
    except sqlite3.Error:
        return []

def get_one_file_hash(serverid, filename):  # 给定服务器id和文件名，返回文件哈希值
    try:
        cursor.execute('select filehash from files where serverid = ? and filename = ?;', (serverid, filename))
        res = cursor.fetchone()
        return res
    except sqlite3.Error:
        return []

def delete_file(serverid, filename):  # 给定服务器id和文件名，删除该文件
    try:
        cursor.execute('delete from files where serverid = ? and filename = ?;', (serverid, filename))
        connection.commit()
        return True
    except sqlite3.Error:
        return False




if __name__ == '__main__':
    server_counter = 0
    connection = sqlite3.connect('info.db')
    cursor = connection.cursor()
    init_db()
    with SimpleXMLRPCServer(database_info, allow_none=True) as server:
        # 创建一个XML-RPC服务器，并注册多个函数来处理远程调用请求
        server.register_function(add_user)
        server.register_function(add_server)
        server.register_function(add_file)
        server.register_function(delete_server)
        server.register_function(delete_file)
        server.register_function(get_user_info)
        server.register_function(get_file_infos)
        server.register_function(get_all_server_addresses)
        server.register_function(get_server_address)
        server.register_function(get_server_id)
        server.register_function(get_one_file_hash)
        server.register_function(get_server_info)
        server.register_function(get_lock)
        server.register_function(lock_S)
        server.register_function(unlock_S)
        server.register_function(lock_X)
        server.register_function(unlock_X)
        try:
            print('Welcome to Tangzhj\'s database.')
            server.serve_forever()  # 启动服务器并开始监听端口上的请求
        except KeyboardInterrupt:
            print('Good bye.')
            connection.close()
