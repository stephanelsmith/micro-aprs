/* ULP-RISC-V example

   This example code is in the Public Domain (or CC0 licensed, at your option.)

   Unless required by applicable law or agreed to in writing, this
   software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
   CONDITIONS OF ANY KIND, either express or implied.

   This code runs on ULP-RISC-V  coprocessor
*/

#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include "ulp_riscv.h"
#include "ulp_riscv_utils.h"
#include "ulp_riscv_gpio.h"
#include "ulp_riscv_adc_ulp_core.h"
#include "hal/adc_types.h"

unsigned int var_vbat_raw;
unsigned int var_toggle = 1;
unsigned int var_counter = 0;

int main (void)
{      
    //GPIO 2
    var_vbat_raw = ulp_riscv_adc_read_channel(ADC_UNIT_1, ADC_CHANNEL_1);
    
    if(var_toggle){
        ulp_riscv_gpio_output_enable(3);
        ulp_riscv_gpio_output_level(3, 1);
        ulp_riscv_gpio_output_level(3, 0);
    }

    var_counter += 1;

    return 0;
}
