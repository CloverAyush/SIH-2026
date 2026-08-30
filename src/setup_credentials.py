import os
import sys
import getpass


def setup_credentials():
    print("=========================================")
    print("   OPENDRIFT CREDENTIAL SETUP WIZARD")
    print("=========================================")

    home_dir = os.path.expanduser('~')

    print("\n--- 1. Copernicus Marine (Ocean Currents) ---")
    cmems_user = os.getenv('COPERNICUSMARINE_SERVICE_USERNAME')
    cmems_pass = os.getenv('COPERNICUSMARINE_SERVICE_PASSWORD')

    if not cmems_user:
        cmems_user = input("Enter Copernicus Username: ").strip()
    if not cmems_pass:
        cmems_pass = getpass.getpass("Enter Copernicus Password: ").strip()

    os.environ['COPERNICUSMARINE_SERVICE_USERNAME'] = cmems_user
    os.environ['COPERNICUSMARINE_SERVICE_PASSWORD'] = cmems_pass

    netrc_path = os.path.join(home_dir, '_netrc')
    netrc_content = f"machine my.cmems-du.eu\nlogin {cmems_user}\npassword {cmems_pass}\n"

    with open(netrc_path, 'w') as f:
        f.write(netrc_content)
    print(f"[SUCCESS] Saved Copernicus credentials to: {netrc_path}")

    print("\n--- 2. ERA5 / Climate Data Store (Wind) ---")
    print("Go to https://cds.climate.copernicus.eu/user to find your UID and API Key.")
    cds_uid = os.getenv('CDSAPI_UID')
    cds_key = os.getenv('CDSAPI_KEY')

    if not cds_uid:
        cds_uid = input("Enter your ERA5 UID (e.g. 12345): ").strip()
    if not cds_key:
        cds_key = getpass.getpass("Enter your ERA5 API Key: ").strip()

    os.environ['CDSAPI_UID'] = cds_uid
    os.environ['CDSAPI_KEY'] = cds_key

    cdsapirc_path = os.path.join(home_dir, '.cdsapirc')
    cdsapirc_content = f"url: https://cds.climate.copernicus.eu/api/v2\nkey: {cds_uid}:{cds_key}\n"

    with open(cdsapirc_path, 'w') as f:
        f.write(cdsapirc_content)
    print(f"[SUCCESS] Saved ERA5 credentials to: {cdsapirc_path}")

    print("\n[ALL DONE] Your computer is now securely configured to stream physics data!")


if __name__ == "__main__":
    setup_credentials()
