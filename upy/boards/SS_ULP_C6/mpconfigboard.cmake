set(IDF_TARGET esp32c6)

set(SDKCONFIG_DEFAULTS
    boards/sdkconfig.base
    boards/sdkconfig.c6
    boards/sdkconfig.ble
)

#set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)
set(ulp_embedded_sources ${MICROPY_BOARD_DIR}/ulp/main.c)

# C modules (board dir is symlinked into the port, so resolve the real path)
get_filename_component(_BOARD_REAL "${MICROPY_BOARD_DIR}" REALPATH)
include(${_BOARD_REAL}/../../c_modules/board.cmake)
