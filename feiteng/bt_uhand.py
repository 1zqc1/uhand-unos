# bt_uhand.py
# 飞腾派 V3 与机械手蓝牙通信程序
# 使用 BLE GATT 协议
# 需要安装: pip install pexpect (可选)

import time
import subprocess

# HC-08 MAC 地址
HC08_MAC = "48:87:2D:7E:B4:37"

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
    data.append(CMD_SERVO_MOVE)         # func
    data.append(time_ms & 0xFF)         # time low
    data.append((time_ms >> 8) & 0xFF) # time high

    for servo_id, angle in servos:
        pos = int(SERVO_MIN + (angle / 180.0) * (SERVO_MAX - SERVO_MIN))
        data.append(servo_id)
        data.append(pos & 0xFF)
        data.append((pos >> 8) & 0xFF)

    return data


def send_via_gatttool(data):
    """通过 gatttool 发送数据"""
    # 将数据转换为 hex 字符串
    hex_str = ''.join(f'{b:02x}' for b in data)

    cmd = f'gatttool -b {HC08_MAC} --char-write-req -a 0x0001 -d {hex_str}'

    try:
        subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=2
        )
        return True
    except subprocess.TimeoutExpired:
        print("[错误] gatttool 超时")
        return False
    except Exception as e:
        print(f"[错误] {e}")
        return False


def connect_ble():
    """连接 BLE 设备"""
    print(f"[BLE] 连接到 {HC08_MAC}...")

    # 使用 gatttool 连接
    cmd = f'gatttool -b {HC08_MAC} -I'

    try:
        # 启动 gatttool 交互模式
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            text=True
        )

        time.sleep(0.5)

        # 发送连接命令
        proc.stdin.write("connect\n")
        proc.stdin.flush()
        time.sleep(1)

        # 检查是否连接成功
        output = proc.stderr.read(100)
        if b'Connection successful' in output or b'connected' in output.lower():
            print("[BLE] 连接成功!")
            return proc
        else:
            print("[BLE] 连接失败")
            proc.terminate()
            return None

    except Exception as e:
        print(f"[错误] {e}")
        return None


def disconnect_ble(proc):
    """断开 BLE 连接"""
    if proc:
        try:
            proc.stdin.write("disconnect\n")
            proc.stdin.flush()
            time.sleep(0.3)
            proc.terminate()
            print("[BLE] 已断开")
        except:
            pass


def set_all_servos(servos):
    """设置所有舵机角度"""
    cmd = build_servo_cmd(servos)
    send_via_gatttool(cmd)


def open_hand():
    """张开手"""
    servos = [(i+1, 180) for i in range(5)]
    servos.append((6, 90))
    cmd = build_servo_cmd(servos)
    send_via_gatttool(cmd)


def close_hand():
    """握拳"""
    servos = [(i+1, 0) for i in range(5)]
    servos.append((6, 90))
    cmd = build_servo_cmd(servos)
    send_via_gatttool(cmd)


def reset():
    """复位"""
    servos = [(i+1, 90) for i in range(6)]
    cmd = build_servo_cmd(servos)
    send_via_gatttool(cmd)


def set_servo(idx, angle):
    """设置单个舵机"""
    cmd = build_servo_cmd([(idx, angle)])
    send_via_gatttool(cmd)


# ==================== 使用示例 ====================
if __name__ == "__main__":
    print("=" * 40)
    print("飞腾派 V3 蓝牙控制机械手")
    print("=" * 40)

    # 连接 BLE
    ble = connect_ble()
    if not ble:
        print("[错误] 无法连接，请检查 HC-08 是否上电")
        exit(1)

    time.sleep(0.5)

    try:
        # 测试命令
        print("\n[测试] 复位...")
        reset()
        time.sleep(1)

        print("[测试] 张开手...")
        open_hand()
        time.sleep(1)

        print("[测试] 握拳...")
        close_hand()
        time.sleep(1)

        print("[测试] 设置单个舵机...")
        set_servo(1, 90)
        time.sleep(0.5)

        print("[测试] 设置所有舵机...")
        set_all_servos([0, 45, 90, 135, 180, 90])
        time.sleep(1)

        print("\n[完成] 所有测试完成!")

    finally:
        disconnect_ble(ble)