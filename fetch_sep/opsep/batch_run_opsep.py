from . import opsep
from ..json import ccmc_json_handler as ccmc_json
from ..json import keys
from ..utils import config as cfg
from importlib import reload
import matplotlib.pyplot as plt
import argparse
import csv
import datetime
import logging
import sys
import os
import asciitable

__version__ = "0.7"
__author__ = "Katie Whitman"
__maintainer__ = "Katie Whitman"
__email__ = "kathryn.whitman@nasa.gov"

#Changes in 0.2: Modified so that output list files will indicate
#   when an observation or flux did not exceed a certain threshold
#   for a given SEP event. Added a column specifying SEP date to
#    sep_list
#2021-01-14, Changes in 0.3: Made consistent with operational_sep_quantities.py
#   v2.3 which includes background subtraction and various energy bin options.
#   Added more fields to list file to allow better specification of each data
#   set.
#2021-02-24, Changes in 0.4: Read in json files produced by
#   operational_sep_quantities.py and then write certain quantities to list.
#2021-04-05, Changes in 0.4.1: Reads pathnames from config.py.
#   Added checking for listpath. Code will check for listpath and create.
#2021-05-17, changes in 0.5: Discovered differences in CCMC's json files.
#   Making changes here to be consistent with their format. CCMC defines
#   "fluences" and "event_lengths" as arrays.
#2021-08-17, changes in 0.6: Making modifications to reflect changes in
#   operational_sep_quantities.py v3.0 w.r.t. inputs and outputs.
#   run_multi_sep.py now works with keys.py and ccmc_json_handler.py to
#   read in values from the json file and write out to list.
#2021-09-16, changes in 0.7: Add support for the JSONType (json_type)
#   variable added in operational_sep_quantities.py v3.2.


datapath = cfg.datapath
outpath = cfg.outpath + "/opsep"
listpath = cfg.listpath + "/opsep"

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('opsep')
logging.getLogger("matplotlib").setLevel(logging.WARNING)


def about_batch_run_opsep():
    """This and supporting codes are found in the respository:
            https://github.com/ktindiana/fetch-sep

        This code will run opsep.py for multiple SEP events.

        The input list file specifying which time periods must follow the format
        below. The SEP dates will be read in from a csv file with the columns:
        
            :Start Date: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS
            :End Date: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS
            :Experiment: GOES-08 up to GOES-15, EPHIN, SEPEM, SEPEMv3, user
            :Flux Type: differential or integral
            :Flags: Options are blank, TwoPeak, DetectPreviousEvent, and/ or SubtractBG separated by semi-colons, e.g. TwoPeak;SubtractBG
            :Model Name: blank if not a model
            :User Filename: name of file containing SEP time profile that user wants to input
            :options: may be "S14;Bruno2017;uncorrected"
            :Background Start Date: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS (if subtracting a BG)
            :Background End Date: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS
        
        COLUMN ENTRIES FOR OBSERVATIONS:
        
        StartDate, Enddate, Experiment, FluxType, Flags,,,options, bgstartdate, bgenddate
        
        COLUMN ENTRIES FOR 'user' FILE:
        
        StartDate, Enddate, Experiment, FluxType, Flags, Model Name, User Filename, options, bgstartdate, bgenddate

      
        OUTPUT FILES INCLUDE:
        
            * All of the output files generated by operational_sep_quantities.py
        
            * An aggregated list of information for all of the SEP events for each of the thresholds containing:
        
                * Start Time,End Time,Onset Peak Flux,Onset Peak Time,Max Flux, Max Flux Time,Fluence
        
            * If UMASEP, then the additional columns:
        
                * Ts + 3hr, Ts + 4hr, Ts + 5hr, Ts + 6hr, Ts + 7hr
                
    """


def check_list_path():
    """Check if the path listpath (in opsep/config.py) exists"""
    if not os.path.isdir(listpath):
        print('check_paths: Directory containing lists, ' + listpath +
        ', does not exist. Creating.')
        os.mkdir(listpath);



def read_sep_dates(sep_filename):
    ''' Reads in a csv list file of SEP events. List must have the format:
        
        StartDate, Enddate, Experiment, FluxType, Flags,,,options,bgstartdate,
            bgenddate
        
        If the experiment is 'user', indicating a user-input flux file, then
        the file must have the format:
        
        StartDate, Enddate, Experiment, FluxType, Flags, Model Name,
            User Filename, options, bgstartdate, bgenddate, JSON type

        Flags may be: TwoPeak, DetectPreviousEvent, SubtractBG
        
        options may be: "S14,Bruno2017,uncorrected"
        
        JSON type may be: model or observations
        
        Each column is returned as an array.
        
        INPUTS:
        
        :sep_filename: (string) name of file containing the list of
            experiments and time periods to run
        
        OUTPUTS:
        
        :start_dates: (datetime 1xn array)
        :end_dates: (datetime 1xn array)
        :experiments: (string 1xn array)
        :flux_types: (string 1xn array)
        :flags: (string 1xn array)
        :model_names: (string 1xn array)
        :user_files: (string 1xn array)
        :json_types: (string 1xn array)
        :options: (string 1xn array)
        :bgstartdate: (datetime 1xn array)
        :bgenddate: (datetime 1xn array)
        
    '''
    print('Reading in file ' + sep_filename)
    start_dates = [] #row 0
    end_dates = []
    experiments = [] #row 1, e.g. GOES-11, GOES-13, GOES-15, SEPEM, user
    flux_types = [] #row 3
    flags = [] #row 4
    model_names = [] #row 5
    user_files = [] #row 6
    options = [] #row 7
    bgstartdate = [] #row 8
    bgenddate = [] #row 9
    json_types = [] #row 10 (if user experiment)

    with open(sep_filename) as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',')
        #Define arrays that hold dates
        for row in readCSV:

            chk = row[0].lstrip()
            if '#' in row[0]: continue #skip if header row
            
            if len(row[0]) > 10:
                stdate = datetime.datetime.strptime(row[0][0:19],
                                            "%Y-%m-%d %H:%M:%S")
            if len(row[0]) == 10:
                stdate = datetime.datetime.strptime(row[0][0:10],
                                            "%Y-%m-%d")
            if len(row[1]) > 10:
                enddate = datetime.datetime.strptime(row[1][0:19],
                                            "%Y-%m-%d %H:%M:%S")
            if len(row[1]) == 10:
                enddate = datetime.datetime.strptime(row[1][0:10],
                                            "%Y-%m-%d")
            start_dates.append(str(stdate))
            end_dates.append(str(enddate))
            experiments.append(row[2])
            flux_types.append(row[3])

            if len(row) > 4:
                flags.append(row[4])
            else:
                flags.append('')

            if len(row) > 5:
                model_names.append(row[5])
            else:
                model_names.append('')

            if len(row) > 6:
                user_files.append(row[6])
            else:
                user_files.append('')

            if len(row) > 7:
                options.append(row[7])
            else:
                options.append('')

            if len(row) > 8:
                bgstartdate.append(row[8])
            else:
                bgstartdate.append('')

            if len(row) > 9:
                bgenddate.append(row[9])
            else:
                bgenddate.append('')
            
            if len(row) > 10:
                json_types.append(row[10])
            else:
                json_types.append('')


            if row[1] == 'user':
                if len(row) < 7:
                    sys.exit("For a user file, you must specify model name and "
                            "input filename in the list.")


    return start_dates, end_dates, experiments, flux_types, flags,\
        model_names, user_files, json_types, options, bgstartdate,\
        bgenddate



def initialize_files(jsonfname):
    ''' Create and initialize the output files that will contain
        the sep quantities. One output file for each unique energy
        channel and threshold combination.
        
        Create file and add header.
        
        INPUTS:
        
        :jsonfname: (string) name of json file
        
        OUTPUT:
        
        :combos: (array of dictionaries)
        
        combos contains all the unique energy and threshold combinations
        identified in all the different possible values in the json file.
        combos = [{'energy_channel': {'min': min, 'max': max},'threshold': thresh},
          {'energy_channel': {'min': min, 'max': max},'threshold': thresh},
          ...]
        
    '''
    data = ccmc_json.read_in_json(jsonfname)
    
    #Identify number of blocks in the json file
    nblocks = ccmc_json.return_nforecasts(data)
    
    #IDs for values within the blocks that are stored in arrays
    array_ids = [keys.id_event_lengths,
                 keys.id_fluence_spectra,
                 keys.id_threshold_crossings,
                 keys.id_probabilities]
    #matching identifiers for the associated threshold fields
    thresh_ids = [keys.id_event_length_threshold,
                  keys.id_fluence_spectrum_threshold_start,
                  keys.id_crossing_threshold,
                  keys.id_prob_threshold]
                  
    
    #Identify the unique energy channel and threshold combinations
    combos = []
    #search each energy block
    for i in range(nblocks):
        #search each entry that is an array that may contain
        #info for multiple thresholds
        energy_channel = ccmc_json.return_json_value_by_index(data,\
                        keys.id_energy_channel,i)
        for j in range(len(array_ids)):
            #pull out entry that is an array
            sub_dict = ccmc_json.return_json_value_by_index(\
                        data,array_ids[j],i)
            for k in range(len(sub_dict)):
                thresh = ccmc_json.return_json_value_by_index(\
                        data,thresh_ids[j],i,k)
                if thresh != cfg.errval:
                    combo = {'energy_channel': energy_channel,
                        'threshold': thresh}
                    if combo not in combos:
                        combos.append(combo)
    
    #combos should now contain all possible energy channel and
    #threshold combinations
    nthresh = len(combos)
    for i in range(nthresh):
        energy_min = combos[i]['energy_channel']['min']
        energy_max = combos[i]['energy_channel']['max']
        thresh = combos[i]['threshold']
        
        #Create an output file to contain list of calculated
        #quantities for all SEPs in input list
        #NOTE WILL WRITE OVER LIST FROM PREVIOUS RUNS UNLESS RENAMED
        if energy_max == -1:  #integral channel
            threshfile = listpath + '/' +'sep_list_' + str(energy_min) + 'MeV_' \
                    + str(thresh) + 'pfu.csv'
            bin_def = '>'+str(energy_min) + ' MeV [cm-2 sr-1]'
        else:
            threshfile = listpath + '/' +'sep_list_' + str(energy_min) +'-'\
                    + str(energy_max) + 'MeV_' + str(thresh) + 'dpfu.csv'
            bin_def = str(energy_min) + '-' + str(energy_max) + ' MeV [MeV-1 cm-2 sr-1]'
        
        fin = open(threshfile,'w+')
        fin.write('#Experiment,SEP Date,Start Time,End Time,Onset Peak Flux,'
                    'Onset Peak Time,Max Flux,Max Flux Time,Channel Fluence '+bin_def)
        fin.write('\n')
        fin.close()
        print('Created file ' + threshfile)
    
    return combos


def write_sep_lists(jsonfname, combos):
    ''' Reads in sep_values_*.json files output by operational_sep_quantities.
        Selected information is taken and sorted into lists for each threshold
        definition. Output is then an SEP list with associated quantities for
        each threshold.
        
        In the output list file, None, null, or global_var.py errval variable
        (currently "Value Not Found") indicate that the model
        or observations did not cross threshold.
        
        combos = [{'energy_channel': {'min': min, 'max': max},'threshold': thresh},
                  {'energy_channel': {'min': min, 'max': max},'threshold': thresh},
                  ...]
                  
        INPUTS:
        
        :jsonfname: (string) name of the json file
        :combos: (array of dictionaries) all of the different energy channel
            and threshold combinations in the json file
            
        OUTPUTS:
        
        :Boolean: True if values successfully written to file
        
    '''
    
    data = ccmc_json.read_in_json(jsonfname)
    exp_name = ccmc_json.return_json_value_by_index(data,keys.id_short_name)
    options = ccmc_json.return_json_value_by_index(data,keys.id_options)
    if isinstance(options,list):
        options = sorted(options)
        for opt in options:
            if opt.lstrip().strip() == "": continue
            exp_name = exp_name + "_" + opt.lstrip().strip()
    
    #Identify number of blocks in the json file
    nblocks = ccmc_json.return_nforecasts(data)
    for i in range(nblocks):
        energy_min = ccmc_json.return_json_value_by_index(data,\
                        keys.id_energy_min,i)
        energy_max = ccmc_json.return_json_value_by_index(data,\
                        keys.id_energy_max,i)
        energy_channel = ccmc_json.return_json_value_by_index(data,\
                        keys.id_energy_channel,i)
        for j in range(len(combos)):
            if combos[j]['energy_channel'] != energy_channel:
                continue
            thresh = combos[j]['threshold']
        
            #OPEN OR CREATE FILES THAT COMPILE INFO FOR ALL EVENTS
            #RUN WITH run_multi_sep
            #NOTE WILL WRITE OVER LIST FROM PREVIOUS RUNS UNLESS RENAMED
            if energy_max == -1:  #integral channel
                threshfile = listpath + '/' +'sep_list_' + str(energy_min) + 'MeV_' \
                        + str(thresh) + 'pfu.csv'
            else:
                threshfile = listpath + '/' +'sep_list_' + str(energy_min) +'-'\
                        + str(energy_max) + 'MeV_' + str(thresh) + 'dpfu.csv'
            
            isgood = os.path.isfile(threshfile)
            if not isgood:
                #In case a new threshold is encoutered
                bin_def = '>'+str(energy_min) + ' MeV [cm-2 sr-1]'
                if energy_max != -1:
                    bin_def = str(energy_min) + '-' + str(energy_max) + ' MeV [MeV-1 cm-2 sr-1]'
                fin = open(threshfile,'w+')
                fin.write('#Experiment,SEP Date,Start Time,End Time,'
                        'Onset Peak Flux,Onset Peak Time,Max Flux,'
                        'Max Flux Time,Channel Fluence ' + bin_def)
                fin.write('\n')
                fin.close()
                print('Creating file ' + threshfile)

            #Pick out columns to extract and save to SEP list
            #start time, onset peak, onset time, peak flux, peak time, end time, fluence
            #If UMASEP, then all delayed proton values <---NEED TO EDIT TO INCLUDE IN OUTPUT
            
            ###EXTRACT THE QUANTITIES FOR THIS ENERGY CHANNEL AND THRESHOLD
            #DEFINITION
            start_time = ccmc_json.return_json_value_by_threshold(
                        data,keys.id_event_length_start_time,
                        energy_channel, thresh)
            
            if start_time == '' or start_time == None \
                or start_time == cfg.errval: #NO SEP EVENT FOR THRESHOLD
                continue
            sep_year = start_time.year
            sep_month = start_time.month
            sep_day = start_time.day
            
            end_time = ccmc_json.return_json_value_by_threshold(
                        data,keys.id_event_length_end_time,
                        energy_channel, thresh)
             
            onset_peak = ccmc_json.return_json_value_by_threshold(
                        data,keys.id_peak_intensity,
                        energy_channel, thresh)
            
            onset_peak_time = ccmc_json.return_json_value_by_threshold(
                        data,keys.id_peak_intensity_time,
                        energy_channel, thresh)
            
            max_flux = ccmc_json.return_json_value_by_threshold(
                        data,keys.id_peak_intensity_max,
                        energy_channel, thresh)
                        
            max_flux_time = ccmc_json.return_json_value_by_threshold(
                        data,keys.id_peak_intensity_max_time,
                        energy_channel, thresh)
            
            fluence = ccmc_json.return_json_value_by_threshold(
                        data,keys.id_fluence,
                        energy_channel, thresh)
            
            #WRITE QUANTITIES TO FILE
            fin = open(threshfile,'a')
            fin.write(exp_name + ',')
            date = '{0:d}-{1:02d}-{2:02d}'.format(sep_year, sep_month,sep_day)
            fin.write(date + ',')
            fin.write(str(start_time) + ',')
            fin.write(str(end_time) + ',')
            fin.write(str(onset_peak) + ',')
            fin.write(str(onset_peak_time) + ',')
            fin.write(str(max_flux) + ',')
            fin.write(str(max_flux_time) + ',')
            fin.write(str(fluence))
            #Add code to include UMASEP cols when get chance (those values
            #need to be added to JSON file first)
            fin.write('\n')
            fin.close()

    return True


#def run_all_events(sep_filename, outfname, threshold, umasep):
#    """ Run all of the time periods and experiments in the list
#        file. Extract the values of interest and compile them
#        in event lists, one list per energy channel and threshold
#        combination.
#
#        INPUTS:
#
#        :sep_filename: (string) file containing list of events
#            and experiments to run
#        :outfname: (string) name of a file that will report any
#            errors encountered when running each event in the list
#        :threshold: (string) any additional thresholds to run
#            beyond >10 MeV, 10 pfu and >100 MeV, 1 pfu. Specify
#            in same way as called for by operational_sep_quantities.py
#        :umasep: (boolean) set to true to calculate values related to
#            the UMASEP model
#
#        OUTPUTS:
#
#        None except for:
#
#            * Output file listing each run and any errors encountered
#            * Output files containing event lists for each unique energy
#                channel and threshold combination
#
#    """
#
#    check_list_path()
#
#    #READ IN SEP DATES AND experiments
#    start_dates, end_dates, experiments, flux_types, flags, \
#        model_names, user_files, json_types, options, bgstart, \
#        bgend = read_sep_dates(sep_filename)
#
#    #Prepare output file listing events and flags
#    fout = open(outfname,"w+")
#    fout.write('#Experiment,SEP Date,Exception\n')
#
#    #---RUN ALL SEP EVENTS---
#    Nsep = len(start_dates)
#    combos = {}
#    print('Read in ' + str(Nsep) + ' SEP events.')
#    for i in range(Nsep):
#        start_date = start_dates[i]
#        end_date = end_dates[i]
#        experiment = experiments[i]
#        flux_type = flux_types[i]
#        flag = flags[i]
#        model_name = model_names[i]
#        user_file = user_files[i]
#        json_type = json_types[i]
#        option = options[i]
#        bgstartdate = bgstart[i]
#        bgenddate = bgend[i]
#
#        spase_id = ''
#
#        flag = flag.split(';')
#        detect_prev_event = detect_prev_event_default
#        two_peaks = two_peaks_default
#        doBGSub = False
#        nointerp = False #if true, will not do interpolation in time
#        if "DetectPreviousEvent" in flag:
#            detect_prev_event = True
#        if "TwoPeak" in flag:
#            two_peaks = True
#        if "SubtractBG" in flag:
#            doBGSub = True
#
#        print('\n-------RUNNING SEP ' + start_date + '---------')
#        #CALCULATE SEP INFO AND OUTPUT RESULTS TO FILE
#        try:
#            sep_year, sep_month, \
#            sep_day, jsonfname = opsep.run_all(start_date, end_date, experiment, flux_type, model_name, user_file, json_type,
#                spase_id, showplot, saveplot, detect_prev_event,
#                two_peaks, umasep, threshold, option, doBGSub,
#                bgstartdate, bgenddate, nointerp)
#
#            sep_date = datetime.datetime(year=sep_year, month=sep_month,
#                            day=sep_day)
#            if experiment == 'user' and model_name != '':
#                fout.write(model_name + ',')
#            if experiment != 'user':
#                fout.write(experiment + ',')
#            fout.write(str(sep_date) + ', ')
#            fout.write('Success\n')
#
#            #COMPILE QUANTITIES FROM ALL SEP EVENTS INTO A SINGLE
#            #LIST FOR EACH THRESHOLD
#            if not combos:
#                combos = initialize_files(jsonfname)
#            success=write_sep_lists(jsonfname,combos)
#            if not success:
#                print('Could not write values to file for ' + jsonfname)
#
#            plt.close('all')
#            opsep = reload(opsep)
#            cfg = reload(cfg)
#
#        except SystemExit as e:
#            # this log will include traceback
#            logger.exception('opsep failed with exception')
#            # this log will just include content in sys.exit
#            logger.error(str(e))
#            if experiment == 'user' and model_name != '':
#                fout.write(model_name + ',')
#            if experiment != 'user':
#                fout.write(experiment + ',')
#            fout.write(str(start_date) +',' + '\"' + str(e) + '\"' )
#            fout.write('\n')
#            opsep = reload(opsep)
#            cfg = reload(cfg)
#            continue
#
#    fout.close()
#
