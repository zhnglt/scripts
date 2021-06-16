import base64
import json

import requests
from airtest.utils.logger import get_logger

logger = get_logger("airtest")


def get_vcode_click_pos(uname, pwd, img):
    """
    打码平台破解极验验证码
    :param uname: 账号
    :param pwd: 密码
    :param img: 验证码截图路径或者图片二进制流
    :return: 成功返回打码坐标 失败返回空字符
    """
    try:
        if isinstance(img, str):
            with open(img, 'rb') as f:
                img = f.read()

        base64_data = base64.b64encode(img)
        b64 = base64_data.decode()
        data = {"username": uname, "password": pwd, "image": b64, "typeid": 21}
        data = json.loads(requests.post("https://api.ttshitu.com/imageXYPlus", json=data).text)

        logger.debug('打码请求反馈数据: %s' % data)
        """
        参数	说明	类型
        success	请求返回的状态,true成功，false失败。注：接入的程序只需根据此字段判断请求是否成功。	boolean
        code	返回的code。成功为0，失败为-1	string
        message	当请求失败时，返回的失败原因即success=false时返回的原因	string
        data	成功返回的结果内容。具体包含下面参数	-
        ├ result	当请求成功时，返回的识别的结果,即success=ture时返回的识别结果如:AXSZ	string
        └ id	当请求成功时，返回的识别的结果,即success=ture时返回的识别结果的id用于报错	string
        """
        return data
    except:
        return ''
