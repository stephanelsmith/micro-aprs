if(USER_C_MODULES)
    message(FATAL_ERROR "c_modules are built via c_modules/board.cmake; drop USER_C_MODULES from the build command")
endif()

# C modules as board sources of the main IDF component: compiled once, with IDF's full flags.
list(APPEND MICROPY_SOURCE_BOARD
    ${CMAKE_CURRENT_LIST_DIR}/chelloworld/helloworld.c
    ${CMAKE_CURRENT_LIST_DIR}/ccrc/ccrc.c
    ${CMAKE_CURRENT_LIST_DIR}/cdsp/cdsp.c
)
list(APPEND MICROPY_INC_USERMOD ${CMAKE_CURRENT_LIST_DIR}/cdsp)
