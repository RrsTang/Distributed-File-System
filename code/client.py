from xmlrpc.client import ServerProxy
import base64
import bcrypt
from pathlib import Path
from config import database_url
import argparse
import datetime
import os
import hashlib
import time

def calculate_file_hash(file_path):  # 计算文件哈希值
    with open(file_path, 'rb') as file:
        data = file.read()
        hash_value = hashlib.sha256(data).hexdigest()
        return hash_value
    
def sign_up(username, password):  # 注册用户
    if len(password) > 72:
        print('Password must be less than 72 characters.')
        return
    # salt值属于随机值。用户注册时，系统用来和用户密码进行组合而生成的随机数值
    salt = bcrypt.gensalt()
    hash_password = bcrypt.hashpw(password.encode('utf-8'), salt)  # 将明文密码哈希化，增加安全性，input的是字节串，哈希后的密码中会包含盐值的信息
    # 储存哈希化之后的密码和盐值，input的是base64格式的字符串
    if proxy.add_user(username, base64.b64encode(hash_password).decode('utf-8'),
                       base64.b64encode(salt).decode('utf-8')):
        print('salt:{} hash_passpord:{}'.format(salt, hash_password))
        print('User {} created successfully.'.format(username))
    else:
        print('User already exists, Could not create user {}.'.format(username))


def login(username, password):  # 登录
    results = proxy.get_user_info(username)
    if results is None:
        print('Username does not exist.')
    else:
        hash_password = results[0].encode('utf-8')  # 转为字节串

        if bcrypt.checkpw(password.encode('utf-8'), hash_password):  # 可以自动从哈希后密码中提取盐值，无需显式传递
            print('Logged in as {}.'.format(username))
            return App(username)
        else:
            print('Wrong password.')
    return None

def mktxt(path, name, content):  # 创建txt文件
    name = name + '.txt'
    txt_path = path / name
    try:
        with txt_path.open(mode='w') as f:
            # 写入数据
            f.write(content)
        print('The local txt file was written successfully.')
        update(path, name, 'upload')
    except:
        print('An error occurred while making the local txt or uploading the txt.')

def deltxt(path, name):  # 删除txt文件
    name = name + '.txt'
    txt_path = path / name
    try:
        txt_path.unlink()
        print('The local txt file was deleted successfully.')
        update(path, name, 'delete')
    except FileNotFoundError:
        print("Txt does not exist")
    except OSError as e:
        print("An error occurred while deleting the txt:", e)

def get_txt_content(path):  # 获取txt文件内容
    try:
        content = path.read_text()
        return content
    except IOError:
        print(f"Unable to open txt {path}")
        return False

def readtxt(path, name):  # 读文件
    name = name + '.txt'
    serverid = proxy.get_server_info()[0][0]  # 随便获取一个服务器id
    lock = proxy.get_lock(serverid, name)
    xlock = lock[1]
    if xlock == 1:  # 如果当前文件被加上了排他锁，则等待
        print('The txt is being written, please wait...')
    while proxy.get_lock(serverid, name)[1]:
        pass
    proxy.lock_S(serverid, name)  # 给文件加上一个共享锁
    if not (path / name).exists():  # 如果本地没有这个文件，则从服务器下载
        print('The txt is not existed loaclly, so we download it from server.')
        download(serverid, name, path)
    else:  # 如果本地有文件，但是和服务器的不一致，则从服务器下载更新
        local_filehash = calculate_file_hash(path / name)
        cloud_filehash = proxy.get_one_file_hash(serverid, name)[0]
        if (local_filehash != cloud_filehash):
            print('Local files are not the same as cloud files, so we update it from server.')
            download(serverid, name, path)
    content = get_txt_content(path / name)
    if content == False:
        print('Unable to read {}'.format(name))
    else:
        print('The content of {} is {}'.format(name, content))
    proxy.unlock_S(serverid, name)  # 解开一个共享锁

def upload_all(path):  # 将本地的所有txt都上传到服务器
    for txt in path.rglob('*'):
        update(path, txt.name, 'upload')

def update(path, name, op):  # 将本地的操作更新到服务器
    addresses = proxy.get_all_server_addresses()
    if op == 'upload':  # 上传操作
        if name.endswith('.txt'):
            content = get_txt_content(path / name)
            for address in addresses:  # 遍历所有服务器地址
                serverid = proxy.get_server_id(address)[0]
                lock = proxy.get_lock(serverid, name)
                if lock != None:
                    slock = lock[0]
                    xlock = lock[1]
                    if slock != 0 or xlock != 0:  # 如果该文件已被加上任意一把锁，则等待
                        print('The txt is being read or written, please wait...')
                        while True:
                            lock = proxy.get_lock(serverid, name)
                            slock = lock[0]
                            xlock = lock[1]
                            if slock == 0 and xlock == 0:
                                break
                    proxy.lock_X(serverid, name)  # 给文件加上一把排他锁
                with ServerProxy(address, allow_none=True) as server_proxy:
                    server_id = proxy.get_server_id(address)[0]
                    back = server_proxy.mktxt(name[:-4], content)
                    print('Server_id:{}'.format(str(server_id)), end=' ')
                    if back == 'success':
                        lastmodified = os.path.getmtime(os.path.join(path, name))
                        filehash = calculate_file_hash(os.path.join(path, name))
                        proxy.add_file([tuple([name, server_id, lastmodified, filehash, 0, 1])])
                        print('Successfully upload.')
                    else:
                        print('Fail to upload.')
                proxy.unlock_X(serverid, name)  # 解开一个排他锁
    elif op == 'delete':  # 删除操作
        if name.endswith('.txt'):
            for address in addresses:  # 遍历所有服务器地址
                serverid = proxy.get_server_id(address)[0]
                lock = proxy.get_lock(serverid, name)
                slock = lock[0]
                xlock = lock[1]
                if slock != 0 or xlock != 0:  # 如果该文件已被加上任意一把锁，则等待
                    print('The txt is being read or written, please wait...')
                    while True:
                        lock = proxy.get_lock(serverid, name)
                        slock = lock[0]
                        xlock = lock[1]
                        if slock == 0 and xlock == 0:
                            break
                proxy.lock_X(serverid, name)  # 给文件加上一把排他锁
                with ServerProxy(address, allow_none=True) as server_proxy:
                    server_id = proxy.get_server_id(address)[0]
                    back = server_proxy.deltxt(name[:-4])
                    print('Server_id:{}'.format(str(server_id)), end=':')
                    if back == 'success':
                        proxy.delete_file(server_id, name)
                        print('Successfully delete.')
                    else:
                        print(back)
                # 文件已经被删了，所以不需要解开排他锁了

def download(server_id, name, local_path):  # 从服务器下载文件
    address = proxy.get_server_address(server_id)[0]
    txt_list = proxy.get_file_infos(server_id)
    try:
        for info in txt_list:
            if info[0] == name:
                with ServerProxy(address, allow_none=True) as server_proxy:
                    content = server_proxy.get_txt_content(name)
                local_path = Path(local_path) / name
                with local_path.open(mode='w') as f:
                    # 写入数据
                    f.write(content)
                print('The txt file was downloaded successfully.')
    except:
        print('An error occurred while downloading the txt.')

def print_local_filename(path):  # 打印本地文件名
    for txt in path.rglob('*'):
        print(txt.name)

def print_cloud_filename():  # 打印服务器所有文件信息
    addresses = proxy.get_all_server_addresses()
    print('{0:25s} {1:7s} {2}'.format('File Name', 'Server', 'Last Modified Time'))
    for address in addresses:
        server_id = proxy.get_server_id(address)[0]
        txt_list = proxy.get_file_infos(server_id)
        for info in txt_list:
            modified_time_str = datetime.datetime.fromtimestamp(info[2]).strftime('%Y-%m-%d %H:%M:%S')
            print('{0:25s} {1:7s} {2}'.format(info[0], str(info[1]), modified_time_str))

class App(object):
    def __init__(self, username):
        self.username = username
        self.root_dir =  Path(__file__).parent / 'local_cache' / username  # 用户的本地缓存
        if not (Path(__file__).parent / 'local_cache').exists():
            (Path(__file__).parent / 'local_cache').mkdir()
        if not self.root_dir.exists():
            self.root_dir.mkdir()

    def print_option(self):  # 打印操作教程
        print('OPTIONS')
        print('- ls')
        print('- server_ls')
        print('- mktxt <txt_name> <content>')
        print('- deltxt <txt_name>')
        print('- readtxt <txt_name>')
        print('- upload')
        print('- download <server_id> <txt_name>')
        print('- help')
        print('- exit')

    def main_loop(self):
        print('Current user:', self.username)
        self.print_option()
        print('Type \'help\' to get tutorial')
        while True:
            print('Current user:', self.username)
            command = str(input('$ ')).split(' ')
            if command[0] == 'ls' and len(command) == 1:
                print_local_filename(self.root_dir)
            elif command[0] == 'server_ls' and len(command) == 1:
                print_cloud_filename()
            elif command[0] == 'mktxt' and len(command) == 3:
                mktxt(self.root_dir, command[1].strip(), command[2])      
            elif command[0] == 'deltxt' and len(command) == 2:
                deltxt(self.root_dir, command[1].strip())
            elif command[0] == 'readtxt' and len(command) == 2:
                readtxt(self.root_dir, command[1].strip())
            elif command[0] == 'upload' and len(command) == 1:
                upload_all(self.root_dir)
            elif command[0] == 'download' and len(command) == 3:
                download(int(command[1].strip()), command[2].strip() + '.txt', self.root_dir)
            elif command[0] == 'help' and len(command) == 1:
                self.print_option()
            elif command[0] == 'exit':
                break
            else:
                print('Invalid Command.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', help='Client mode, "signup" or "login".', type=str)
    parser.add_argument('username', help='Username of the user.', type=str)
    parser.add_argument('password', help='Password of the user.', type=str)
    args = parser.parse_args()

    proxy = ServerProxy(database_url, allow_none=True)

    if args.mode == 'signup':
        sign_up(args.username, args.password)
    elif args.mode == 'login':
        app = login(args.username, args.password)

        if app is not None:
            app.main_loop()
    else:
        print('Invalid operation.')
