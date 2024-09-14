
from .AXP2101 import AXP2101
from .AXP2101 import AXP2101_SLAVE_ADDRESS


async def start(i2c):
    pmu = AXP2101(i2c_bus = i2c, addr=AXP2101_SLAVE_ADDRESS)
    print('XPOWER CHIPID:{}'.format(hex(pmu.getChipID())))

    pmu.setVbusVoltageLimit(pmu.XPOWERS_AXP2101_VBUS_VOL_LIM_4V36)
    pmu.setVbusCurrentLimit(pmu.XPOWERS_AXP2101_VBUS_CUR_LIM_1500MA)
    pmu.setSysPowerDownVoltage(2600)

    pmu.disableBLDO1(); #Rev2.x Microphone LDO
    pmu.disableDC3();   #Rev2.0 SA8x8  DC boost , Rev2.1 user LDO
    pmu.disableBLDO2(); #Rev2.1 User LDO
    pmu.disableALDO2(); #Rev2.x SD Card LDO
    pmu.disableALDO3(); #Rev2.1 Audio amplification switch ， Rev2.0 user LDO
    pmu.disableALDO4(); #Rev2.x GPS LDO
    pmu.disableDLDO1(); #Rev2.1 Download switch enable

    # The following supply voltages can be controlled by the user
    pmu.disableALDO1();
    pmu.disableDC5();

    # The following power supplies are unavailable
    pmu.disableDC2();
    pmu.disableDC4();
    pmu.disableCPUSLDO();
    pmu.disableDLDO2();

    pmu.setALDO2Voltage(3300);
    pmu.setALDO3Voltage(3300);
    pmu.setBLDO2Voltage(3300);
    # There is no need to pmu.set the voltage because DLDO1 is just a switch and cannot adjust the voltage.
    # pmu.setDLDO1Voltage(3300); Invalid

    # External use
    pmu.setALDO1Voltage(3300);
    pmu.setDC5Voltage(3300);

    # radio
    pmu.setDC3Voltage(3400)
    pmu.enableDC3()
    pmu.getDC3Voltage()

    # voice vcc
    pmu.setBLDO1Voltage(3300)
    pmu.enableBLDO1()
    pmu.getBLDO1Voltage()

    # gnss 
    # pmu.setALDO4Voltage(3300);
    # pmu.enableALDO4()

    return pmu
