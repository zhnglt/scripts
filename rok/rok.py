# -*- encoding=utf8 -*-
__author__ = "thou"

import random
import re
import traceback

from settings import *
from airtest.core.api import *
from airtest.aircv.aircv import *

from util.tujian import get_vcode_click_pos
from util.util import save_touch_screen, img_to_str
import datetime


dev = None


def init_logging():
    logger = logging.getLogger("ROK")
    logger.setLevel(logging.INFO)
    stdout_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(filename="log/rok.log")
    formatter = logging.Formatter(
        fmt='[%(asctime)s][%(levelname)s]<%(name)s>: %(message)s',
        datefmt='%Y-%m-%d %I:%M:%S'
    )
    stdout_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stdout_handler)
    return logger


def pass_geetest_vcode(threshold=10):
    """
    验证极验人机验证码
    :return: 无
    """
    start_time = time.time()
    for i in range(threshold):
        # 查找确认按钮
        screen = dev.snapshot()
        pos = Template(r"item/sure.png").match_in(screen)
        if pos is not None:
            x, y = pos
            logger.info('检测到人机<<确认>>(%d, %d)按钮' % (x, y))
            logger.info('开始从全屏帧中截取验证码区域')
            img = screen
            if DEBUG:
                xs, ys = 200, 730
                img = img[200:, 730:1810]
            else:
                xs, ys = 134, 730
                img = img[134:, 730:1540]

            st = time.time()
            logger.info('开始向第三方打码平台发送打码请求')
            data = get_vcode_click_pos(uname='okiyar', pwd='okiyar',
                                       img=np.array(cv2.imencode('.jpg', img)[1]).tobytes())
            logger.info('收到返回结果: (%s) 耗时: %.5s 秒' % (data, (time.time() - st)))
            if data['success']:
                result = data["data"]["result"]
                result = result.split('|')

                logger.info('开始模拟人工点击验证码')
                for i in range(len(result)):
                    r = result[i].split(',')
                    x = int(r[0]) + ys
                    y = int(r[1]) + xs
                    dev.touch((int(r[0]) + ys, int(r[1]) + xs))
                    logger.info('点击打点%d坐标: (%d, %d)' % (i + 1, x, y))
                    sleep(0.5)

                # 保存打码验证码
                save_touch_screen(pos, dev.snapshot(), filename='screenshot/vcode/%s.png' % datetime.datetime.now())
                dev.touch(pos)
                sleep(3)

                # 检测是否通过验证
                if not Template("item/sure.png").match_in(dev.snapshot()):
                    logger.info("已通过验证")
                    logger.info('本次验证共计耗时: %.5s 秒' % (time.time() - start_time))
                    break
                else:
                    logger.info("未通过验证")
                    continue
            else:
                logger.info("打码失败，重新打码，说明：%s" % data["message"])

        else:
            # 查找验证按钮
            screen = dev.snapshot()
            pos = Template(r"item/verify.png").match_in(screen)
            if pos is not None:
                x, y = pos
                logger.info('找到人机<<验证>>(%d, %d)按钮，开始点击，并等待5秒加载验证码，进行下一步骤查找<<确认>>按钮' % (x, y))
                dev.touch(pos)
                # save_touch_screen(pos, screen)

        logger.info("人机验证标志循环检测中... %d/%d" % (i + 1, threshold))
    else:
        logger.info("检测次数超出阈值仍未检测到相应标志，退出人机验证任务")


def switch_role(threshold=10):
    """
    大小号切换
    :return:
    """
    # 保证当前界面含有个人头像
    logger.info("开始检测当前界面是否含有个人头像界面...")
    for i in range(10):
        pos = Template("item/home-map.png").match_in(dev.snapshot()) or Template("item/home-tower.png").match_in(
            dev.snapshot())
        if pos:
            logger.info("检测到当前界面含有个人头像界面")
            dev.touch((100, 70))
            logger.info("已点击个人头像")
            break

        dev.keyevent("BACK")
        sleep(1)
        logger.info("个人头像界面循环检测中... (%d/%d)" % (i + 1, threshold))
    else:
        logger.info("检测次数超出阈值仍未检测到相应标志，退出切换角色任务")
        return

    for i in range(threshold):
        pos = Template(r"item/settings.png").match_in(dev.snapshot())
        if pos:
            logger.info("检测到<<设置>>图标，期望<<角色管理>>图标")
            dev.touch(pos)
            sleep(1)

        pos = Template(r"item/role.png").match_in(dev.snapshot())
        if pos:
            logger.info("检测到<<角色管理>>图标，期望<<✅>>图标")
            dev.touch(pos)
            sleep(1)

        pos = Template(r"item/green-flag.png").match_in(dev.snapshot())
        if pos:
            logger.info("检测到<<✅>>图标，期望<<是>>按钮")
            x, y = pos
            if x < 1000:
                x += 1600
            else:
                x -= 500
            dev.touch((x, y))
            sleep(1)

        pos = Template(r"item/yes.png").match_in(dev.snapshot())
        if pos:
            logger.info("检测到<<是>>图标")
            dev.touch(pos)
            break

        sleep(1)
        logger.info("操作标志循环检测中... (%d/%d)" % (i + 1, threshold))
    else:
        logger.info("检测次数超出阈值仍未检测到相应标志，退出切换角色任务")
        return

    logger.info("等待角色切换进入游戏内堡界面中...")
    while not Template(r"item/home-map.png").match_in(dev.snapshot()):
        try:
            pkg_name = dev.get_top_activity()[0]
            if pkg_name != ROK_PACKAGE_NAME:
                dev.start_app(ROK_PACKAGE_NAME)
        except:
            pass
        sleep(1)
    else:
        logger.info("角色切换已进入游戏内堡界面")
        logger.info("已完成角色切换任务")


def home(threshold=5):
    """
    返回家
    :return: None
    """
    logger.info("开始检测当前界面，返回执政官内堡界面中...")
    for i in range(threshold):
        pos = Template("item/exit-game-tip.png").match_in(dev.snapshot())
        if pos:
            keyevent('BACK')
            sleep(2)

        pos = Template("item/home-tower.png").match_in(dev.snapshot())
        if pos is not None:
            dev.touch(pos)
            sleep(1)
            break

        pos = Template(r"item/home-map.png").match_in(dev.snapshot())
        if pos is not None:
            dev.touch(pos)
            sleep(1)
            dev.touch(pos)
            sleep(1)
            break

        keyevent('BACK')
        sleep(1)
        logger.info("界面循环检测中... (%d/%d)" % (i + 1, threshold))
    else:
        logger.info("检测次数超出阈值仍未检测到相应标志，开始重启应用实现进入内堡界面")
        dev.start_app_timing(ROK_PACKAGE_NAME, ROK_MAIN_ACTIVITY)
        while not Template(r'item/home-map.png').match_in(dev.snapshot()):
            try:
                pkg_name = dev.get_top_activity()[0]
                if pkg_name != ROK_PACKAGE_NAME:
                    dev.start_app(ROK_PACKAGE_NAME)
            except:
                pass
            sleep(1)

    logger.info("当前界面已恢复至执政官内堡初始界面")


def walker():
    if Template("item/earth.png").match_in(dev.snapshot()):
        # print("阶段三")
        pass
    elif not Template("item/menu.png").match_in(dev.snapshot()):
        # print("阶段二")
        pass
    else:
        dev.pinch(steps=50)

    info = dev.get_display_info()
    x = int(info['width'] / 2)
    y = int(info['height'] / 2)
    dx = random.randint(-500, 500)
    dy = random.randint(-500, 500)
    dev.swipe([x, y], [x + dx, y + dy])


def scout(threshold=3):
    logger.info("==================================================")
    logger.info("开始斥候任务")
    for i in range(threshold):
        pos = Template("item/home-tower.png").match_in(dev.snapshot())
        if pos:
            dev.touch(pos)
            sleep(1)
        else:
            pos = Template("item/home-map.png").match_in(dev.snapshot())
            if pos is None:
                logger.info("当前界面未知，退出本次斥候任务")
                return

        info = dev.get_display_info()
        w = info['width']
        h = info['height']
        dev.touch([int(w / 2), int(h / 2)])
        sleep(1)

        pos = Template("item/scout.png").match_in(dev.snapshot())
        if pos:
            dev.touch(pos)
            sleep(1)

        pos = Template("item/scout-manage-string.png").match_in(dev.snapshot())
        if pos:
            flag = False
            for j in range(2 * threshold):
                pos = Template("item/explore-string.png").match_in(dev.snapshot())
                if pos:
                    save_touch_screen(pos, dev.snapshot())
                    dev.touch(pos)
                    sleep(1)

                pos = Template("item/send-string.png").match_in(dev.snapshot())
                if pos:
                    if not flag:
                        flag = True
                        screen = dev.snapshot()
                        tpos = Template("item/go-back.png").match_in(screen) \
                               or Template("item/station.png").match_in(screen)
                        save_touch_screen(pos, screen)
                        if tpos:
                            dev.touch(tpos)
                            sleep(1)
                        else:
                            dev.touch(pos)
                            save_touch_screen(pos, screen)
                            sleep(1)
                            logger.info("已派遣斥候")
                            break
                    else:
                        dev.touch(pos)
                        save_touch_screen(pos, screen)
                        sleep(1)
                        logger.info("已派遣斥候")
                        break

                logger.info("循环检测标志中... (%d/%d)" % (j + 1, 2 * threshold))
            else:
                logger.info("检测次数超出阈值仍未检测到相应标志，退出斥候任务")
                return
    else:
        logger.info("检测次数超出阈值仍未检测到相应标志，退出斥候任务")


def farm(times=None, threshold=10, index=None):
    # 保证当前界面为堡外界面
    logger.info("开始检测当前界面是否为堡外界面...")
    for i in range(10):
        pos = Template("item/home-map.png").match_in(dev.snapshot())
        if pos:
            logger.info("检测到当前界面在执政官城堡内部，开始点击<<地图>>小图标显示堡外界面 (%d/%d)" % (i + 1, threshold))
            dev.touch(pos)
            logger.info("已点击<<地图>>小图标按钮")
            break

        pos = Template("item/home-tower.png").match_in(dev.snapshot())
        if pos:
            logger.info("检测到当前界面为堡外界面，退出堡外界面保证循环检测，进入下一步骤... (%d/%d)" % (i + 1, threshold))
            break

        dev.keyevent("BACK")
        sleep(1)
        logger.info("堡外界面循环检测中... (%d/%d)" % (i + 1, threshold))
    else:
        logger.info("检测次数超出阈值仍未检测到相应标志，退出采集任务")
        return

    info = dev.get_display_info()
    cx = int(info['width'] / 2)
    cy = int(info['height'] / 2)
    img_list = ("farm-string.png", "wood-string.png", "stone-string.png")
    img_string = ("农田", "木材", "石头", "金币")
    sc_counter = 0
    # key: r_index -> value: list
    has_searched_pos = dict()
    index_black = [False for i in range(len(img_list))]
    allow_remnant_ore = False
    for i in range(threshold):
        flag = False
        # 根据多次搜索反馈重新选择合理采集资源点种类
        logger.info("开始初始化本次循环采集的资源矿种类")
        while True:
            if index is None:
                r_index = random.randint(0, len(img_list) - 1)
            else:
                if isinstance(index, int):
                    r_index = index
                    if index_black[r_index]:
                        allow_remnant_ore = True
                else:
                    r_index = index[random.randint(0, len(index) - 1)]

            if all(index_black):
                logger.info("检测到所有种类的资源矿都含有残矿，忽略残矿检测，本次允许采集残矿")
                allow_remnant_ore = True
                break

            if not index_black[r_index]:
                if r_index not in has_searched_pos:
                    has_searched_pos[r_index] = []
                logger.info("已选择本次循环采集的资源矿种类：<<%s>>" % img_string[r_index])
                break

        logger.info("开始检测堡外界面采集入口标志")
        screen = dev.snapshot()
        pos = Template("item/search.png").match_in(screen)
        if pos:
            logger.info("检测到堡外界面采集入口标志<<搜索>>小图标")
            dev.touch(pos)
            logger.info("点击<<搜索>>小图标，进入资源搜索界面")
            # save_touch_screen(pos, screen)
            sleep(1)

        logger.info("开始检测资源搜索界面<<搜索>>文字蓝色按钮")
        screen = dev.snapshot()
        pos = Template("item/search-string.png").match_in(screen)
        if pos:
            logger.info("检测到资源搜索界面<<搜索>>文字蓝色按钮")
            logger.info("开始检测资源矿等级递增标志<<+>>号蓝色图标")
            pos = Template("item/jia.png").match_in(dev.snapshot())
            if pos:
                logger.info("检测到资源矿等级递增标志<<+>>号蓝色图标")
                logger.info("开始连续点击<<＋>>号图标，使其递增至最高级等级矿")
                for i in range(5):
                    dev.touch(pos)
                    logger.info("点击<<＋>>号图标 %d/%d" % (i + 1, 5))
                    sleep(0.2)

                sleep(1)

            logger.info("开始检测搜索前资源矿<<%s>>文字图标" % img_string[r_index])
            screen = dev.snapshot()
            pos = Template('item/' + img_list[r_index]).match_in(screen)
            if pos:
                logger.info("检测到搜索前资源矿<<%s>>文字图标" % img_string[r_index])
                # Todo 后续优化智能均衡选矿
                dev.touch(pos)
                logger.info("点击资源矿<<%s>>文字图标，进入下一步骤..." % img_string[r_index])
                save_touch_screen(pos, screen)
                sleep(1)

            tlc = 0
            r_index_plist = has_searched_pos[r_index]
            is_continue = False
            is_down = False
            search_click_counter = 0

            logger.info("开始%s资源矿采集保证循环检测..." % img_string[r_index])
            same_pos_times = 0
            for j in range(2 * threshold):
                logger.info("开始检测%s资源矿<<搜索>>文字按钮..." % img_string[r_index])
                screen = dev.snapshot()
                pos = Template('item/search-string.png').match_in(screen)
                if pos is None:
                    logger.info("检测到%s资源矿<<搜索>>文字按钮消失，开始检测当前搜索的资源点是否符合采集要求..." % img_string[r_index])
                    # 检查坐标是否搜索过
                    logger.info("开始检测%s资源点坐标" % img_string[r_index])
                    # pos = Template("item/cpos-flag.png").match_in(dev.snapshot())
                    # pos = Template("item/c2.png").match_in(dev.snapshot())
                    # if pos:
                    # logger.info("检测到%s资源点坐标位置参考标志<<收藏>>图标" % img_string[r_index])
                    # save_touch_screen(pos, screen)
                    # logger.info("开始以参考标志截取资源点坐标")
                    logger.info("开始向第三方平台发送 OCR 识别请求资源点坐标...")
                    st = time.time()
                    result = img_to_str(
                        np.array(cv2.imencode('.jpg',
                                              dev.snapshot()[15:65, 530: 850]
                                              # screen[pos[1] - 30:pos[1] + 30, pos[0] - 330:pos[0] - 100]
                                              )[1]).tobytes())
                    logger.info("收到请求结果：%s, 耗时：%.2f 秒" % ("".join(result), (time.time() - st)))
                    if result is not None:
                        # 判断当前坐标是否检测过
                        logger.info("开始检测坐标是否已经检测过...")
                        result = ",".join(re.findall(r'(?:\d){1,4}', result))
                        if result not in r_index_plist:
                            r_index_plist.append(result)
                            print(r_index_plist)
                            logger.info("检测到本次选矿是全新的位置")

                            # 检测残矿
                            if not allow_remnant_ore:
                                logger.info("开始检测残矿...")
                                for k in range(threshold):
                                    dev.touch((cx, cy))
                                    sleep(1)

                                    # 查找资源点详情界面
                                    screen = dev.snapshot()
                                    rs_pos = Template('item/res-sum.png').match_in(screen)
                                    if rs_pos:
                                        # 查找<<采集>>蓝色按钮
                                        screen = dev.snapshot()
                                        save_touch_screen((cx, cy), screen)
                                        pos = Template('item/gather-string.png').match_in(screen)
                                        if pos:
                                            dev.touch(pos)
                                            sleep(1)
                                            logger.info("开始检测当前搜索矿资源储量...")
                                            # 农田和木材 6|1008000  5|756000 4|504000 3|378000 2|252000 1|126000
                                            # 石头 6|756000 5|567000 4|378000 3|283500 2|189000 1|94500
                                            # 金币 6|33600 5|252000 4|168000 3|126000 2|84000 1|42000
                                            tvs = (
                                                1008000, 756000, 567000, 504000, 378000, 336000, 283500, 252000,
                                                189000, 126000,
                                                94500,
                                                84000, 42000)
                                            logger.info("开始向第三方平台发送 OCR 识别请求资源点资源储量...")
                                            st = time.time()
                                            result = img_to_str(
                                                np.array(cv2.imencode('.jpg',
                                                                      screen[rs_pos[1] - 25:rs_pos[1] + 25,
                                                                      rs_pos[0] + 300:rs_pos[0] + 550]
                                                                      )[1]).tobytes())
                                            logger.info(
                                                "收到请求结果：%s, 耗时：%.2f 秒" % ("".join(result), (time.time() - st)))

                                            if result is not None:
                                                if isinstance(result, str):
                                                    v = int(result.replace(",", ""))
                                                elif isinstance(result, list):
                                                    v = int("".join(result))

                                                if v in tvs:
                                                    is_continue = False
                                                    logger.info("检测到当前资源矿储量完整(%s)，开始采集..." % v)
                                                else:
                                                    is_continue = True
                                                    logger.info("检测到当前资源点储量 %s， 判定为残矿，开始重新选矿" % v)
                                                    dev.touch((cx, cy))
                                        else:
                                            is_continue = True
                                            search_click_counter = 0
                                            logger.info("检测到当前资源点已经被其他执政官占领，忽略当前矿，进行再选矿...")
                                            dev.touch((cx, cy))
                                        break
                                else:
                                    logger.info("检测次数超出阈值仍未检测到相应标志，退出采集任务")
                                    return
                                if not is_continue:
                                    break
                            else:
                                logger.info("忽略残矿检查，开始采集...")
                                break
                        else:
                            is_continue = True
                            if same_pos_times > 2:
                                is_down = True
                            else:
                                is_down = False
                            same_pos_times += 1
                            dev.touch((cx, cy))
                            logger.info("当前采集坐标(%s)，已被检测过判定为不适合采集坐标，忽略当前矿，进行再选矿..." % result)
                else:
                    logger.info("检测到%s资源矿<<搜索>>文字按钮..." % img_string[r_index])
                    search_click_counter += 1
                    dev.touch(pos)
                    logger.info("点击%s资源矿<<搜索>>文字按钮..." % img_string[r_index])
                    save_touch_screen(pos, screen)
                    sleep(1)

                if is_continue:
                    search_click_counter = 0
                    logger.info("开始检测资源采集界面入口标志<<搜索>>图标")
                    pos = Template("item/search.png").match_in(dev.snapshot())
                    if pos:
                        logger.info("检测到资源采集界面入口标志<<搜索>>图标")
                        dev.touch(pos)
                        sleep(1)

                if is_down or search_click_counter > 1:
                    search_click_counter = 0
                    screen = dev.snapshot()
                    logger.info("多次搜索当前等级资源矿，仍无适合采集矿，开始递减一次矿等级")
                    logger.info("开始检测资源矿递减标志<<->>图标")
                    pos = Template("item/jian.png").match_in(screen)
                    if pos:
                        same_pos_times = 0
                        logger.info("检测到资源矿递减标志<<->>图标")
                        if tlc == 5:
                            dev.touch((cx, cy))
                            flag = True
                            logger.info("检测到遍历所有等级都未搜索到可采集点，进行重新选取其他种类矿")
                            break
                        tlc += 1
                        dev.touch(pos)
                        save_touch_screen(pos, screen)
                        sleep(0.5)
                        logger.info("资源矿搜索等级当前等级%d" % (6 - tlc))

                is_down = False
                is_continue = False

                logger.info("资源矿采集保证循环检测... (%d/%d)" % (j + 1, 2 * threshold))
            else:
                logger.info("检测次数超出阈值仍未检测到相应标志，退出采集任务")
                return

            if flag:
                index_black[r_index] = True
                logger.info("添加%s资源矿至本次采集黑名单" % img_string[r_index])
                continue

            for i in range(threshold):
                pos = Template('item/create-troop-string.png').match_in(dev.snapshot())
                if pos:
                    logger.info("开始创建采集部队")
                    dev.touch(pos)
                    sleep(1)
                    break

                pos = Template('item/march-string.png').match_in(dev.snapshot())
                if pos:
                    logger.info("检测到队列已满，取消当前采集行军操作！")
                    dev.touch((cx, cy))
                    return
            else:
                logger.info("检测次数超出阈值仍未检测到相应标志，退出采集任务")
                return

            for i in range(threshold):
                pos = Template('item/march-string.png').match_in(dev.snapshot())
                if pos:
                    dev.touch(pos)
                    logger.info("已派遣采集行军部队")
                    sc_counter += 1
                    sleep(1)
                    break
            else:
                logger.info("检测次数超出阈值仍未检测到相应标志，退出采集任务")
                return

            if times is not None and times == sc_counter:
                break

        logger.info("操作标志循环检测中... (%d/%d)" % (i + 1, threshold))
    else:
        logger.info("检测次数超出阈值仍未检测到相应标志，退出采集任务")


if __name__ == "__main__":

    # if not cli_setup():
    logger = init_logging()
    logger.info("连接安卓模拟器中...")
    is_ok = False
    os.system("open /Applications/NemuPlayer.app")
    while not is_ok:
        try:
            auto_setup(__file__, logdir=True, devices=[
                "android:///%s" % (VM if DEBUG else WIRE_VIVO),
            ])
            dev = device()
            is_ok = True
        except:
            os.system("adb devices")

        sleep(1)

    logger.info("已连接上安卓模拟器")

    if not dev.check_app(ROK_PACKAGE_NAME):
        logger.error("检测到当前设备未安装 ROK 应用，自动化脚本执行结束")
        sys.exit(1)

    has_locked_rs_index = [0, 1, 2]
    alliance_name = '[11TC]'
    help_counter = 0
    loop_counter = 1
    forced_logout_counter = 1
    open_offline_sleep = True
    running_time = random.randint(60 * 30, 60 * 50)
    logger.info("ROK 自动化脚本开始运行...")
    logger.info("防封号保护：游戏将在运行%d分钟后进行下线休眠" % int(running_time / 60))

    start_time = time.time()
    while True:

        logger.info('守屏卫士第%d次巡逻中...' % loop_counter)

        flag = False
        # 检测应用是否正常运行中
        pkg_name = dev.get_top_activity()[0]
        if pkg_name != ROK_PACKAGE_NAME:
            logger.info("检测到当前 Top Activity 非 ROK 应用")
            logger.info("开始启动 ROK 应用，等待游戏进入执政官城堡主界面...")
            dev.start_app_timing(ROK_PACKAGE_NAME, ROK_MAIN_ACTIVITY)
            while not Template(r'item/home-map.png').match_in(dev.snapshot()):
                sleep(1)

        # 查找帮助小图标
        screen = dev.snapshot()
        pos = Template(r"item/help.png").match_in(screen)
        if pos is not None:
            flag = True
            x, y = pos
            help_counter += 1
            logger.info('检测到<<帮助>>图标(%d, %d)，小手第%d次点了起来' % (x, y, help_counter))
            dev.touch(pos)
            save_touch_screen(pos, screen)

        # 检查队列
        screen = dev.snapshot()
        pos = Template("item/troop-flag2.png").match_in(screen)
        try:
            if pos:
                save_touch_screen(pos, screen)
                # screen = screen[pos[1] - 25:pos[1] + 15, pos[0] + 60:pos[0] + 130]
                screen = screen[pos[1] - 25:pos[1] + 30, pos[0] + 60:pos[0] + 130]
                save_touch_screen([0, 0], screen)
                result = img_to_str(np.array(cv2.imencode('.jpg', screen)[1]).tobytes())
                if result is not None:
                    result = re.findall('(?:^\d{1}|\d{1}$)', result)
                    ut = int(result[0])
                    st = int(result[1])
                    if ut < st:
                        flag = True
                        logger.info("检测到空闲队列(%d/%d), 开始种田..." % (ut, st))
                        farm(times=st - ut, index=has_locked_rs_index)
            else:
                pos = Template("item/home-map.png").match_in(screen) or Template("item/home-tower.png").match_in(screen)
                if pos:
                    flag = True
                    logger.info("检测到所有队列空闲，开始种田...")
                    farm(index=has_locked_rs_index)
        except:
            logger.error("种田出现异常：%s" % traceback.format_exc())

        # 断开连接
        pos = Template('item/disconnect_tip_strings.png').match_in(dev.snapshot())
        if pos:
            pos = Template('item/blue_sure_string.png').match_in(dev.snapshot())
            if pos:
                dev.touch(pos)
                stop_app(ROK_PACKAGE_NAME)
                logger.info('检测到网络中断与游戏服务器断开连接，终止游戏应用进行重新启动操作')

        # 检测顶号
        pos = Template('item/logout_tip_strings.png').match_in(dev.snapshot())
        if pos:
            stop_app(ROK_PACKAGE_NAME)
            logger.info('检测到被顶号，十分钟后重新启动游戏应用')
            # 五分钟后重启
            st = time.time()
            while time.time() - st <= 30 * 60:
                sleep(1)

            start_time = time.time()
            logger.info("由于被顶号原因，游戏运行时长重新计时")
            logger.info("游戏已进入执政官城堡主界面，开始自动化任务...")
            continue
        else:
            home()

        # 查找人机验证奖励箱子
        screen = dev.snapshot()
        pos = Template(r"item/vcase.png").match_in(screen)
        if pos is not None:
            x, y = pos
            logger.info('检测到人机验证<<箱子>>图标(%d, %d)，进入验证步骤' % (x, y))
            dev.touch(pos)
            save_touch_screen(pos, screen)
            pass_geetest_vcode()

        # 漫游者
        # walker()

        sleep(30)
        loop_counter += 1

        end_time = time.time()
        logger.info("轮号倒计时：%d 秒" % (900-int(end_time-start_time)))
        if end_time - start_time >= 900:
            switch_role()
            start_time = time.time()

        # has_run_time = time.time() - start_time
        # if has_run_time >= running_time and open_offline_sleep:
        #     st = random.randint(60 * 5, 60 * 10)
        #     stop_app(ROK_PACKAGE_NAME)
        #     logger.info("游戏应用已运行 %d 分钟，开始下线休眠 %d 分钟" % (int(has_run_time / 60), int(st / 60)))
        #     sleep(st)
        #     start_time = time.time()
        #     running_time = random.randint(60 * 30, 60 * 50)
        #     logger.info("ROK 自动化脚本开始运行...")
        #     logger.info("防封号保护：游戏将在运行%d分钟后进行下线休眠" % int(running_time / 60))