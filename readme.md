## 简易使用教程

首先需要安装一个依赖库bcrypt

```
pip install bcrypt
```

然后启动数据库服务器

```
python database.py
```

然后启动RPC服务器，其参数项要加上服务器id和端口号、

```
python server.py <serverid> <port>
```

然后注册并登录用户

```
python client.py signup <username> <password>
python client.py login <usernme> <password>
```

登录之后，用户可以使用如下几条命令

- **ls** 查看本地缓存的文件信息
- **server_ls** 查看云端服务器的所有文件信息
- **mktxt <txt_name> \<content>** 创建或修改txt文件，先在本地操作后更新到云端
- **deltxt <txt_name>** 删除本地和所有云端服务器的某个txt文件
- **readtxt <txt_name>** 读txt文件，如果本地存在最新的版本，则直接在本地读取，否则先到服务器获取最新版本
- **upload** 上传本地所有文件到服务器中
- **download <server_id> <txt_name>** 从指定的服务器中下载指定名字的txt
- **help** 获取可用命令列表
- **exit** 登出



更详细的使用教程请查看实验报告