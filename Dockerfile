# 选择编译镜像
FROM python:3.7

# 配置ssh
WORKDIR /root/.ssh
RUN chmod 777 /root/.ssh \
    && ssh-keyscan -t rsa gc.hlc >> /root/.ssh/known_hosts 
COPY id_rsa .

RUN chmod 400 /root/.ssh/id_rsa

WORKDIR /www

# 缓存code，用于控制清理缓存
ARG ACTIVITY_CACHE=1

# 下载 explorer_s_common
RUN git clone -b dev ubuntu@gc.hlc:xmpool/explorer_s_activity.git \ 
    && cd /www/explorer_s_common \
    && git pull \
    && cd /www

# 安装依赖
RUN pip install -i https://pypi.doubanio.com/simple/ -r explorer_s_common/requirements.txt

# 修改时区
RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

WORKDIR /www/explorer_s_activity
COPY . /www/explorer_s_activity/

# 暴露端口
EXPOSE 10040

# 启动
CMD cd /www/explorer_s_common \
    && git pull \
    && cd /www/explorer_s_activity \
    && gunicorn -c gunicorn.conf.py explorer_s_activity.wsgi:application

# docker build -f Dockerfile_build -t explorer_s_activity:latest .
# docker container run --rm -p 10010:10010 --env-file ../dev.env explorer_s_activity:latest