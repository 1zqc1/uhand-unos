#ifndef _HW_ACTION_CTL_
#define _HW_ACTION_CTL_
#include "actions.h"

// 蓝牙接收存储变量
struct uHand_Servo{
  uint8_t num;
  uint16_t time;
  struct LobotServo {
    uint8_t  ID;
    uint16_t Position;
  } servos[6];
};

class HW_ACTION_CTL{
  public:
    uint8_t extended_func_angles[6] = { 0,0,0,0,0, 90 };
    void action_set(int num);
    int action_state_get(void);
    void action_task(void);

    // 蓝牙控制任务
    void blue_task(void);
    void blue_ctl_receive(void);
    bool blue_get_servos(struct uHand_Servo* uhand_servos);

  private:
    int action_num = 0;
};

#endif