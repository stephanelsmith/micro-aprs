
def aprs_gps_format(lat, lon, 
                    symbol1 = '/', # standard set
                    symbol2 = '>', # car
                    ):
    lat_deg = int(lat)*100
    lat_min = (abs(lat)%1)*60.0
    lat_dir = 'N' if lat_deg > 0 else 'S'
    lat = abs(lat_deg)+abs(lat_min)

    lon_deg = int(lon)*100
    lon_min = (abs(lon)%1)*60.0
    lon_dir = 'W' if lon_deg < 0 else 'E'
    lon = abs(lon_deg)+abs(lon_min)

    aprs_loc = '{:07.2f}{}{}{:08.2f}{}{}'.format(lat, lat_dir, 
                                                 symbol1, lon, lon_dir,
                                                 symbol2)
    return aprs_loc
