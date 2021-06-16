import logging
import os

from airtest.core.settings import Settings as ST
from airtest.utils.logger import get_logger
from concurrent.futures import ThreadPoolExecutor

ST.CVSTRATEGY = ["surf", "tpl"]

DEBUG = True
VIVO_X21 = '4beda60'
VM = 'emulator-5554'
WIRE_VIVO = '192.168.1.101:5555'
BASE_DIR = os.path.dirname(__file__)
ROK_PACKAGE_NAME = 'com.lilithgames.rok.offical.cn'
ROK_MAIN_ACTIVITY = 'com.harry.engine.MainActivity'
logger = get_logger("airtest")
logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)
EXIT_FLAG = False
THREAD_POOL_EXECUTOR = ThreadPoolExecutor(max_workers=10)
BAIDU_AIP_OCR_CONFIG = {
    'appId': '23519624',
    'apiKey': 'TKy0zut7HeB3Hnj1ivyBDiwe',
    'secretKey': 'KPCGygIFChQGTEOWUOD6iBvPK4f0YGPS'
}

APP_RUNNING_TIME = 60*30

