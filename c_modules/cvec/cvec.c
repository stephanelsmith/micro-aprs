// Include MicroPython API.
#include "py/runtime.h"

#include "py/objstr.h"
#include "py/objtuple.h"
#include "py/objlist.h"
#include "py/binary.h"
#include <string.h>
#include <stdlib.h>

#include "cvec.h"

// #include "extmod/moductypes.c" //why is there no .h file?
typedef struct _mp_obj_uctypes_struct_t {
    mp_obj_base_t base;
    mp_obj_t desc;
    byte *addr;
    uint32_t flags;
} mp_obj_uctypes_struct_t;

/////////////////////////
// from cvec import *
// cisqrt(100)
// cmag2(12,34)
// csign(-123)
// csign(123)

// SIGN
int32_t sign(int32_t v){
    return v>=0?1:-1;
}
static mp_obj_t mp_csign(mp_obj_t a_obj) {
    int a = mp_obj_get_int(a_obj);
	return mp_obj_new_int(sign(a));
}
static MP_DEFINE_CONST_FUN_OBJ_1(csign_obj, mp_csign);

// TO INT
static mp_obj_t mp_uint_to_int(mp_obj_t a_obj) {
    uint32_t a = mp_obj_get_int(a_obj);
    return mp_obj_new_int((int32_t)a);
}
static MP_DEFINE_CONST_FUN_OBJ_1(uint_to_int_obj, mp_uint_to_int);

// Reference for sqrt implementation
// https://stackoverflow.com/questions/65986056/is-there-a-non-looping-unsigned-32-bit-integer-square-root-function-c
////////////////////////////
// ISQRT (integer based sqrt)
////////////////////////////
static const uint8_t isqrt32_tab[192] = {
	127, 128, 129, 130, 131, 132, 133, 134, 135, 136,
	137, 138, 139, 140, 141, 142, 143, 143, 144, 145,
	146, 147, 148, 149, 150, 150, 151, 152, 153, 154,
	155, 155, 156, 157, 158, 159, 159, 160, 161, 162,
	163, 163, 164, 165, 166, 167, 167, 168, 169, 170,
	170, 171, 172, 173, 173, 174, 175, 175, 176, 177,
	178, 178, 179, 180, 181, 181, 182, 183, 183, 184,
	185, 185, 186, 187, 187, 188, 189, 189, 190, 191,
	191, 192, 193, 193, 194, 195, 195, 196, 197, 197,
	198, 199, 199, 200, 201, 201, 202, 203, 203, 204,
	204, 205, 206, 206, 207, 207, 208, 209, 209, 210,
	211, 211, 212, 212, 213, 214, 214, 215, 215, 216,
	217, 217, 218, 218, 219, 219, 220, 221, 221, 222,
	222, 223, 223, 224, 225, 225, 226, 226, 227, 227,
	228, 229, 229, 230, 230, 231, 231, 232, 232, 233,
	234, 234, 235, 235, 236, 236, 237, 237, 238, 238,
	239, 239, 240, 241, 241, 242, 242, 243, 243, 244,
	244, 245, 245, 246, 246, 247, 247, 248, 248, 249,
	249, 250, 250, 251, 251, 252, 252, 253, 253, 254,
	254, 255,
};
uint16_t isqrt32(uint32_t x){
    if (x == 0) return 0;
    int lz = clz32(x) & 30;
    x <<= lz;
    uint16_t y = 1 + isqrt32_tab[(x >> 24) - 64];
    y = (y << 7) + (x >> 9) / y;
    y -= x < (uint32_t)y * y;
    return y >> (lz >> 1);
}
static mp_obj_t mp_cisqrt(mp_obj_t a_obj) {
    int32_t a = mp_obj_get_int(a_obj);
	return mp_obj_new_int(isqrt32(a));
}
static MP_DEFINE_CONST_FUN_OBJ_1(cisqrt_obj, mp_cisqrt);


// MAG 2
uint16_t mag2(int32_t a, int32_t b){
    return isqrt32(a*a+b*b);
}
static mp_obj_t mp_cmag2(mp_obj_t a_obj, mp_obj_t b_obj) {
    int32_t a = mp_obj_get_int(a_obj);
    int32_t b = mp_obj_get_int(b_obj);
	return mp_obj_new_int(mag2(a, b));
}
static MP_DEFINE_CONST_FUN_OBJ_2(cmag2_obj, mp_cmag2);

// FIR CORE
// ARGS: coefs, buf, v, idx, scale
// OUT : tuple(idx, o)
static mp_obj_t mp_fir_core(size_t n_args, const mp_obj_t *args) {
    (void)n_args; // always 5 args: coefs, buf, v, idx, scale
    mp_obj_array_t *coefs_array = MP_OBJ_TO_PTR(args[0]);
    mp_obj_array_t *buf_array = MP_OBJ_TO_PTR(args[1]);
    int32_t v = mp_obj_get_int(args[2]);
    int32_t idx = mp_obj_get_int(args[3]);
    int64_t scale = mp_obj_get_int(args[4]);

    int32_t o = 0;
    int32_t *coefs = coefs_array->items;
    int32_t *buf = buf_array->items;
    int32_t ncoefs = coefs_array->len;

    buf[idx] = v;
    for(int32_t i=0; i<ncoefs; i++){
        int32_t buf_i = idx-i>=0 ? idx-i : ncoefs+idx-i; // emulate python mod for negative numbers
        // do 64bit operation to prevent overflow during accumulation
        o += ((int64_t)coefs[i] * (int64_t)buf[buf_i]) / (int64_t)scale;
    }
    idx = (idx+1)%ncoefs;

    mp_obj_t ret = mp_obj_new_tuple(2, NULL);
    mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(ret);
    tuple->items[0] = mp_obj_new_int(idx);
    tuple->items[1] = mp_obj_new_int(o);
    return ret;
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(fir_core_obj, 5, 5, mp_fir_core);


// Define all properties of the module.
// Table entries are key/value pairs of the attribute name (a string)
// and the MicroPython object reference.
// All identifiers and strings are written as MP_QSTR_xxx and will be
// optimized to word-sized integers by the build system (interned strings).
static const mp_rom_map_elem_t example_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_cvec) },
    { MP_ROM_QSTR(MP_QSTR_cisqrt), MP_ROM_PTR(&cisqrt_obj) },
    { MP_ROM_QSTR(MP_QSTR_cmag2), MP_ROM_PTR(&cmag2_obj) },
    { MP_ROM_QSTR(MP_QSTR_csign), MP_ROM_PTR(&csign_obj) },
    { MP_ROM_QSTR(MP_QSTR_uint_to_int), MP_ROM_PTR(&uint_to_int_obj) },
    { MP_ROM_QSTR(MP_QSTR_fir_core), MP_ROM_PTR(&fir_core_obj) },
};
static MP_DEFINE_CONST_DICT(example_module_globals, example_module_globals_table);

// Define module object.
const mp_obj_module_t cmodule_cvec = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&example_module_globals,
};

// Register the module to make it available in Python.
MP_REGISTER_MODULE(MP_QSTR_cvec, cmodule_cvec);

