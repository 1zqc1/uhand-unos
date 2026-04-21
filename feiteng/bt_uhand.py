# bt_uhand.py
# 飞腾派 V3 与机械手蓝牙通信程序
# 使用 Bluetooth Socket 连接
# 安装: pip install pyserial (仅用于调试)

import socket
import time
import os

# HC-08 MAC 地址
HC08_MAC = "48:87:2D:7E:B4:37"
RFCOMM_PORT = 1

# 协议常量
FRAME_HEADER = 0x55
CMD_SERVO_MOVE = 0x03
SERVO_MIN = 1100
SERVO_MAX = 1950


def build_servo_cmd(servos):
    """构建舵机移动命令"""
    time_ms = 500
    data = [FRAME_HEADER, FRAME_HEADER]
    data.append(len(servos) * 3 + 3)  # num
    data.append(CMD_SERVO_MOVE)          # func
    data.append(time_ms & 0xFF)         # time low
    data.append((time_ms >> 8) & 0xFF) # time high

    for servo_id, angle in servos:
        pos = int(SERVO_MIN + (angle / 180.0) * (SERVO_MAX - SERVO_MIN))
        data.append(servo_id)
        data.append(pos & 0xFF)
        data.append((pos >> 8) & 0xFF)

    return bytes(data)


def ensure_rfcomm():
    """确保 rfcomm0 存在"""
    try:
        # 检查 rfcomm0 是否存在
        if not os.path.exists("/dev/rfcomm0"):
            print("[蓝牙] 绑定 rfcomm0...")
            os.system(f"rfcomm bind rfcomm0 {HC08_MAC} {RFCOMM_PORT}")
            time.sleep(1)
        else:
            print("[蓝牙] rfcomm0 已存在")
    except Exception as e:
        print(f"[错误] {e}")


class UHandBT:
    def __init__(self):
        self.sock = None

    def connect(self):
        """通过 socket 连接"""
        try:
            self.sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            self.sock.connect((HC08_MAC, RFCOMM_PORT))
            print(f"[蓝牙] 连接成功!")
            return True
        except Exception as e:
            print(f"[错误] 连接失败: {e}")
            return False

    def send(self, data):
        """发送数据"""
        if not self.sock:
            print("[错误] 未连接")
            return False
        try:
            self.sock.send(data)
            print(f"[发送] {[hex(b) for b in data]}")
            return True
        except Exception as e:
            print(f"[错误] 发送失败: {e}")
            return False

    def close(self):
        """关闭连接"""
        if self.sock:
            self.sock.close()

    def set_servo(self, idx, angle):
        cmd = build_servo_cmd([(idx, angle)])
        return self.send(cmd)

    def set_all_servos(self, angles):
        servos = [(i+1, angles[i]) for i in range(len(angles))]
        cmd = build_servo_cmd(servos)
        return self.send(cmd)

    def open_hand(self):
        servos = [(i+1, 180) for i in range(5)]
        servos.append((6, 90))
        cmd = build_servo_cmd(servos)
        return self.send(cmd)

    def close_hand(self):
        servos = [(i+1, 0) for i in range(5)]
        servos.append((6, 90))
        cmd = build_servo_cmd(servos)
        return self.send(cmd)

    def reset(self):
        servos = [(i+1, 90) for i in range(6)]
        cmd = build_servo_cmd(servos)
        return self.send(cmd)


def main():
    print("=" * 40)
    print("飞腾派 V3 蓝牙控制机械手 (Socket)")
    print("=" * 40)

    # 确保 rfcomm0 存在
    ensure_rfcomm()

    hand = UHandBT()

    if hand.connect():
        print("\n[测试] 复位...")
        hand.reset()
        time.sleep(1)

        print("\n[测试] 张开手...")
        hand.open_hand()
        time.sleep(1)

        print("\n[测试] 握拳...")
        hand.close_hand()
        time.sleep(1)

        print("\n[测试] 设置舵机1到90度...")
        hand.set_servo(1, 90)
        time.sleep(0.5)

        print("\n[测试] 设置所有舵机...")
        hand.set_all_servos([0, 45, 90, 135, 180, 90])
        time.sleep(1)

        print("\n[完成] 所有测试完成!")
        hand.close()
    else:
        print("[错误] 无法连接")


if __name__ == "__main__":
    main()