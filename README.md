# ZSPIDER | [![Documentation Status](https://readthedocs.org/projects/zspider/badge/?version=latest)](http://zspider.readthedocs.org/en/latest/?badge=latest)
一个分布式的定时抓站系统
for [English README](README_EN.md)

## Python 版本要求
- python3.7
- python3.8
- python3.9

## 系统组件
#### dispatcher
_任务分配中心 :_ 可以在多个服务器上启动，它将自动检测一个工作，其余冷备.
#### crawler
_抓站工作组件 :_ 实际执行抓取任务
#### web
_web后台 :_ 系统管理web后台.

## 三方资源依赖
- rabbitmq
- mongodb
- memcached

使用docker安装更快捷

## 说明
文档也许有时间会慢慢写

当前项目已经处于基本可用状态。运行前装好资源依赖，修改好配置即可。

注意源文件文件名包含 `conf`的. 主要是:
- `conf.py`
- `crawl_conf.py`
- `dispatcher_conf.py`
- `web_conf.py`

## 开发工具
[dev](https://github.com/wish/dev) 工具可以尝试使用.

安装好后在本项目目录执行 `dev zspider` 查看选项
