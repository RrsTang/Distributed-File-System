import os
from pathlib import Path
import hashlib
import argparse
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.client import ServerProxy
from config import database_url


def mktxt(name, content):  # 写文件
    path = root_dir / (name + '.txt')
    try:
        with path.open(mode='w') as f:
            # 写入数据
            f.write(content)
        return 'success'
    except:
        return ''
    
def deltxt(name):  # 删除文件
    path = root_dir / (name + '.txt')
    try:
        path.unlink()
    except FileNotFoundError:
        return 'Txt does not exist'
    except OSError as e:
        return 'An error occurred while deleting the txt'
    return 'success'

def print_cloud_filename():  # 获取云端服务器中所有文件名
    res = []
    for txt in root_dir.rglob('*'):
        res.append(txt.name)
    return res

def get_txt_content(name):  # 获取txt文件内容
    path = root_dir / name
    try:
        content = path.read_text()
        return content
    except IOError:
        print(f"Unable to open txt {path}")
        return False
    
def calculate_file_hash(file_path):  # 计算文件的哈希值
    with open(file_path, 'rb') as file:
        data = file.read()
        hash_value = hashlib.sha256(data).hexdigest()
        return hash_value

if __name__ == '__main__':
    root_dir =  Path(__file__).parent / 'cloud_server'  # 云端服务器
    if not root_dir.exists():
            root_dir.mkdir()
    # 添加初始化参数
    parser = argparse.ArgumentParser()
    parser.add_argument('server_id', help='ID of the file server.', type=int)
    parser.add_argument('port', help='Port of the file server.', type=int)
    args = parser.parse_args()

    with SimpleXMLRPCServer(('localhost', args.port)) as server:
        # 注册函数
        server.register_function(mktxt)
        server.register_function(deltxt)
        server.register_function(print_cloud_filename)
        server.register_function(get_txt_content)

        # 服务器地址
        server_address = 'http://{}:{}'.format(server.server_address[0], server.server_address[1])

        # 更新数据库中服务器的信息
        server_registered = False
        with ServerProxy(database_url, allow_none=True) as proxy:
            server_registered = proxy.add_server(args.server_id, server_address)

        if server_registered:
            # 更新数据库中的文件信息
            root_dir = root_dir / str(args.server_id)

            if not root_dir.exists():
                root_dir.mkdir(parents=True)
            print('Welcome to Tangzhj\'s server.')
            print('Initializing cloud server for files in "{}"...'.format(str(root_dir)))

            # 将云端服务器中已有的文件的信息添加进数据库中
            files_registered = False
            file_list = []
            for filename in os.listdir(root_dir):
                path = os.path.join(root_dir, filename)
                lastmodified = os.path.getmtime(path)
                filehash = calculate_file_hash(path)
                file_list.append(tuple([filename, args.server_id, lastmodified, filehash, 0, 0]))
            with ServerProxy(database_url, allow_none=True) as proxy:
                files_registered = proxy.add_file(file_list)

            if files_registered:
                print('Serving file cloud server on {}.'.format(server.server_address))
                if len(file_list) != 0:
                    print('Successfully synchronized existing files:')
                    for file_info in file_list:
                        print(file_info[0])
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    with ServerProxy(database_url, allow_none=True) as proxy:
                        # 关闭服务器，清理数据库中有关该服务器的信息和文件
                        proxy.delete_server(args.server_id)
                        print('Shutting down the server and cleaning up the files in database.')
            else:
                print('Failed file registration.')
        else:
            print('Failed server registration.')
