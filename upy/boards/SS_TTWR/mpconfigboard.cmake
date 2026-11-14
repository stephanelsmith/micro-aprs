set(IDF_TARGET esp32s3)
set(SDKCONFIG_DEFAULTS
    boards/sdkconfig.base
    ${SDKCONFIG_IDF_VERSION_SPECIFIC}
    boards/sdkconfig.usb
    boards/sdkconfig.ble
    boards/sdkconfig.240mhz
    boards/sdkconfig.spiram_sx
    boards/SS_TTWR/sdkconfig.board
)

set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)

# C modules (board dir is symlinked into the port, so resolve the real path)
get_filename_component(_BOARD_REAL "${MICROPY_BOARD_DIR}" REALPATH)
include(${_BOARD_REAL}/../../c_modules/board.cmake)
