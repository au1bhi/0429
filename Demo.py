import time
import logging
import colorlog
import requests
import dataclasses
from json import JSONDecodeError

log_colors_config = {
    'DEBUG': 'red',  # cyan white
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'bold_red',
}


logger = logging.getLogger('logger_name')
# 输出到控制台
console_handler = logging.StreamHandler()
# 日志级别，logger 和 handler以最高级别为准，不同handler之间可以不一样，不相互影响
logger.setLevel(logging.DEBUG)
console_handler.setLevel(logging.DEBUG)

# 日志输出格式
console_formatter = colorlog.ColoredFormatter(
    fmt='%(log_color)s[%(asctime)s.%(msecs)03d] [%(levelname)s] : %(message)s',
    datefmt='%Y-%m-%d  %H:%M:%S',
    log_colors=log_colors_config
)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)
console_handler.close()


# 定义机器人的所有运行行为
class Action:
    MOVE_TO = 'slamtec.agent.actions.MoveToAction'
    GO_HOME = 'slamtec.agent.actions.GoHomeAction'
    ROTATE = 'slamtec.agent.actions.RotateToAction'


@dataclasses.dataclass
class RobotMessage:
    scene: str  # 场景
    intention: str  # 意图
    content: str  # 内容

    def to_dict(self):
        data = {key: getattr(self, key) for key in self.__annotations__.keys()}
        data['text'] = ''
        return data


# 机器人api
class RobotAPI:
    uri: str

    def __init__(self, robot_name: str, address: str = '8.130.69.6', port: str = '39099'):
        self.port = port
        self.uri = f'http://{address}:{port}'
        self.headers = {'Authorization': f'Robot {robot_name}'}

    # 创建新的运动行为
    # /api/core/motion/v1/actions
    def create_action(self, action_name: str, **options):
        url = self.uri + '/api/core/motion/v1/actions'
        data = {
            "action_name": action_name,
            "options": options
        }
        # pprint.pprint(data)
        resp = requests.post(url=url, json=data, headers=self.headers)
        res = resp.json()
        return res
    
    # 查询Action状态
    # /api/core/motion/v1/actions/<action_id>
    def ask_action(self, action_id):
        url = self.uri + f'/api/core/motion/v1/actions/{action_id}'
        res = requests.get(url=url, headers=self.headers).json()
        return res
    
    # 获取机器人位姿
    # /api/core/slam/v1/localization/pose
    def get_pose(self):
        url = self.uri + f'/api/core/slam/v1/localization/pose'
        try:
            res = requests.get(url=url, headers=self.headers).json()
            return res
        except JSONDecodeError:
            return self.get_points()

    # 获取当前地图中的所有POI
    # /api/core/artifact/v1/pois
    def get_points(self):
        url = self.uri + '/api/core/artifact/v1/pois'
        res = requests.get(url, headers=self.headers).json()
        return res


class Robot:
    uri: str

    def __init__(self, api: RobotAPI):
        self.api = api

    # 监听行为，阻塞至该行为结束！
    def listen_util_action_end(self, action_id):
        while True:
            time.sleep(0.1)
            res = self.api.ask_action(action_id=action_id)
            if res['state']['status'] == 4:
                break

    # 执行行为，阻塞至该行为结束！
    def execute_action(self, action_name: str, **kwargs):
        res = self.api.create_action(action_name, **kwargs)
        action_id = res['action_id']
        self.listen_util_action_end(action_id)

    # 行为-回到充电桩
    def action_go_home(self):
        options = {
            'gohome_options': {
                'flags': 'dock',
                'back_to_landing': True,
                'charging_retry_count': 1,
                'move_options': {
                    'mode': 0
                }
            }
        }
        self.execute_action(action_name=Action.GO_HOME, **options)

    # 行为-原地旋转
    def action_rotate(self, angle):
        options = {
            'angle': angle
        }
        self.execute_action(action_name=Action.ROTATE, **options)

    # 行为-移动+原地旋转
    def action_move_to(self, x, y, z, yaw):
        options = {
            "target": {"x": x, "y": y, "z": z},
            "move_options": {
                "mode": 0,
                "flags": [],
                "yaw": yaw,
                "acceptable_precision": 0,
                "fail_retry_count": 0,
                "speed_ratio": 0}
        }
        self.execute_action(action_name=Action.MOVE_TO, **options)
        self.action_rotate(yaw)

    def speak(self, message: RobotMessage):
        uri = f'http://8.130.69.6:39099'
        if self.api.port.__eq__('1448'):
            while True:
                resp = requests.post(f'{uri}/api/setData', json=message.to_dict())
                resp = resp.json()
                if resp['code'] == '1':
                    break
                time.sleep(0.5)
        logger.debug('信息发送成功！')
        if self.api.port.__eq__('1448'):
            while True:
                resp = requests.get(f'{uri}/api/getStatus')
                resp = resp.json()
                if resp['code'] == '0':
                    break
                time.sleep(0.5)
        logger.debug('机器人已播报完成!')

if __name__ == '__main__':
    # 注意：机器人名不能有空格
    one_api = RobotAPI('avatar123', '8.130.175.216', '39092')  # 虚拟仿真环境的api
    # one_api = RobotAPI('avatar123', '192.168.11.1', '1448')  # 实体机器人api
    robot = Robot(one_api)
    # 防止机器人不在充电桩原点
    logger.debug(f'机器人当前位置{one_api.get_pose()}')
    logger.info('机器人准备回到充电桩！')
    robot.action_go_home()
    # 这里是你的场景
    s = 'mainProcess'
    # 点位1-8 为意图
    # 场景+意图 相当于 上下文语境
    # RobotMessage 第三个参数为大模型的问题
    # 大模型会结合 上下文语境 回答你的问题，然后由机器人播报出来！
    # 场景+意图配置网站：http://8.130.69.6:39099/admin/
    # 配置演示账号：demo 密码：admin123456
    speak = [
        RobotMessage(s, 'Pos1', '介绍|迎宾|导览|展览'),
        RobotMessage(s, 'Pos2', '介绍|石器时代|夏|商|周'),
        RobotMessage(s, 'Pos3', '介绍|春秋|战国|时期'),
        RobotMessage(s, 'Pos4', '介绍|秦|汉|两代'),
        RobotMessage(s, 'Pos5', '介绍|三国|两晋|南北朝|时期'),
        RobotMessage(s, 'Pos6', '介绍|隋唐|五代|十国|时期'),
        RobotMessage(s, 'Pos7', '介绍|宋辽|金|西夏|元|五代'),
        RobotMessage(s, 'Pos8', '介绍|明朝'),
        RobotMessage(s, 'Pos9', '介绍|清朝|结束')
    ]
    # 获取到所有点位
    logger.warning('开始获取所有目标点！！！')
    points = one_api.get_points()
    points = sorted(points, key=lambda x: x['metadata']['display_name'])
    print(points)
    # 开启跑点
    for index, point in enumerate(points):
        display_name = point['metadata']['display_name']
        pose = point['pose']
        tx, ty, yaw = pose['x'], pose['y'], pose['yaw']
        logger.info(f'准备移动到->({tx}, {ty})')
        robot.action_move_to(tx, ty, 0, yaw)
        robot.speak(speak[index])
        # input('输入Enter继续:')
        logger.warning(f'已移动到指定位置！当前位置{one_api.get_pose()}！！！')
    robot.action_go_home()
