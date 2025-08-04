""" Local functions """
from general import *
""" Python libraries """
from locale import format_string
from operator import concat
from datetime import *
import os
import errno
import csv
import pandas as pd
from xlsxwriter import Workbook


#list of log files headers
list_log = {
        'log_bib' : ['PROCESSUS', 'SRU', 'NZ ID', 'IZ ID', "035 (ID du système d'origine)", 'CHAMPS AJOUTES', 'CONTENU XML'],
        'log_bib_unimported' : ['INTERRUPTION DU PROCESSUS', 'CAUSE DE REJET', "035 (ID du système d'origine)", 'NZ ID', 'IZ ID', "CODE D'ERREUR", 'CONTENU XML'],
        'log_bib_match' : ['INST REQUETE', 'SRU', 'ERREUR', 'NZ ID', 'IZ ID', "035 (ID du système d'origine)", 'CODE REPONSE', 'CONTENU XML'],
        'log_holding' : ['NZ ID', 'IZ ID', 'HOLDING ID', "035 (ID du système d'origine)", 'LOCALISATION', 'COTE', 'NOMBRE D\'EXEMPLAIRES', 'MESSAGE SUPPRESSION', 'CONTENU XML'],
        'log_holding_unimported' : ['CAUSE DE REJET', 'NZ ID', 'IZ ID', 'HOLDING ID', "035 (ID du système d'origine)", 'LOCALISATION', 'COTE GENERIQUE', 'COTE1', 'CODE REQUETE', 'CONTENU XML'],
        'log_item' : ['CODE-BARRE', 'NZ ID', 'IZ ID', 'HOLDING ID', '035 (ID du système d\'origine)', 'LOCALISATION', 'COTE HOL', 'COTE EXEMPLAIRE', 'CONTENU XML'],
        'log_item_unimported' : ['CAUSE DE REJET', 'CODE-BARRE', 'NZ ID', 'IZ ID', 'HOLDING ID', '035 (ID du système d\'origine)', 'LOCALISATION EXEMPLAIRE', 'COTE EXEMPLAIRE GENERIQUE', 'COTE EXEMPLAIRE', 'LISTE DES HOLDINGS', 'CODE REQUETE', 'CONTENU XML'],
        'log_portfolio' : ['NZ ID', 'IZ ID', 'PORTFOLIO ID', '035 (ID du système d\'origine)', 'COLLECTION ID', 'URL', 'LISTE DES PORTFOLIOS', 'CONTENU XML'],
        'log_portfolio_unimported' : ['CAUSE DE REJET', 'NZ ID', 'IZ ID', 'LISTE DES PORTFOLIOS', '035 (ID du système d\'origine)', 'COLLECTION ID', 'URL', 'CODE REQUETE', 'CONTENU XML']
}

log_time = datetime.now().strftime("%Y%m%d_%H%M%S")

def initiate_log(input_folder, input_file, inst, env):
    log_files = {}
    for name, headers in list_log.items() :
        path = f"{input_folder}/{log_time}_{input_file}_{inst}_{env}/{name}.csv"
        save_log(path, headers)
        log_files[name] = path
    return log_files


# save log in csv file
def save_log(log_file,log_line):

    # create directory if not exists
    if not os.path.exists(os.path.dirname(log_file)):
        try:
            os.makedirs(os.path.dirname(log_file))

        # guard against race condition
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
            
    with open(log_file, 'a', encoding="utf-8", newline='\n') as csvfile:
        csv_write = csv.writer(csvfile, delimiter='\t', quotechar='"')
        csv_write.writerow(log_line)


def rm_empty_file(log_files):
    files_to_remove = {}
    for name, log_path in log_files.items() :
        if os.path.isfile(log_path):
            nb_line = count_line(log_path)
            if nb_line == 1 :
                files_to_remove[name] = log_path
                os.remove(log_path)
                #print(f"{log_path} has been removed, count = {nb_line}")
    for key in files_to_remove.keys() :
        del log_files[key]
    #print(f"liste des fichiers de log : {log_files.keys()}")
    return  log_files


def count_line(file) :
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
    file_dir = os.path.dirname(next(iter(log_files.values()))) # extraire le chemin du nom de fichier
    excel_path = concat(file_dir, "_import.xlsx")
    
    with pd.ExcelWriter(excel_path, mode='w') as writer: # mode w pour crééer et modifier fichier
        for name, l_path in log_files.items():
            excel_log = pd.read_csv(l_path, sep='\t', dtype=pd.StringDtype()) # dtype=pd.StringDtype() => colonnes au format str !
            excel_log.to_excel(writer, sheet_name=name, index=False, header=True)
            worksheet = writer.sheets[name]  # pull worksheet object
            for idx, col in enumerate(excel_log):  # loop through all columns
                series = excel_log[col]
                max_len = max((
                    series.astype(str).map(len).max(),  # len of largest item
                    len(str(series.name))  # len of column name/header
                    )) + 1  # adding a little extra space
                worksheet.set_column(idx, idx, max_len)
