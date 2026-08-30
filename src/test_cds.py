import cdsapi
import logging
logging.basicConfig(level=logging.DEBUG)
client = cdsapi.Client(url='https://cds.climate.copernicus.eu/api', key='00000000-0000-0000-0000-000000000000')
try:
    client.retrieve('reanalysis-era5-single-levels', {'product_type': 'reanalysis'}, 'test.nc')
except Exception as e:
    print("Caught Exception:", e)
