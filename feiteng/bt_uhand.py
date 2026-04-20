# bt_uhand.py
# 飞腾派 V3 与机械手蓝牙通信程序
# 使用 bleak BLE 库
# 安装: pip install bleak

import asyncio
from bleak import BleakClient

# HC-08 MAC 地址
HC08_MAC = "48:87:2D:7E:B4:37"

# HC-08 BLE UUID (串口透传服务)
SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

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


class UHandBLE:
    def __init__(self, mac):
        self.mac = mac
        self.client = None
        self.connected = False

    async def connect(self):
        """连接 BLE 设备"""
        try:
            self.client = BleakClient(self.mac)
            await self.client.connect()
            self.connected = self.client.is_connected
            return self.connected
        except Exception as e:
            print(f"[错误] 连接失败: {e}")
            return False

    async def disconnect(self):
        """断开连接"""
        if self.client:
            await self.client.disconnect()
            self.connected = False

    async def send(self, data):
        """发送数据"""
        if not self.connected:
            print("[错误] 未连接")
            return False
        try:
            await self.client.write_gatt_char(CHAR_UUID, data)
            return True
        except Exception as e:
            print(f"[错误] 发送失败: {e}")
            return False

    async def set_servo(self, idx, angle):
        """设置单个舵机"""
        cmd = build_servo_cmd([(idx, angle)])
        return await self.send(cmd)

    async def set_all_servos(self, angles):
        """设置所有舵机 [a1,a2,a3,a4,a5,a6]"""
        servos = [(i+1, angles[i]) for i in range(len(angles))]
        cmd = build_servo_cmd(servos)
        return await self.send(cmd)

    async def open_hand(self):
        """张开手"""
        servos = [(i+1, 180) for i in range(5)]
        servos.append((6, 90))
        cmd = build_servo_cmd(servos)
        return await self.send(cmd)

    async def close_hand(self):
        """握拳"""
        servos = [(i+1, 0) for i in range(5)]
        servos.append((6, 90))
        cmd = build_servo_cmd(servos)
        return await self.send(cmd)

    async def reset(self):
        """复位"""
        servos = [(i+1, 90) for i in range(6)]
        cmd = build_servo_cmd(servos)
        return await self.send(cmd)


async def main():
    print("=" * 40)
    print("飞腾派 V3 蓝牙控制机械手 (bleak)")
    print("=" * 40)

    hand = UHandBLE(HC08_MAC)

    # 连接
    print(f"\n[BLE] 连接到 {HC08_MAC}...")
    if await hand.connect():
        print("[BLE] 连接成功!")
    else:
        print("[错误] 连接失败")
        return

    try:
        # 测试
        print("\n[测试] 复位...")
        await hand.reset()
        await asyncio.sleep(1)

        print("[测试] 张开手...")
        await hand.open_hand()
        await asyncio.sleep(1)

        print("[测试] 握拳...")
        await hand.close_hand()
        await asyncio.sleep(1)

        print("[测试] 设置舵机1到90度...")
        await hand.set_servo(1, 90)
        await asyncio.sleep(0.5)

        print("[测试] 设置所有舵机...")
        await hand.set_all_servos([0, 45, 90, 135, 180, 90])
        await asyncio.sleep(1)

        print("\n[完成] 所有测试完成!")

    finally:
        await hand.disconnect()
        print("[BLE] 已断开")


if __name__ == "__main__":
    asyncio.run(main())