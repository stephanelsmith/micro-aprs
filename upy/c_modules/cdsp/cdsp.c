// Include MicroPython API.
#include "py/runtime.h"

#include "py/objstr.h"
#include "py/objtuple.h"
#include "py/objlist.h"
#include "py/binary.h"
#include <string.h>
#include <stdlib.h>

#include "cdsp.h"

// #include "extmod/moductypes.c" //why is there no .h file?
typedef struct _mp_obj_uctypes_struct_t {
    mp_obj_base_t base;
    mp_obj_t desc;
    byte *addr;
    uint32_t flags;
} mp_obj_uctypes_struct_t;

/////////////////////////
// from cdsp import *
// isqrt(100)
// sign(-123)
// sign(123)

// SIGN
int32_t sign(int32_t v){
    return v>=0?1:-1;
}
static mp_obj_t mp_sign(mp_obj_t a_obj) {
    int a = mp_obj_get_int(a_obj);
	return mp_obj_new_int(sign(a));
}
static MP_DEFINE_CONST_FUN_OBJ_1(sign_obj, mp_sign);

// TO INT, perform a uint32 to int32 type cast
// we need this in viper modules since all arrays are always uint
static mp_obj_t mp_utoi32(mp_obj_t a_obj) {
    uint32_t a = mp_obj_get_int(a_obj);
    return mp_obj_new_int((int32_t)a);
}
static MP_DEFINE_CONST_FUN_OBJ_1(utoi32_obj, mp_utoi32);

// 2 BYTES (encoded as U16 or S16) to integer (unsigned shifted)
// struct.unpack('<h', b)[0]
// int.from_bytes(b, 'little', signed=True)
static mp_obj_t mp_bs16toi(mp_obj_t buf_obj) {
    mp_buffer_info_t bufinfo;
    mp_get_buffer(buf_obj, &bufinfo, MP_BUFFER_READ);
    int16_t *bufin = bufinfo.buf;
    return mp_obj_new_int(*bufin);
}
static MP_DEFINE_CONST_FUN_OBJ_1(bs16toi_obj, mp_bs16toi);

// struct.unpack('<H', a)[0] - 32768
// int.from_bytes(a,'little',signed=False) - 32768
static mp_obj_t mp_bu16toi(mp_obj_t buf_obj) {
    mp_buffer_info_t bufinfo;
    mp_get_buffer(buf_obj, &bufinfo, MP_BUFFER_READ);
    uint16_t *bufin = bufinfo.buf;
    return mp_obj_new_int((*bufin) - 32768);
}
static MP_DEFINE_CONST_FUN_OBJ_1(bu16toi_obj, mp_bu16toi);

// INT to BYTEARRAY(size=2)
// same as int(123).to_bytes(2, 'little')
static mp_obj_t mp_i16tobs(mp_obj_t a_obj) {
    uint32_t u32 = mp_obj_get_int(a_obj);
    uint16_t u16 = (uint16_t)u32;
    mp_obj_t mp_bufout = mp_obj_new_bytearray(sizeof(u16), &u16);
    return mp_bufout;
}
static MP_DEFINE_CONST_FUN_OBJ_1(i16tobs_obj, mp_i16tobs);

////////////////////////////
// CLZ (count leading zeros)
////////////////////////////
// count leading zeros of nonzero 32-bit unsigned integer
// for gcc, use builtin
// #define clz32 __builtin_clz
// alternative implementation
// static const uint8_t clz_tab[32] = 
// {
    // 31, 22, 30, 21, 18, 10, 29,  2, 20, 17, 15, 13, 9,  6, 28, 1,
    // 23, 19, 11,  3, 16, 14,  7, 24, 12,  4,  8, 25, 5, 26, 27, 0
// };
// uint8_t clz32 (uint32_t a)
// {
    // a |= a >> 16;
    // a |= a >> 8;
    // a |= a >> 4;
    // a |= a >> 2;
    // a |= a >> 1;
    // return clz_tab [0x07c4acdd * a >> 27];
// }

// static mp_obj_t mp_clz(mp_obj_t a_obj) {
    // int a = mp_obj_get_int(a_obj);
	// return mp_obj_new_int(clz32(a));
// }
// static MP_DEFINE_CONST_FUN_OBJ_1(clz_obj, mp_clz);



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
static mp_obj_t mp_isqrt(mp_obj_t a_obj) {
    int32_t a = mp_obj_get_int(a_obj);
	return mp_obj_new_int(isqrt32(a));
}
static MP_DEFINE_CONST_FUN_OBJ_1(isqrt_obj, mp_isqrt);


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
        int32_t k = idx-i>=0 ? idx-i : ncoefs+idx-i; // emulate python mod for negative numbers
        // do 64bit operation to prevent overflow during accumulation
        o += ((int64_t)coefs[i] * (int64_t)buf[k]) / (int64_t)scale;
    }
    return mp_obj_new_int(o);

    // PASSING A TUPLE IS SLOW, WE'LL CALC IDX IN PARENT
    // idx = (idx+1)%ncoefs;
    // mp_obj_t ret = mp_obj_new_tuple(2, NULL);
    // mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(ret);
    // tuple->items[0] = mp_obj_new_int(idx);
    // tuple->items[1] = mp_obj_new_int(o);
    // return ret;
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(fir_core_obj, 5, 5, mp_fir_core);

// POWER METER 
// ARGS:  buf, v, idx
// OUT : tuple(idx, o)
static mp_obj_t mp_power_meter_core(mp_obj_t buf_obj, mp_obj_t v_obj, mp_obj_t idx_obj) {
    mp_obj_array_t *buf_array = MP_OBJ_TO_PTR(buf_obj);
    int32_t v = mp_obj_get_int(v_obj);
    int32_t idx = mp_obj_get_int(idx_obj);

    int32_t a = 0;
    int32_t o = 0;
    int32_t siz = buf_array->len;
    int32_t *buf = buf_array->items;

    buf[idx] = v;

    // get dc point
    for(int32_t i=0; i<siz; i++){
        a += buf[i];
    }
    a /= siz;

    for(int32_t i=0; i<siz; i++){
        int32_t k = idx-i>=0 ? idx-i : siz+idx-i; // emulate python mod for negative numbers
        o += (buf[k]-a) * (buf[k]-a);
    }
    o = isqrt32(o);

    return mp_obj_new_int(o);

    // PASSING A TUPLE IS SLOW, WE'LL CALC IDX IN PARENT
    // idx = (idx+1)%siz;
    // mp_obj_t ret = mp_obj_new_tuple(2, NULL);
    // mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(ret);
    // tuple->items[0] = mp_obj_new_int(idx);
    // tuple->items[1] = mp_obj_new_int(o);
    // return ret;
}
static MP_DEFINE_CONST_FUN_OBJ_3(power_meter_core_obj, mp_power_meter_core);

/*// POWER METER */
/*// ARGS:  buf, siz, v, idx*/
/*// OUT : tuple(idx, o)*/
/*//static mp_obj_t mp_power_meter_core(mp_obj_t buf_obj, mp_obj_t siz_obj, mp_obj_t v_obj, mp_obj_t idx_obj) {*/
/*static mp_obj_t mp_power_meter_core(size_t n_args, const mp_obj_t *args) {*/
    /*[>mp_obj_array_t *buf_array = MP_OBJ_TO_PTR(buf_obj);<]*/
    /*[>int32_t v = mp_obj_get_int(v_obj);<]*/
    /*[>int32_t siz = mp_obj_get_int(siz_obj);<]*/
    /*[>int32_t idx = mp_obj_get_int(idx_obj);<]*/
    /*(void)n_args; // always 5 args: coefs, buf, v, idx, scale*/
    /*mp_obj_array_t *buf_array = MP_OBJ_TO_PTR(args[0]);*/
    /*int32_t siz = mp_obj_get_int(args[1]);*/
    /*int32_t v = mp_obj_get_int(args[2]);*/
    /*int32_t idx = mp_obj_get_int(args[3]);*/

    /*int32_t o = 0;*/
    /*int32_t bufsiz = buf_array->len;*/
    /*int32_t *buf = buf_array->items;*/

    /*buf[idx] = v;*/
      
    /*// get average*/
    /*int64_t avg = 0;*/
    /*for(int64_t i=0; i<bufsiz; i++){*/
        /*avg += buf[i];*/
    /*}*/
    /*avg /= bufsiz;*/
    /*avg = 0;*/
    /*//avg = 337;*/

    /*//*/
    /*for(int32_t i=0; i<siz; i++){*/
        /*int32_t k = idx-i>=0 ? idx-i : bufsiz+idx-i; // emulate python mod for negative numbers*/
        /*int64_t x = (int64_t)buf[k] - avg;*/
        /*o += x*x;*/
    /*}*/
    /*o = isqrt32(o);*/
    /*idx = (idx+1)%siz;*/

    /*mp_obj_t ret = mp_obj_new_tuple(2, NULL);*/
    /*mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(ret);*/
    /*tuple->items[0] = mp_obj_new_int(idx);*/
    /*tuple->items[1] = mp_obj_new_int(o);*/
    /*return ret;*/
/*}*/
/*[>static MP_DEFINE_CONST_FUN_OBJ_4(power_meter_core_obj, mp_power_meter_core);<]*/
/*MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(power_meter_core_obj, 4, 4, mp_power_meter_core);*/





// Define all properties of the module.
// Table entries are key/value pairs of the attribute name (a string)
// and the MicroPython object reference.
// All identifiers and strings are written as MP_QSTR_xxx and will be
// optimized to word-sized integers by the build system (interned strings).
static const mp_rom_map_elem_t example_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_cdsp) },
    { MP_ROM_QSTR(MP_QSTR_isqrt), MP_ROM_PTR(&isqrt_obj) },
    { MP_ROM_QSTR(MP_QSTR_sign), MP_ROM_PTR(&sign_obj) },
    { MP_ROM_QSTR(MP_QSTR_fir_core), MP_ROM_PTR(&fir_core_obj) },
    { MP_ROM_QSTR(MP_QSTR_power_meter_core), MP_ROM_PTR(&power_meter_core_obj) },
    { MP_ROM_QSTR(MP_QSTR_utoi32), MP_ROM_PTR(&utoi32_obj) },
    { MP_ROM_QSTR(MP_QSTR_bs16toi), MP_ROM_PTR(&bs16toi_obj) },
    { MP_ROM_QSTR(MP_QSTR_bu16toi), MP_ROM_PTR(&bu16toi_obj) },
    { MP_ROM_QSTR(MP_QSTR_i16tobs), MP_ROM_PTR(&i16tobs_obj) },
};
static MP_DEFINE_CONST_DICT(example_module_globals, example_module_globals_table);

// Define module object.
const mp_obj_module_t cmodule_cdsp = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&example_module_globals,
};

// Register the module to make it available in Python.
MP_REGISTER_MODULE(MP_QSTR_cdsp, cmodule_cdsp);

