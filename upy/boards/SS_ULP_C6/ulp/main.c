

#include <stdint.h>
/*#include "ulp_riscv_gpio.h"*/
/*#include "ulp_riscv_utils.h"*/
/*#include "ulp_riscv.h"*/

#define LED_GPIO_NUM 3

unsigned int var_counter = 0;
unsigned int var_count = 1;

void main(){
      if(var_count){
          var_counter++;
      }
      /*ulp_riscv_gpio_output_level(LED_GPIO_NUM, 1);*/
      /*ulp_riscv_gpio_output_level(LED_GPIO_NUM, 0);*/
}
