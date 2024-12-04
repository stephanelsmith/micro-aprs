
from micropython import const

PTT = const(41)       # 0-> transmit mode
PD  = const(40)       # 0-> power down, 1-> enable

# the actual module implements open-drain logic, lilygo module uses logic level
#HL_POWER  = const(38) # open drain logic, 0->low power, open->high power
# in lilygo, this is the SA868_RF_PIN   
HL_POWER  = const(38) # 0->low power, 1->high power

TX  = const(48)       # radio tx, connect to esp32 rx
RX  = const(39)       # radio rx, connect to esp32 tx

AUDIO_MIC       = const(18)  # radio mic (ESP2SA868_MIC) (ESP2MIC)
AUDIO_SPEAKER   = const(1)   # audio/adc (SA8682ESP_AUDIO)

