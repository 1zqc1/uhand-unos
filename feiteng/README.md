# 飞腾派 V3 蓝牙控制机械手

## 文件说明

- `bt_uhand.py` - 蓝牙通信主程序

## 依赖安装

```bash
pip install pyserial pybluez
```

麒麟/星光国产系统还需：
```bash
sudo apt install bluetooth libbluetooth-dev
```

## 接线

| HC-08 | Arduino UNO |
|-------|-------------|
| TX    | D8          |
| RX    | D9          |
| VCC   | 5V          |
| GND   | GND         |

## 运行

```bash
cd feiteng
python bt_uhand.py
```