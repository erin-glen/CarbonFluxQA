import os
import arcpy
import pandas as pd

TCD_THRESHOLD = 30
GAIN_FLAG = True
MASK_PATHS = {"IDN": "00N_110E", "GMB": "20N_20W"}


def get_tile_id(raster_name):
    return raster_name.split("_", 3)[3]


def get_mask_tiles(tile_id):
    if "00N_110E" in tile_id:
        return os.path.join(arcpy.env.workspace, "Mask", "Mask", "00N_110E")
    else:
        return os.path.join(arcpy.env.workspace, "Mask", "Mask", "20N_20W")


def process_raster(raster, gain_tiles, mangrove_tiles, whrc_tiles, mask_tiles):
    tile_id = get_tile_id(os.path.splitext(os.path.basename(raster))[0])
    gain_raster_path = os.path.join(gain_tiles, f'{tile_id}_gain.tif')
    mangrove_raster_path = os.path.join(mangrove_tiles, f'{tile_id}_mangrove_agb_t_ha_2000_rewindow.tif')
    whrc_raster_path = os.path.join(whrc_tiles, f'{tile_id}_t_aboveground_biomass_ha_2000.tif')
    pre_2000_raster_path = os.path.join(whrc_tiles, f'{tile_id}_plantation_2000_reclass.tif')

    mask_path_tcd_gain = os.path.join(mask_tiles, f'{tile_id}_tcd_gain.tif')
    print(f'Creating masks for {tile_id}: \n')

    # alter these conditional statements to test different mask combinations. for example, comment out mangroves to
    # ignore mangroves
    tcd_raster = arcpy.sa.Con(arcpy.Raster(raster) > TCD_THRESHOLD, 1, 0)
    gain_raster = arcpy.sa.Con(arcpy.Raster(gain_raster_path) > 0, 1, 0)
    whrc_raster = arcpy.sa.Con(arcpy.Raster(whrc_raster_path) > 0, 1, 0)
    mangrove_raster = arcpy.sa.Con(arcpy.Raster(mangrove_raster_path) > 0, 1, 0)
    #check if pre_2000 raster exists and reclass
    #pre_2000_raster = arcpy.sa.Con(arcpy.Raster(pre_2000_raster_path) > 0, 1, 0)

    # step 1 multiply tcd and whrc raster (intersection of both rasters)
    output_raster = arcpy.sa.Times(tcd_raster, whrc_raster)
    # step 2 add the output to gain raster (union of outputs)
    output_raster = arcpy.sa.Plus(output_raster, gain_raster)
    # step 3 add the output to mangrove raster (union of outputs)
    #output_raster = arcpy.sa.Plus(output_raster, mangrove_raster)

    # step 4 (reclassify final mask raster to binary)
    output_raster = arcpy.sa.Con(output_raster > 0, 1, 0)

    output_raster.save(mask_path_tcd_gain)

def create_masks():
    mask_inputs = os.path.join(arcpy.env.workspace, "Mask", "Inputs")

    tcd_tiles = os.path.join(mask_inputs, "TCD")
    gain_tiles = os.path.join(mask_inputs, "Gain")
    whrc_tiles = os.path.join(mask_inputs, "WHRC")
    mangrove_tiles = os.path.join(mask_inputs, "Mangrove")

    tcd_list = [os.path.join(tcd_tiles, f) for f in os.listdir(tcd_tiles) if f.endswith('.tif')]
    print(tcd_list)

    for raster in tcd_list:
        tile_id = get_tile_id(os.path.splitext(os.path.basename(raster))[0])
        mask_tiles = get_mask_tiles(tile_id)
        process_raster(raster, gain_tiles, mangrove_tiles, whrc_tiles, mask_tiles)


def list_files_in_directory(directory, file_extension):
    return [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(file_extension)]


def process_zonal_statistics(aoi, raster_folder, output_folder):
    raster_list = list_files_in_directory(raster_folder, '.tif')

    for raster in raster_list:
        raster_name = os.path.splitext(os.path.basename(raster))[0]
        print(f'Calculating zonal statistics for {raster_name}: \n')

        output_name = f"{os.path.splitext(os.path.basename(aoi))[0]}_{raster_name}.dbf"
        output_path = os.path.join(output_folder, output_name)

        arcpy.gp.ZonalStatisticsAsTable_sa(aoi, "GID_0", raster, output_path, "DATA", "SUM")
        csv_file = f"{os.path.splitext(os.path.basename(aoi))[0]}_{raster_name}.csv"
        arcpy.TableToTable_conversion(output_path, output_folder, csv_file)


def zonal_stats(input_folder):
    aoi_list = list_files_in_directory(input_folder, '.shp')

    for aoi in aoi_list:
        aoi_name = os.path.splitext(os.path.basename(aoi))[0]
        print(f"Now processing {aoi_name}: \n")

        if "IDN" in aoi_name:
            raster_folder = os.path.join(arcpy.env.workspace, "Input", "00N_110E")
            output_folder = os.path.join(arcpy.env.workspace, "Outputs", "00N_110E")
        else:
            raster_folder = os.path.join(arcpy.env.workspace, "Input", "20N_20W")
            output_folder = os.path.join(arcpy.env.workspace, "Outputs", "20N_20W")

        process_zonal_statistics(aoi, raster_folder, output_folder)


def zonal_stats_masked(input_folder):
    # Define the dictionary for path assignments
    paths = {
        "IDN": {
            "raster_folder": os.path.join(arcpy.env.workspace, "Input", "00N_110E"),
            "output_folder": os.path.join(arcpy.env.workspace, "Outputs", "00N_110E"),
            "mask_tiles": os.path.join(arcpy.env.workspace, "Mask", "Mask", "00N_110E")
        },
        "GMB": {
            "raster_folder": os.path.join(arcpy.env.workspace, "Input", "20N_20W"),
            "output_folder": os.path.join(arcpy.env.workspace, "Outputs", "20N_20W"),
            "mask_tiles": os.path.join(arcpy.env.workspace, "Mask", "Mask", "20N_20W")
        }
    }

    aoi_list = list_files_in_directory(input_folder, '.shp')

    for aoi in aoi_list:
        aoi_name = os.path.splitext(os.path.basename(aoi))[0]
        print(f"Now processing {aoi_name}: \n")

        # Determine which set of paths to use
        path_key = "IDN" if "IDN" in aoi_name else "GMB"
        raster_folder = paths[path_key]["raster_folder"]
        output_folder = paths[path_key]["output_folder"]
        mask_tiles = paths[path_key]["mask_tiles"]

        raster_list = list_files_in_directory(raster_folder, '.tif')
        mask_list = list_files_in_directory(mask_tiles, '.tif')

        for raster in raster_list:
            raster_name = os.path.splitext(os.path.basename(raster))[0]

            for mask in mask_list:
                mask_name = os.path.splitext(os.path.basename(mask))[0].split("_", 2)[2]

                output_name = f"{aoi_name}_{raster_name}_{mask_name}.dbf"
                output_path = os.path.join(output_folder, output_name)

                masked_raster = arcpy.sa.Times(raster, mask)
                arcpy.gp.ZonalStatisticsAsTable_sa(aoi, "GID_0", masked_raster, output_path, "DATA", "SUM")

                csv_file = f"{aoi_name}_{raster_name}_{mask_name}.csv"
                arcpy.TableToTable_conversion(output_path, output_folder, csv_file)
                print(f"Exporting mask output {csv_file}")


def list_files_in_directory_annual(directory, file_keyword):
    """
    Lists all files in the given directory that contain the specified keyword in their name and end with .tif.
    """
    return [os.path.join(directory, file) for file in os.listdir(directory) if
            file_keyword in file and file.endswith('.tif')]


def process_annual_zonal_stats(aoi, raster_folder, output_folder):
    raster_list = list_files_in_directory_annual(raster_folder, 'emis')
    print(raster_list)

    for raster in raster_list:
        raster_name = os.path.splitext(os.path.basename(raster))[0]
        print(f'Calculating zonal statistics for {raster_name}: \n')

        output_name_dbf = f"{os.path.splitext(os.path.basename(aoi))[0]}_{raster_name}.dbf"
        output_name_csv = f"{os.path.splitext(os.path.basename(aoi))[0]}_{raster_name}.csv"

        output_path_dbf = os.path.join(output_folder, output_name_dbf)
        output_path_csv = os.path.join(output_folder, output_name_csv)

        try:
            arcpy.gp.ZonalStatisticsAsTable_sa(aoi, "Value", raster, output_path_dbf, "DATA", "SUM")
            arcpy.TableToTable_conversion(output_path_dbf, output_folder, output_name_csv)

            # Read the CSV file
            df = pd.read_csv(output_path_csv)

            # Rename 'Value' column to 'YEAR'
            df.rename(columns={'VALUE': 'YEAR'}, inplace=True)

            # Sort by 'YEAR' column in ascending order
            df_sorted = df.sort_values(by='YEAR', ascending=True)

            # Save the sorted data back to CSV
            df_sorted.to_csv(output_path_csv, index=False)

            print(f"Output saved and sorted as CSV: {output_path_csv}")
        except Exception as e:
            print(f"An error occurred: {e}")
            continue


def zonal_stats_annualized(input_folder):
    # Define the dictionary for path assignments
    paths = {
        "IDN": {
            "raster_folder": os.path.join(arcpy.env.workspace, "Input", "00N_110E")
        },
        "GMB": {
            "raster_folder": os.path.join(arcpy.env.workspace, "Input", "20N_20W")
        }
    }

    # Common output folder for both AOIs
    output_folder = os.path.join(arcpy.env.workspace, "Outputs", "Annual")

    # Ensure the output directory exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    aoi_list = list_files_in_directory(input_folder, 'clip.tif')
    print(aoi_list)

    for aoi in aoi_list:
        aoi_name = os.path.splitext(os.path.basename(aoi))[0]
        print(f"Now processing {aoi_name}: \n")

        # Determine which raster_folder to use
        path_key = "IDN" if "IDN" in aoi_name else "GMB"
        raster_folder = paths[path_key]["raster_folder"]
        print(raster_folder)

        process_annual_zonal_stats(aoi, raster_folder, output_folder)


def load_and_process_csv(file_path, file_name):
    csv_df = pd.read_csv(file_path)

    # Assigning attributes based on file name
    csv_df["Name"] = file_name
    csv_df[
        "Type"] = "gross emissions" if "emis" in file_name else "gross removals" if "removals" in file_name else "net flux"
    csv_df["Extent"] = "forest extent" if "forest" in file_name else "full extent"
    csv_df["Mask"] = "tcd and gain" if "tcd_gain" in file_name else "tcd" if "_tcd." in file_name else "no mask"

    # Dropping unnecessary columns
    csv_df.drop(['OID_', 'COUNT', 'AREA'], axis=1, inplace=True)
    return csv_df


def zonal_stats_clean(input_folders):
    df = pd.DataFrame()

    for folder in input_folders:
        for file in os.listdir(folder):
            print(file)
            if file.endswith(".csv"):
                file_path = os.path.join(folder, file)
                csv_df = load_and_process_csv(file_path, file)
                df = pd.concat([df, csv_df], axis=0)

    print(df)

    output_path = os.path.join(arcpy.env.workspace, "Outputs", "CSV", "output.csv")
    df.to_csv(output_path, index=False)

# todo check why we only have forest extent outputs for removals
