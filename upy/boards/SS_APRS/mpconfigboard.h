#define MICROPY_HW_BOARD_NAME               "SSAPRS"
#define MICROPY_HW_MCU_NAME                 "ESP32-S3-FN8"
#define MICROPY_PY_NETWORK_HOSTNAME_DEFAULT "SSAPRS"

// turn-off unused
// https://github.com/orgs/micropython/discussions/14473
#define MICROPY_HW_ENABLE_SDCARD            (0)
#define MICROPY_PY_MACHINE_DAC              (0)
#define MICROPY_PY_ESPNOW                   (0)
#define MICROPY_PY_NETWORK_LAN              (0)
//#define MICROPY_PY_WEBREPL                  (0)
#define MICROPY_ENABLE_COMPILER (1)

// enable encryption
#define MICROPY_PY_SSL (1)
#define MICROPY_SSL_MBEDTLS (1)
#define MICROPY_PY_CRYPTOLIB (1)
#define MICROPY_PY_HASHLIB (1)

