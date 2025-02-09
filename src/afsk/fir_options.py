
# germany tuned
# options = dict({
    # 'bandpass_ncoefsbaud' : 3,
    # 'bandpass_width'      : 460,
    # 'bandpass_amark'      : 7,
    # 'bandpass_aspace'     : 24,
    # 'lpf_ncoefsbaud'      : 4,
    # 'lpf_f'               : 1000,
    # 'lpf_width'           : 360,
    # 'lpf_aboost'          : 3,
# }, **options)

# rtl_fm test tuning, working with ttwr
# options = dict({
    # 'bandpass_ncoefsbaud' : 5,
    # 'bandpass_width'      : 460,
    # 'bandpass_amark'      : 6,
    # 'bandpass_aspace'     : 6,
    # 'lpf_ncoefsbaud'      : 5,
    # 'lpf_f'               : 1000,
    # 'lpf_width'           : 360,
    # 'lpf_aboost'          : 3,
# }, **options)

# optimizer tuning for tnc test, 1020 decoded frames (but NOT ttwr!)
# options = dict({
    # 'bandpass_ncoefsbaud' : 5,
    # 'bandpass_width'      : 400,
    # 'bandpass_amark'      : 1,
    # 'bandpass_aspace'     : 3,
    # 'lpf_ncoefsbaud'      : 5,
    # 'lpf_f'               : 800,
    # 'lpf_width'           : 250,
    # 'lpf_aboost'          : 3,
# }, **options)

# co-optimize ttwr and tnc test, this is decode ttwr and decode 983 tnc frames
fir_options = {
    'bandpass_ncoefsbaud' : 5,
    'bandpass_width'      : 400,
    'bandpass_amark'      : 2,
    'bandpass_aspace'     : 3,
    'lpf_ncoefsbaud'      : 5,
    'lpf_f'               : 800,
    'lpf_width'           : 250,
    'lpf_aboost'          : 3,
    'squelch'             : 300,
}
# bandpass_ncoefs 91

