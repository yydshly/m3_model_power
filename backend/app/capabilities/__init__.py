"""所有 handler 模块在 app 启动时 import 即可注册。"""
from . import chat, files, image, models, music, video, voice  # noqa: F401
