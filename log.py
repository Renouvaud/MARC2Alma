# Copyright 2025 Renouvaud
# License GPL-3.0 or later (https://www.gnu.org/licenses/gpl-3.0)

""" Python libraries """
from operator import concat
from datetime import *
import os
import errno
import csv
import pandas as pd


# Headers of log files
list_log = {
        'log_bib' : ['PROCESS', 'SRU', 'NZ ID', 'IZ ID', "035 (Other System Number)", 'LOCAL FIELDS ADDED', 'XML CONTENT'],
        'log_bib_unimported' : ['PROCESS INTERRUPTION', 'REJECTION REASON', "035", 'NZ ID', 'IZ ID', "ERROR CODE", 'XML CONTENT'],
        'log_bib_match' : ['INST REQUEST', 'SRU', 'ERROR', 'NZ ID', 'IZ ID', "035 (Other System Number)", 'REPONSE CODE', 'XML CONTENT'],
        'log_holding' : ['NZ ID', 'IZ ID', 'HOLDING ID', "035 (Other System Number)", 'LOCATION', 'CALL NUMBER', 'NUMBER OF ITEMS', 'DELETE MESSAGE', 'XML CONTENT'],
        'log_holding_unimported' : ['REJECT REASON', 'NZ ID', 'IZ ID', 'HOLDING ID', "035 (Other System Number)", 'LOCATION', 'GENERIC CALL NUMBER', 'CALL NUMBER 1', 'CODE REQUETE', 'XML CONTENT'],
        'log_item' : ['BARCODE', 'NZ ID', 'IZ ID', 'HOLDING ID', '035 (Other System Number)', 'LOCATION', 'HOL CALL NUMBER', 'ITEM CALL NUMBER', 'XML CONTENT'],
        'log_item_unimported' : ['REJECT REASON', 'BARCODE', 'NZ ID', 'IZ ID', 'HOLDING ID', '035 (Other System Numbere)', 'ITEM LOCATION', 'GENERIC ITEM CALL NUMBER', 'ITEM CALL NUMBER', 'HOLDINGS LIST', 'REQUEST CODE', 'XML CONTENT'],
        'log_portfolio' : ['NZ ID', 'IZ ID', 'PORTFOLIO ID', '035 (Other System Number)', 'COLLECTION ID', 'URL', 'PORTFOLIOS LIST', 'XML CONTENT'],
        'log_portfolio_unimported' : ['REJECT REASON', 'NZ ID', 'IZ ID', 'PORTFOLIOS LIST', '035 (Other System Number)', 'COLLECTION ID', 'URL', 'REQUEST CODE', 'XML CONTENT']
}

# Timestamp used in log file names
log_time = datetime.now().strftime("%Y%m%d_%H%M%S")

def initiate_log(input_folder, input_file, inst, env):
    """
    Initialize log files for the current import.
    Creates one CSV log file for each log type defined in list_log.
    """
    log_files = {}
    for name, headers in list_log.items() :
        path = f"{input_folder}/{log_time}_{input_file}_{inst}_{env}/{name}.csv"
        save_log(path, headers)
        log_files[name] = path
    return log_files


def save_log(log_file,log_line):
    """
    Save a log entry into a CSV file.
    If the directory does not exist, it is created.
    """
    if not os.path.exists(os.path.dirname(log_file)):
        try:
            os.makedirs(os.path.dirname(log_file))

        # Handle potential race condition when creating the folder
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise

    # Open file in append mode and write line        
    with open(log_file, 'a', encoding="utf-8", newline='\n') as csvfile:
        csv_write = csv.writer(csvfile, delimiter='\t', quotechar='"')
        csv_write.writerow(log_line)


def rm_empty_file(log_files):
    """
    Remove empty log files (i.e. containing only headers).
    Returns the updated dictionary of log files.
    """
    files_to_remove = {}
    for name, log_path in log_files.items() :
        if os.path.isfile(log_path):
            nb_line = count_line(log_path)
            # If file has only 1 line (headers), remove it
            if nb_line == 1 :
                files_to_remove[name] = log_path
                os.remove(log_path)

    # Remove references from dictionary
    for key in files_to_remove.keys() :
        del log_files[key]

    return  log_files


def count_line(file) :
    """
    Count the number of lines in a file.
    Creates the directory if it does not exist (edge case).
    """
    if not os.path.exists(os.path.dirname(file)):
        try:
            os.makedirs(os.path.dirname(file))

        # guard against race condition
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
            
    with open(file, 'r', encoding="utf-8") as log:
        for count, line in enumerate(log):
            pass
    return count + 1


def convert_log_excel(log_files):
    """
    Convert all log CSV files into a single Excel file with multiple sheets.
    Each log type is stored in a separate sheet.
    """
    # Extract base directory for Excel output
    file_dir = os.path.dirname(next(iter(log_files.values())))
    excel_path = concat(file_dir, "_import.xlsx")
    
    # Write Excel file (overwrite if exists)
    with pd.ExcelWriter(excel_path, mode='w') as writer:
        for name, l_path in log_files.items():
            # Read log file into DataFrame (all columns as strings)
            excel_log = pd.read_csv(l_path, sep='\t', dtype=pd.StringDtype()) # dtype=pd.StringDtype() => str format for columns !
            # Export DataFrame to Excel, one sheet per log type
            excel_log.to_excel(writer, sheet_name=name, index=False, header=True)

            # Auto-adjust column widths based on max content length
            worksheet = writer.sheets[name] 
            for idx, col in enumerate(excel_log):  
                series = excel_log[col]
                max_len = max((
                    series.astype(str).map(len).max(),  # length of largest cell
                    len(str(series.name))               # length of column header
                    )) + 1  # add a little extra space
                worksheet.set_column(idx, idx, max_len)
