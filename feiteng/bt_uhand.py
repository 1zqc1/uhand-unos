# bt_uhand.py
# 飞腾派 V3 与机械手蓝牙通信程序
# 使用原始二进制协议 (0x55 0x55 帧头)
# 需要安装: pip install pyserial pybluez

import serial
import bluetooth
import time
import threading

class UHandBT:
    # 协议常量
    FRAME_HEADER = 0x55
    CMD_SERVO_MOVE = 0x03
    CMD_ACTION_GROUP_RUN = 0x06
    CMD_ACTION_GROUP_STOP = 0x07
    CMD_ACTION_GROUP_SPEED = 0x0B
    CMD_GET_BATTERY_VOLTAGE = 0x0F

    # 舵机角度范围
    SERVO_MIN = 1100
    SERVO_MAX = 1950

    def __init__(self, hc08_mac=None):
        self.mac = hc08_mac
        self.port = 1
        self.socket = None
        self.connected = False
        self.running = False

    # 搜索附近的HC-08设备
    def discover_hc08(self, timeout=10):
        print("[蓝牙] 搜索附近设备...")
        nearby_devices = bluetooth.discover_devices(duration=timeout, lookup_names=True)
        hc08_devices = []
        for addr, name in nearby_devices:
            if name and ('HC' in name.upper() or 'BT' in name.upper()):
                hc08_devices.append((addr, name))
                print(f"  发现: {name} @ {addr}")
        return hc08_devices

    # 连接HC-08（蓝牙RFCOMM）
    def connect_rfcomm(self, mac=None):
        if mac:
            self.mac = mac
        if not self.mac:
            print("[错误] 请指定HC-08的MAC地址")
            return False

        try:
            print(f"[蓝牙] 连接到 {self.mac} ...")
            self.socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            self.socket.connect((self.mac, self.port))
            self.connected = True
            print("[蓝牙] 连接成功！")
            return True
        except Exception as e:
            print(f"[错误] 连接失败: {e}")
            self.connected = False
            return False

    # 发送原始协议数据
    def send_raw(self, data):
        if not self.connected:
            print("[错误] 未连接")
            return False
        try:
            self.socket.send(bytes(data))
            print(f"[发送] {[hex(b) for b in data]}")
            return True
        except Exception as e:
            print(f"[错误] 发送失败: {e}")
            self.connected = False
            return False

    # 构建舵机移动命令
    # servos: [(id, angle), ...] angle范围 0-180
    def build_servo_move_cmd(self, servos):
        """
        帧格式: 0x55 0x55 num(1) func(1) time_l(1) time_h(1) servo1_id(1) pos_l(1) pos_h(1) ...
        """
        # 计算时间（固定500ms）
        time_ms = 500
        time_l = time_ms & 0xFF
        time_h = (time_ms >> 8) & 0xFF

        data = [self.FRAME_HEADER, self.FRAME_HEADER]
        data.append(len(servos) * 3 + 3)  # num = servo_count * 3 + 3
        data.append(self.CMD_SERVO_MOVE)   # func
        data.append(time_l)                # time low
        data.append(time_h)                # time high

        for servo_id, angle in servos:
            # 将 0-180 度映射到 1100-1950
            pos = int(self.SERVO_MIN + (angle / 180.0) * (self.SERVO_MAX - self.SERVO_MIN))
            pos_l = pos & 0xFF
            pos_h = (pos >> 8) & 0xFF
            data.append(servo_id)   # servo id (1-6)
            data.append(pos_l)       # position low
            data.append(pos_h)       # position high

        return data

    # 设置单个舵机角度
    def set_servo(self, idx, angle):
        # idx: 1-6 (对应大拇指到云台)
        # angle: 0-180
        cmd = self.build_servo_move_cmd([(idx, angle)])
        return self.send_raw(cmd)

    # 设置所有舵机角度
    def set_all_servos(self, angles):
        # angles: [a1, a2, a3, a4, a5, a6] 对应 1-6 号舵机
        servos = [(i+1, angles[i]) for i in range(len(angles))]
        cmd = self.build_servo_move_cmd(servos)
        return self.send_raw(cmd)

    # 张开手 (所有手指180度)
    def open_hand(self):
        servos = [(i+1, 180) for i in range(5)]  # 手指张开
        servos.append((6, 90))  # 云台居中
        cmd = self.build_servo_move_cmd(servos)
        return self.send_raw(cmd)

    # 握拳 (所有手指0度)
    def close_hand(self):
        servos = [(i+1, 0) for i in range(5)]  # 手指闭合
        servos.append((6, 90))  # 云台居中
        cmd = self.build_servo_move_cmd(servos)
        return self.send_raw(cmd)

    # 复位
    def reset(self):
        servos = [(i+1, 90) for i in range(6)]  # 所有舵机归中
        cmd = self.build_servo_move_cmd(servos)
        return self.send_raw(cmd)

    # 动作组运行命令
    def play_action_group(self, group_num):
        """
        帧格式: 0x55 0x55 num func group_num time_l time_h
        """
        time_ms = 500
        time_l = time_ms & 0xFF
        time_h = (time_ms >> 8) & 0xFF

        data = [
            self.FRAME_HEADER, self.FRAME_HEADER,
            4,                    # num = 4
            self.CMD_ACTION_GROUP_RUN,
            group_num,
            time_l,
            time_h
        ]
        return self.send_raw(data)

    # 接收数据（后台线程）
    def receive_loop(self):
        print("[蓝牙] 开始接收数据...")
        while self.running and self.connected:
            try:
                data = self.socket.recv(1024)
                if data:
                    print(f"[接收] {[hex(b) for b in data]}")
            except Exception as e:
                print(f"[错误] 接收异常: {e}")
                break
        print("[蓝牙] 接收线程结束")

    # 启动接收线程
    def start_receiving(self):
        self.running = True
        self.recv_thread = threading.Thread(target=self.receive_loop)
        self.recv_thread.daemon = True
        self.recv_thread.start()

    # 关闭连接
    def close(self):
        print("[蓝牙] 关闭连接...")
        self.running = False
        if self.socket:
            self.socket.close()
        self.connected = False


# ==================== 使用示例 ====================
if __name__ == "__main__":
    hand = UHandBT()

    # 方式1：自动搜索HC-08
    devices = hand.discover_hc08()
    if devices:
        mac, name = devices[0]
        hand.connect_rfcomm(mac)
    else:
        # 方式2：手动指定MAC地址
        # hand.connect_rfcomm("00:11:22:33:44:55")
        pass

    if hand.connected:
        hand.start_receiving()

        # 测试命令
        time.sleep(0.5)

        hand.reset()  # 复位
        time.sleep(1)

        hand.open_hand()  # 张开手
        time.sleep(1)

        hand.close_hand()  # 握拳
        time.sleep(1)

        hand.set_servo(1, 90)  # 设置舵机1（大拇指）到90度
        time.sleep(0.5)

        hand.set_all_servos([0, 45, 90, 135, 180, 90])  # 设置所有舵机
        time.sleep(1)

        time.sleep(2)
        hand.close()


# ==================== 协议说明 ====================
"""
原始协议帧格式:
| 0x55 | 0x55 | num | func | data... |
|------|------|-----|------|---------|

CMD_SERVO_MOVE (0x03):
| num | func | time_L | time_H | servo1_id | pos_L | pos_H | servo2_id | pos_L | pos_H | ... |

舵机角度映射:
- 舵机ID: 1-6 (1=大拇指, 2=食指, 3=中指, 4=无名指, 5=小指, 6=云台)
- 舵机角度范围: 1100-1950 对应 0-180度
- 大拇指角度映射相反: 1100->180, 1950->0

其他命令:
- CMD_ACTION_GROUP_RUN (0x06): 运行动作组
- CMD_ACTION_GROUP_STOP (0x07): 停止动作组
- CMD_ACTION_GROUP_SPEED (0x0B): 设置动作组速度
- CMD_GET_BATTERY_VOLTAGE (0x0F): 获取电池电压
"""