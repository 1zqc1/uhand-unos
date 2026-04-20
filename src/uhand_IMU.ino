#include <FastLED.h>
#include <Servo.h>
#include <MPU6050.h>
#include "tone.h"
#include "actions.h"
#include "uhand_servo.h"
#include "Ultrasound.h"

// 动作组数据定义
uint8_t action[action_count][7] =
    {
      {1,0,0,0,0,0,90},
      {1,180,180,180,180,180,0},
      {1,19,43,40,8,23,116}
    };

// MPU6050 对象
MPU6050 accelgyro;
int16_t ax, ay, az;
int16_t gx, gy, gz;
float ax0, ay0, az0;
float gx0, gy0, gz0;
float ax1, ay1, az1;
float gx1, gy1, gz1;

int ax_offset, ay_offset, az_offset, gx_offset, gy_offset, gz_offset;
float radianX;
float radianY;
float radianX_last;
float radianY_last;
float radianYaw_last;

// 超声波对象
Ultrasound ul;

// 音调定义
const static uint16_t DOC6[] = { TONE_C6 };

/* 引脚定义 */
const static uint8_t servoPins[6] = { 7, 6, 5, 4, 3, 2 };
const static uint8_t buzzerPin = 11;
const static uint8_t rgbPin = 13;

// 动作组控制对象
HW_ACTION_CTL action_ctl;
// RGB灯控制对象
static CRGB rgbs[1];
// 舵机控制对象
Servo servos[6];

// 蜂鸣器相关变量
static uint16_t tune_num = 0;
static uint32_t tune_beat = 10;
static uint16_t *tune;

// 云台 PI 控制参数
static float gimbal_target_angle = 0.0f;
static float gimbal_output = 90.0f;
static float gimbal_integral = 0.0f;
static uint8_t gimbal_servo_idx = 5;

void setup() {
  Serial.begin(9600);  // 蓝牙协议使用9600波特率
  Serial.setTimeout(500);

  // 绑定舵机IO口
  for (int i = 0; i < 6; ++i) {
    servos[i].attach(servoPins[i], 500, 2500);
  }

  // RGB灯初始化
  FastLED.addLeds<WS2812, rgbPin, GRB>(rgbs, 1);
  rgbs[0] = CRGB(0, 100, 0);
  FastLED.show();

  // 蜂鸣器初始化
  pinMode(buzzerPin, OUTPUT);
  tone(buzzerPin, 1000);
  delay(100);
  noTone(buzzerPin);

  // MPU6050 配置
  accelgyro.initialize();
  accelgyro.setFullScaleGyroRange(3);
  accelgyro.setFullScaleAccelRange(1);
  delay(200);
  accelgyro.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
  ax_offset = ax;
  ay_offset = ay;
  az_offset = az - 8192;
  gx_offset = gx;
  gy_offset = gy;
  gz_offset = gz;

  delay(1000);
  Serial.println("start");
}

void loop() {
  // 蓝牙接收并解析
  action_ctl.blue_ctl_receive();
  // 蓝牙控制任务
  action_ctl.blue_task();
  // 超声波任务（根据距离控制手指张合）
  ultrasound_task();
  // 蜂鸣器任务
  tune_task();
  // 舵机控制（手指 + 云台）
  servo_control();
  // 动作组运动任务
  action_ctl.action_task();
  // 更新MPU6050数据
  update_mpu6050();
}

// 超声波任务（融合核心：替代原user_task状态机）
void ultrasound_task(void)
{
  static uint32_t last_tick = 0;
  if (millis() - last_tick < 100) {
    return;
  }
  last_tick = millis();

  int dis = ul.Filter();

  if (dis >= 200) {
    for (int i = 0; i < 5; ++i) {
      action_ctl.extended_func_angles[i] = 180;
    }
    rgbs[0].r = 0;
    rgbs[0].g = 0;
    rgbs[0].b = 255;
    FastLED.show();
    ul.Color(0, 0, 255, 0, 0, 255);
  } else if (dis <= 50 && dis >= 0) {
    for (int i = 0; i < 5; ++i) {
      action_ctl.extended_func_angles[i] = 0;
    }
    rgbs[0].r = 255;
    rgbs[0].g = 0;
    rgbs[0].b = 0;
    FastLED.show();
    ul.Color(255, 0, 0, 255, 0, 0);
  } else {
    uint8_t r = map(dis, 50, 200, 255, 0);
    uint8_t b = map(dis, 50, 200, 0, 255);
    uint8_t angle = map(dis, 50, 200, 0, 180);
    for (int i = 0; i < 5; ++i) {
      action_ctl.extended_func_angles[i] = angle;
    }
    rgbs[0].r = r;
    rgbs[0].g = 0;
    rgbs[0].b = b;
    FastLED.show();
    ul.Color(r, 0, b, r, 0, b);
  }
}

// 更新MPU6050数据（含 yaw 积分和云台目标计算）
void update_mpu6050(void)
{
  static uint32_t timer_u;
  if (timer_u < millis())
  {
    timer_u = millis() + 20;
    accelgyro.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

    // 一阶低通滤波（加速度）
    ax0 = ((float)(ax)) * 0.3f + ax0 * 0.7f;
    ay0 = ((float)(ay)) * 0.3f + ay0 * 0.7f;
    az0 = ((float)(az)) * 0.3f + az0 * 0.7f;
    ax1 = (ax0 - ax_offset) / 8192.0f;
    ay1 = (ay0 - ay_offset) / 8192.0f;
    az1 = (az0 - az_offset) / 8192.0f;

    // 一阶低通滤波（角速度）
    gx0 = ((float)(gx)) * 0.3f + gx0 * 0.7f;
    gy0 = ((float)(gy)) * 0.3f + gy0 * 0.7f;
    gz0 = ((float)(gz)) * 0.3f + gz0 * 0.7f;
    gx1 = (gx0 - gx_offset);
    gy1 = (gy0 - gy_offset);
    gz1 = (gz0 - gz_offset);

    // Pitch 角（X轴倾角）
    radianX = atan2(ay1, az1) * 180.0f / 3.1415926f;
    float radian_temp = (float)(gx1) / 16.4f * 0.02f;
    radianX_last = 0.8f * (radianX_last + radian_temp) + (-radianX) * 0.2f;

    // Roll 角（Y轴倾角）
    radianY = atan2(ax1, az1) * 180.0f / 3.1415926f;
    radian_temp = (float)(gy1) / 16.4f * 0.01f;
    radianY_last = 0.8f * (radianY_last + radian_temp) + (-radianY) * 0.2f;

    // Yaw 角（Z轴偏航角）— 纯陀螺仪积分
    // 注意：无磁力计情况下无法获得绝对 yaw，这里只做积分跟踪
    float yaw_delta = (float)gz1 / 16.4f * 0.02f;
    radianYaw_last += yaw_delta;

    // 限幅（-180 ~ 180）
    if (radianYaw_last > 180.0f)  radianYaw_last -= 360.0f;
    if (radianYaw_last < -180.0f) radianYaw_last += 360.0f;

    // 旋转方向与加速度方向相反：
    // 向右倾斜(radianX_last > 0) → 云台向左转 → gimbal_target_angle 为负（PI控制器会减少输出）
    gimbal_target_angle = -radianX_last;
  }
}

// 云台 PI 控制（每20ms调用一次）
// 误差 = -radianX_last → 右倾时 error<0 → 输出减小 → 舵机左转
static void gimbal_control(void)
{
  const float Kp = 1.2f;    // 比例增益
  const float Ki = 0.08f;   // 积分增益
  const float integ_max = 40.0f;  // 积分限幅
  const float out_max = 180.0f;  // 输出限幅

  float error = gimbal_target_angle;  // = -radianX_last

  // 积分项（含抗积分饱和）
  gimbal_integral += error * Ki;
  if (gimbal_integral > integ_max)  gimbal_integral = integ_max;
  if (gimbal_integral < -integ_max) gimbal_integral = -integ_max;

  // PI 输出
  float output = Kp * error + gimbal_integral;

  // 输出限幅
  if (output > out_max) output = out_max;
  if (output < 0.0f) output = 0.0f;

  gimbal_output = output;
}

// 舵机控制任务（手指 + 云台分离）
void servo_control(void) {
  static uint32_t last_tick = 0;
  static float servo_angles[6] = { 130, 130, 130, 130, 130, 90 };
  if (millis() - last_tick < 20) {
    return;
  }
  last_tick = millis();

  // 云台 PI 控制
  gimbal_control();

  for (int i = 0; i < 6; ++i) {
    if (i == gimbal_servo_idx) {
      // 云台舵机：PI 控制输出，直接写入（无滤波延迟）
      servo_angles[i] = gimbal_output;
      servos[i].write((uint8_t)servo_angles[i]);
    } else {
      // 手指舵机：平滑插值
      servo_angles[i] = servo_angles[i] * 0.90f + action_ctl.extended_func_angles[i] * 0.10f;
      servos[i].write(i == 0 ? (uint8_t)(180 - servo_angles[i]) : (uint8_t)servo_angles[i]);
    }
  }
}

// 蜂鸣器任务
void tune_task(void) {
  static uint32_t l_tune_beat = 0;
  static uint32_t last_tick = 0;
  if (millis() - last_tick < l_tune_beat && tune_beat == l_tune_beat) {
    return;
  }
  l_tune_beat = tune_beat;
  last_tick = millis();
  if (tune_num > 0) {
    tune_num -= 1;
    tone(buzzerPin, *tune++);
  } else {
    noTone(buzzerPin);
    tune_beat = 10;
    l_tune_beat = 10;
  }
}

// 蜂鸣器鸣响函数
void play_tune(uint16_t *p, uint32_t beat, uint16_t len) {
  tune = p;
  tune_beat = beat;
  tune_num = len;
}