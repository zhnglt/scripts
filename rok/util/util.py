from datetime import datetime

import matplotlib.pyplot as plt
from aip import AipOcr

from settings import BAIDU_AIP_OCR_CONFIG


def save_touch_screen(plist, screen, filename='screenshot/%s.jpg' % datetime.now()):
    plt.imshow(screen)
    for i in range(0, len(plist), 2):
        plt.text(plist[i], plist[i + 1], 'x')
    plt.gcf().savefig(filename)
    plt.close(plt.gcf())


def img_to_str(image):
    if isinstance(image, str):
        with open(image, 'rb') as fp:
            image = fp.read()
    elif not isinstance(image, bytes):
        return

    client = AipOcr(**BAIDU_AIP_OCR_CONFIG)
    result = client.basicGeneral(image)
    # print(result)
    # {'words_result': [{'words': '109382'}], 'log_id': 1347901057883176960, 'words_result_num': 1}
    if 'words_result' in result:
        return '\n'.join([w['words'] for w in result['words_result']])
