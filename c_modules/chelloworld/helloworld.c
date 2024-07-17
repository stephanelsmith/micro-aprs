// Include MicroPython API.
#include "py/runtime.h"

#include "py/binary.h"
#include "py/objstr.h"
#include "py/objtuple.h"
#include <stdlib.h>

// #include "extmod/moductypes.c" //why is there no .h file?
typedef struct _mp_obj_uctypes_struct_t {
    mp_obj_base_t base;
    mp_obj_t desc;
    byte *addr;
    uint32_t flags;
} mp_obj_uctypes_struct_t;


// from chelloworld import *
//
// add_ints(1,2)
// create_bytearray(10)
// read_write_bytearray(a)
// modify_bytearray_inplace(a)
// modify_bytearray_inplace(a)
// print(test_tuple) #a constant
//
// from array import array
// a = array('i',[1,2,3])
// show_iterable(a)
// show_iterable([4,5,6])
// show_array(a)

// *************************************************
// This is the function which will be called from Python as cexample.add_ints(a, b).
static mp_obj_t mp_add_ints(mp_obj_t a_obj, mp_obj_t b_obj) {
// *************************************************
    // Extract the ints from the micropython input objects.
    int a = mp_obj_get_int(a_obj);
    int b = mp_obj_get_int(b_obj);

    // Calculate the addition and convert to MicroPython object.
    return mp_obj_new_int(a + b);
}
static MP_DEFINE_CONST_FUN_OBJ_2(add_ints_obj, mp_add_ints);


// return a tuple
static mp_obj_t mp_ret_tuple(mp_obj_t a_obj, mp_obj_t b_obj) {
    int a = mp_obj_get_int(a_obj);
    int b = mp_obj_get_int(b_obj);
    mp_obj_t ret = mp_obj_new_tuple(2, NULL);
    mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(ret);
    tuple->items[0] = mp_obj_new_int(a);
    tuple->items[1] = mp_obj_new_int(b);
    return ret;
}
static MP_DEFINE_CONST_FUN_OBJ_2(ret_tuple_obj, mp_ret_tuple);


// *************************************************
// TEST creating new bytearray
// *************************************************
static mp_obj_t create_bytearray(mp_obj_t a_obj) {
    int i;
    int a = mp_obj_get_int(a_obj);
    uint8_t *buff_out = malloc(a);
    for(i=0; i < a; i++){
        buff_out[i] = i%256;
    }
    mp_obj_t mp_buff_out = mp_obj_new_bytearray(a, buff_out);
    return mp_buff_out;
}
static MP_DEFINE_CONST_FUN_OBJ_1(create_bytearray_obj, create_bytearray);

// *************************************************
// TEST reading a bytearray/memoryview/bytes and output a new bytearray
// *************************************************
static mp_obj_t read_write_bytearray(mp_obj_t bufin_obj) {
	mp_buffer_info_t bufinfo;
	mp_get_buffer(bufin_obj, &bufinfo, MP_BUFFER_READ);
    uint8_t *bufin = bufinfo.buf;
    uint8_t i;
    mp_printf(MP_PYTHON_PRINTER, "reading input buffer, bufinfo.len = %u\n", (uint8_t)bufinfo.len);
    for(i=0; i < bufinfo.len; i++){
        // printf("%u %u %c\n", i, bufin[i], bufin[i]);
        mp_printf(MP_PYTHON_PRINTER, "%u %u %c\n", i, bufin[i], bufin[i]);
    }
    mp_printf(MP_PYTHON_PRINTER, "\n");
    mp_printf(MP_PYTHON_PRINTER, "writing output bytearray\n");
    uint8_t *bufout = malloc(bufinfo.len);
    for(i=0; i < bufinfo.len; i++){
        bufout[i] = bufin[i]+1;
        mp_printf(MP_PYTHON_PRINTER, "%u %u %c\n", i, bufout[i], bufout[i]);
    }
    mp_obj_t mp_bufout = mp_obj_new_bytearray(bufinfo.len, bufout);
    return mp_bufout;
}
// Define a Python reference to the function above.
static MP_DEFINE_CONST_FUN_OBJ_1(read_write_bytearray_obj, read_write_bytearray);

// *************************************************
// TEST modifying a bytearray IN PLACE
// *************************************************
static mp_obj_t modify_bytearray_inplace(mp_obj_t buf_obj) {
	mp_buffer_info_t bufinfo;
	mp_get_buffer(buf_obj, &bufinfo, MP_BUFFER_READ|MP_BUFFER_WRITE);
    uint8_t *bufin = bufinfo.buf;
    uint8_t i;
    mp_printf(MP_PYTHON_PRINTER, "reading input buffer, bufinfo.len = %u\n", (uint8_t)bufinfo.len);
    for(i=0; i < bufinfo.len; i++){
        bufin[i] += 1;
        mp_printf(MP_PYTHON_PRINTER, "%u %u %c\n", i, bufin[i], bufin[i]);
    }
    return buf_obj;
}
// Define a Python reference to the function above.
static MP_DEFINE_CONST_FUN_OBJ_1(modify_bytearray_inplace_obj, modify_bytearray_inplace);


// *************************************************
// Example for constants
// *************************************************
#define MAGIC_CONSTANT 42
static const MP_DEFINE_STR_OBJ(test_string_obj, "hello world");
const mp_rom_obj_tuple_t test_tuple_obj = {
    {&mp_type_tuple},
    2,
    {
        MP_ROM_INT(1),
        MP_ROM_PTR(&test_string_obj),
    },
};

// *************************************************
// work with iterable
// *************************************************
static mp_obj_t show_iterable(mp_obj_t a_obj) {
    mp_obj_iter_buf_t iter_buf;
    mp_obj_t item;
    mp_obj_t itr = mp_getiter(a_obj, &iter_buf);
    int32_t idx = 0;
    while ((item = mp_iternext(itr)) != MP_OBJ_STOP_ITERATION) {
        int v = mp_obj_get_int(item);
        mp_printf(MP_PYTHON_PRINTER, "[%u]: %u\n", idx, v);
        idx++;
    }
    return mp_obj_new_int(0);
}
static MP_DEFINE_CONST_FUN_OBJ_1(show_iterable_obj, show_iterable);

// *************************************************
// work with array
// *************************************************
static mp_obj_t show_array(mp_obj_t a_obj) {
    mp_obj_array_t *aptr = MP_OBJ_TO_PTR(a_obj);

    //type codes are just 'i', 'h', etc...
    mp_printf(MP_PYTHON_PRINTER, "typecode: %c\n", (char)aptr->typecode);
    mp_printf(MP_PYTHON_PRINTER, "size: %u\n", (uint16_t)aptr->len);

    //will only work on typecode 'i'!
    int32_t *items = aptr->items;
    for(uint32_t i=0; i<aptr->len; i++){
        int32_t v = items[i];
        mp_printf(MP_PYTHON_PRINTER, "[%u]: %d\n", (uint16_t)i, v);
    }
    
    //work on all numeric typecodes
    //we can also use mp_binary_get_val_array (py/binary.c) which typecasts and gets the index
    for(uint32_t i=0; i<aptr->len; i++){
        mp_obj_t t = mp_binary_get_val_array(aptr->typecode, aptr->items, i);
        int32_t v = mp_obj_get_int(t);
        mp_printf(MP_PYTHON_PRINTER, "[%u]: %d\n", (uint16_t)i, v);
    }
    return mp_obj_new_int(0);
}
static MP_DEFINE_CONST_FUN_OBJ_1(show_array_obj, show_array);

// *************************************************
// work with uctype struct mapping to c struct
// *************************************************
typedef struct _point {
    int32_t x;
    int32_t y;
    int32_t z;
} point_t;
typedef struct _points {
    point_t a[3];
} points_t;
static mp_obj_t test_struct(mp_obj_t a_obj) {
    mp_obj_uctypes_struct_t *aptr = MP_OBJ_TO_PTR(a_obj);

    mp_printf(MP_PYTHON_PRINTER, "addr: %d\n", aptr->addr);
    points_t* points;
    points = (points_t*)aptr->addr;
    for(int i=0; i<3; i++){
        mp_printf(MP_PYTHON_PRINTER, "pt[%d].x %d\n", i, points->a[i].x);
        mp_printf(MP_PYTHON_PRINTER, "pt[%d].y %d\n", i, points->a[i].y);
        mp_printf(MP_PYTHON_PRINTER, "pt[%d].z %d\n", i, points->a[i].z);
    }
    uint8_t* u;
    u = aptr->addr;
    for(int i=0; i<9; i++){
        mp_printf(MP_PYTHON_PRINTER, "%d %d\n", i, (int32_t)u[i]);
    }
    return mp_obj_new_int(0);
}
static MP_DEFINE_CONST_FUN_OBJ_1(test_struct_obj, test_struct);



// Define all properties of the module.
// Table entries are key/value pairs of the attribute name (a string)
// and the MicroPython object reference.
// All identifiers and strings are written as MP_QSTR_xxx and will be
// optimized to word-sized integers by the build system (interned strings).
static const mp_rom_map_elem_t example_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_chelloworld) },
    { MP_ROM_QSTR(MP_QSTR_add_ints), MP_ROM_PTR(&add_ints_obj) },
    { MP_ROM_QSTR(MP_QSTR_ret_tuple), MP_ROM_PTR(&ret_tuple_obj) },
    { MP_ROM_QSTR(MP_QSTR_test_str), MP_ROM_PTR(&test_string_obj) },
    { MP_ROM_QSTR(MP_QSTR_test_int), MP_ROM_INT(MAGIC_CONSTANT) },
    { MP_ROM_QSTR(MP_QSTR_test_tuple), MP_ROM_PTR(&test_tuple_obj) },
    { MP_ROM_QSTR(MP_QSTR_create_bytearray), MP_ROM_PTR(&create_bytearray_obj) },
    { MP_ROM_QSTR(MP_QSTR_read_write_bytearray), MP_ROM_PTR(&read_write_bytearray_obj) },
    { MP_ROM_QSTR(MP_QSTR_modify_bytearray_inplace), MP_ROM_PTR(&modify_bytearray_inplace_obj) },
    { MP_ROM_QSTR(MP_QSTR_show_iterable), MP_ROM_PTR(&show_iterable_obj) },
    { MP_ROM_QSTR(MP_QSTR_show_array), MP_ROM_PTR(&show_array_obj) },
    { MP_ROM_QSTR(MP_QSTR_test_struct), MP_ROM_PTR(&test_struct_obj) },
};
static MP_DEFINE_CONST_DICT(example_module_globals, example_module_globals_table);

// Define module object.
const mp_obj_module_t cmodule_chelloworld = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&example_module_globals,
};

// Register the module to make it available in Python.
MP_REGISTER_MODULE(MP_QSTR_chelloworld, cmodule_chelloworld);

