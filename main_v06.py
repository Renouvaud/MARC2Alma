""" Local functions """
from cgi import test
from xmlrpc.client import Boolean, boolean
from api_keys import *
from general import *
from bib_record import *
from holding import *
from item import *
from call_api import *
from log import *

""" Python libraries """
#from operator import contains
#from pdb import line_prefix
from pickle import FALSE, TRUE
#from tkinter import Variable
from time import *
from datetime import *
import xml.etree.ElementTree as etree
import re # for regex
import io
from pymarc import *
from pymarc import exceptions as exc
import json
#from pathlib import Path
#import pdb; pdb.set_trace()


# Démarrage du calcul de la durée d'exécution du programme
start = datetime.now()
print(f"Start time : {start.strftime('%d-%m-%Y %H:%M:%S')}")


# Calls function main() """
if __name__ == "__main__":
    
    ############################### Read Me  ###############################
    # FIRST : copy general_params_default file and update informations     #
    # SECOND : check API_Keys file --> renamme API Key to use              #
    # THIRD : update here name of general params file                      #
    gen_param_file = "general_params_crissier"
    ########################################################################                   
    
    # Import params
    gen_param = read_json(f"./{gen_param_file}.json")

    # General params
    env = gen_param['env_param']['env']                                       
    inst = gen_param['inst_param']['inst']                            

    # Normalization rules to apply in Alma
    nz_rule = gen_param['rules_param'][f"nz_rule_{env}"]
    iz_rule = gen_param['rules_param'][f"iz_rule_{env}"]
    nz_rule_update = gen_param['rules_param'][f"nz_rule_{env}_update"]
    iz_rule_update = gen_param['rules_param'][f"iz_rule_{env}_update"]

    # Path of xml file to import
    input_file_folder = gen_param['file_param']['XMLfile_path']
    input_file_name = gen_param['file_param']['XMLfile_name']
    input_file_path = f"{input_file_folder}/{input_file_name}.xml"


    ### CHECK FILE DUPLICATE ###
    # check duplicate barcode
    emptybar = json.loads(gen_param['check_duplicates']['barcode_empty'].lower())
    test_bar = check_duplicate(input_file_path, './record/item_data/barcode', emptybar, 'barcode')
    emptymms = json.loads(gen_param['check_duplicates']['mmsid_empty'].lower())
    test_mmsid= check_duplicate(input_file_path, './record/mms_id', emptymms, 'mms_id')
    if gen_param['check_duplicates']['f035_empty'] != "None" :
        empty035 = json.loads(gen_param['check_duplicates']['f035_empty'].lower())
        test_035 = check_duplicate(input_file_path, './record/datafield[@tag="035"]/subfield[@code="a"]',
        empty035, 'subfield code="a"', 'subfield')
    
    #if (test_bar) :
    if gen_param['check_duplicates']['f035_empty'] != "None" :
        if test_bar or test_035 or test_mmsid :
        # exit programm if duplicates !!!
            exit()
    else :
         if test_bar or test_mmsid :
        # exit programm if duplicates !!!
            exit()       
    ############################    
  
    # define API key
    api_key_nz = get_apikey(f"api_key_nz_{env}")
    api_key_iz = get_apikey(f"api_key_{inst}_{env}")

    # initiate log files : #### OPTIMiZE
    log_files = initiate_log(input_file_folder, input_file_name, inst, env)
    log_bib = log_files['log_bib']
    log_bib_unimported = log_files['log_bib_unimported']
    log_bib_match = log_files['log_bib_match']
    log_holding = log_files['log_holding']
    log_holding_unimported = log_files['log_holding_unimported']
    log_item = log_files['log_item']
    log_item_unimported = log_files['log_item_unimported']
    log_portfolio = log_files['log_portfolio']
    log_portfolio_unimported = log_files['log_portfolio_unimported']


    ### HANDLE BIB RECORD ###
    # Split xml file in record : for each record call API
    for record in parse_xmlFile(input_file_path).findall("record"):
        # format xml record
        r_str = etree.tostring(record).decode()
        r_str = r_str.replace("\n", " ").replace("\t", " ") # voir si usage liste possible
        r_format = format_api(r_str, "bib")
        r_format = r_format.encode('UTF-8')
        el035 = find_etree(record, './datafield[@tag="035"]/subfield[@code="a"]')

        # initiate dictionnary for holding --> we don't want to import existing holding or twice same holding
        hol_alma_list = []
        hol_alma_list_id = []
        
        ## check if record in loaded file has holding and item or portfolio --> if not pass ##
        bib_unimport = bib_to_reject(record)
        if bib_unimport[0] :
            save_log(log_bib_unimported, [bib_unimport[1], '', el035, '', '', '', r_format])
            continue
    
        ## match with existing record ##
        xpath_id = gen_param['check_bib_match']['identifier']
        id_type = gen_param['check_bib_match']['id_type']
        multi_prefix = gen_param['check_bib_match']['multi_prefix'].split("|")

        # init dict keys : api_error, exist_nz, exist_iz, nz_id, iz_id, get_xml
        bib_match = {
            'exist_nz' : False,
            'exist_iz' : False,
            'api_error' : False,
            'nz_id' : "Empty",
            'iz_id' : "Empty",
            'get_record_xml' : "Empty"
        }
        bib_has_match(record, xpath_id, id_type, multi_prefix, el035, log_bib_match, api_key_nz, api_key_iz, bib_match)

        # pass record : we don't know if record exists or not 
        if bib_match['api_error'] :
            continue
        
        # sru search if no match and sru param of json file is set True 
        if not bib_match['exist_nz'] and gen_param['sru_search']['bool']=='True' :
            id_list = gen_param['sru_search']['identifier']
            bib_sru(record, id_list, el035, api_key_iz, log_bib_match, env, bib_match)

            # again pass if error
            if bib_match['api_error'] :
                continue            

        ## if exists nz : update bib nz ##
        process_list = {}
        if bib_match['exist_nz'] :
            nz_id = bib_match['nz_id']
            # use json file params to update r_get_str
            log_list = []
            r_alma = pymarc.parse_xml_to_array(io.StringIO(bib_match['get_record_xml']))[0]
            r_import = pymarc.parse_xml_to_array(io.StringIO(r_str))[0]
            for field, params in gen_param['fields_update'].items() :
                if field == '_comment' :
                    continue
                subfields = params['subfields']
                f_function = params['update_method']
                new_content = r_update_content(f_function, r_import, r_alma, field, subfields)
                r_alma = new_content[1]
                if new_content[0] != '':
                    log_list.append(new_content[0])
            log_update_f = " | ".join(log_list)                       
            r_get_str = record_to_xml(r_alma).decode()
            # according to the GET call, the following line is retrieved from the xml --> consequence: 035 is overwritten, so delete line !!!
            string_to_remove = '<datafield ind1=" " ind2=" " tag="035"><subfield code="a">(EXLNZ-41BCULAUSA_NETWORK)'+ nz_id +'</subfield></datafield>'
            r_get_str = r_get_str.replace(string_to_remove, "")
            r_get_format = format_api(r_get_str, "bib")
            r_get_format = r_get_format.encode('UTF-8')
            # update bib nz
            update_nz_record = update_bib(api_key_nz, r_get_format, nz_id, rule = nz_rule_update)
            if update_nz_record[2] != 200 :
                process_list['raccrochage nz'] = 'error'
                save_log(log_bib_unimported, [process_list, update_nz_record[0], el035, nz_id, bib_match['iz_id'], update_nz_record[2], update_nz_record[3]])
                continue
            process_list['raccrochage nz'] = 'done'

            ## if exists iz : update bib iz ##
            if bib_match['exist_iz'] :
                iz_id = bib_match['iz_id']
                update_iz_record = update_bib(api_key_iz, r_get_format, iz_id, rule = iz_rule_update)
                ## import pdb; pdb.set_trace()
                if update_iz_record[2] == 200 :
                    process_list['raccrochage iz'] = 'done'
                    save_log(log_bib, [process_list, nz_id, iz_id, el035, log_update_f, update_iz_record[3]])
                else :
                    process_list['raccrochage iz'] = 'error'
                    save_log(log_bib_unimported, [process_list, update_iz_record[0], el035, nz_id, iz_id, update_iz_record[2], update_iz_record[3]])
                    continue
                
                # check if bib has holdings
                get_hol_list = get_holdings(api_key_iz, iz_id)
                if get_hol_list[2] != 200 :
                    save_log(log_holding_unimported, [f"recherche holdings : {get_hol_list[0]}", nz_id, iz_id, '', el035, '', '', '', get_hol_list[2], get_hol_list[3]])
                    continue
                if get_hol_list[1] != "0" :
                    holdings_alma = etree.fromstring(get_hol_list[3], parser=etree.XMLParser(encoding="utf-8"))
                    library = gen_param['code_bib_alma']
                    for hol in holdings_alma.findall("holding"):
                        hol_lib = hol.find("./library").text
                        if hol_lib != library :
                            continue
                        hol_loc = hol.find("./location").text
                        # call_number contains cote 1 + " " + cote 2
                        hol_cote = hol.find("./call_number")
                        if hol_cote == None:
                            continue
                        hol_cote = hol.find("./call_number").text
                        hol_alma_list.append([hol_loc, hol_cote])
                        hol_id = hol.find("./holding_id").text
                        hol_alma_list_id.append([hol_loc, hol_cote, hol_id])

            ## if not exists in iz : create bib iz ##
            else :
                post_iz_record = create_bib(api_key_iz, r_get_format, nz_id)
                if post_iz_record[2] != 200:
                    process_list['création iz'] = 'error'
                    save_log(log_bib_unimported, [process_list, post_iz_record[0], el035, nz_id, '', post_iz_record[2], post_iz_record[3]])
                    continue
                process_list['création iz'] = 'done'
                iz_id = post_iz_record[1]
                # add local fields in iz
                iz_r_with_locals = update_bib(api_key_iz, r_get_format, iz_id, rule = iz_rule)
                if iz_r_with_locals[2] == 200:
                    process_list['ajout champs locaux'] = 'done'
                    save_log(log_bib, [process_list, nz_id, iz_id, el035, log_update_f, iz_r_with_locals[3]])
                else:
                    process_list['ajout champs locaux'] = 'error'
                    save_log(log_bib_unimported, [process_list, post_iz_record[0], el035, nz_id, iz_id, post_iz_record[2], post_iz_record[3]])
                    continue
                    
        ## if not exist nz : create bib nz and iz ##
        else :
            # create bib record in NZ
            post_nz_record = create_bib(api_key_nz, r_format, rule = nz_rule)
            if post_nz_record[2] != 200 :
                process_list['création nz'] = 'error'
                save_log(log_bib_unimported, [process_list, post_nz_record[0], el035, post_nz_record[1], "", post_nz_record[2], post_nz_record[3]])
                continue
            process_list['création nz'] = 'done'
            # create bib record in IZ    
            nz_id = post_nz_record[1]
            post_iz_record = create_bib(api_key_iz, r_format, nz_id)
            if post_iz_record[2] != 200:
                process_list['création iz'] = 'error'
                save_log(log_bib_unimported, [process_list, post_iz_record[0], el035, nz_id, post_iz_record[1], post_iz_record[2], post_iz_record[3]])
                continue
            process_list['création iz'] = 'done'
            iz_id = post_iz_record[1]
            # add local fields in IZ
            iz_r_with_locals = update_bib(api_key_iz, r_format, iz_id, rule = iz_rule)
            if iz_r_with_locals[2] == 200:
                process_list['ajout champs locaux'] = 'done'
                save_log(log_bib, [process_list, nz_id, iz_id, el035, "", iz_r_with_locals[3]])
            else :
                process_list['ajout champs locaux'] = 'error'
                save_log(log_bib_unimported, [process_list, iz_r_with_locals[0], el035, nz_id, iz_id, iz_r_with_locals[2], iz_r_with_locals[3]])
                continue

        # intitate list for imported items --> we don't want to importe twice same item
        items_imported = []
        # intitate list for unimported items --> used to check if item not imported at all
        items_unimported = []
        # initiate list to save holding log (not possible to save log after creation because some data are added later)
        holdings_logline = []


        ### CREATE Portfolio ###
        # for each portfolio
        for portfolio in record.findall("./portfolio"):
            # put holding location and cotation in var
            pf_nz_id = portfolio.find("./resource_metadata/mms_id").text
            pf_coll = portfolio.find("./electronic_collection/id/xml_value").text
            pf_url = portfolio.find("./linking_details/url").text
            # format holding to POST API
            pf_str = etree.tostring(portfolio).decode()
            pf_str = pf_str.replace("\n", " ").replace("\t", " ")
            # if cotation ends with (+.) not keep in holding
            if pf_nz_id != None:
                pf_str = pf_str.replace(pf_nz_id, nz_id)
            pf_format = pf_str.encode('UTF-8')
            #print(pf_format)

            # check if portfolio already exists
            pf_list = get_pf_list(api_key_iz, iz_id)
            pf_to_create = True
            existing_pf_alma = []
            if pf_list[1] != 200 :
                pf_to_create = False
                save_log(log_portfolio_unimported, ['Liste des portfolios non obtenue : ' + pf_list[0], nz_id, iz_id, '', el035, pf_coll, pf_url, pf_list[1], pf_list[2]])
                continue
            if pf_list[0] != "0" :
                pf_alma_list = etree.fromstring(pf_list[2], parser=etree.XMLParser(encoding="utf-8"))
                for pf in pf_alma_list.findall("portfolio"):
                    if pf.find("./electronic_collection/id") != None :
                        pf_alma_coll = pf.find("./electronic_collection/id").text
                    if pf_alma_coll != pf_coll :
                        existing_pf_alma.append([pf_alma_coll])
                        continue
                    id_pf_alma = pf.find("./id").text
                    full_pf_alma = get_pf(api_key_iz, iz_id, id_pf_alma)
                    if (full_pf_alma[1] != 200) :
                        pf_to_create = False
                        save_log(log_portfolio_unimported, ['Portfolio complet non obtenu : ' + full_pf_alma[0], nz_id, iz_id, existing_pf_alma, el035, pf_coll, pf_url, full_pf_alma[1], pf_format])
                        break                       
                    url_pf_alma = full_pf_alma[0]
                    existing_pf_alma.append([pf_alma_coll, url_pf_alma])
                    if url_pf_alma == pf_url :
                        pf_to_create = False
                        save_log(log_portfolio_unimported, ['Portfolio similaire trouvé', nz_id, iz_id, existing_pf_alma, el035, pf_coll, pf_url, full_pf_alma[1], pf_format])
                        break
            # create new portfolio            
            if pf_to_create :
                new_pf = create_pf(api_key_iz, pf_format, iz_id)
                if new_pf[1] != 200:
                    save_log(log_portfolio_unimported, ['Erreur d\'import : ' + new_pf[0], nz_id, iz_id, existing_pf_alma, el035, pf_coll, pf_url, new_pf[1], pf_format])
                else :
                   save_log(log_portfolio, [nz_id, iz_id, new_pf[0], el035, pf_coll, pf_url, existing_pf_alma, new_pf[2]])
                    

        ### CREATE HOLDING ###
        # for each datafield 852, create holding
        for holding_data in record.findall("./holding_data"):
            # put holding location and cotation in var
            hol_loc = holding_data.find("./datafield[@tag='852']/subfield[@code='c']").text
            hol_cote = holding_data.find("./datafield[@tag='852']/subfield[@code='h']").text
            hol_cote2 = holding_data.find("./datafield[@tag='852']/subfield[@code='j']")
            if hol_cote2 != None:
                hol_cote2 = hol_cote2.text
            """if json.loads(gen_param['cote_j']['bool'].lower()):
                hol_cote2 = holding_data.find("./datafield[@tag='852']/subfield[@code='j']").text"""
            # format holding to POST API
            hol_str = etree.tostring(holding_data).decode()
            hol_str = hol_str.replace("\n", " ").replace("\t", " ")
            # if cotation ends with regex in json file not keep in holding
            hol_cote_gen = hol_cote
            cote_regex = gen_param['cote_generique']['regex']
            if cote_regex != "" :
                hol_cote_gen = get_cote_gen(hol_cote, cote_regex)
            if hol_cote != None:
                hol_str = hol_str.replace(hol_cote, hol_cote_gen)
            if hol_cote2 != None:
                hol_cote_gen = f"{hol_cote} {hol_cote2}"
            hol_format = format_api(hol_str, "holding", "record")
            hol_format = hol_format.encode('UTF-8')

            # check if holding already exists
            current_hol = [hol_loc, hol_cote_gen]
            if current_hol not in hol_alma_list and hol_loc != None and hol_cote != None:
                # if not --> create new holding
                holding = create_holding(api_key_iz, hol_format, iz_id)
                if holding[1] == 200 :
                    holdings_logline.append([nz_id, iz_id, holding[0], el035, hol_loc, hol_cote_gen, '', '', holding[2]])
                    hol_alma_list.append(current_hol)
                    # holding[0] = hol id
                    current_hol.append(holding[0])
                    # hol imported is a list of lists : [[hol_loc, hol_cote, hol_id], [hol_loc, hol_cote, "error message"]]
                    hol_alma_list_id.append(current_hol)
                else :
                    save_log(log_holding_unimported, [f"erreur création holding : {holding[0]}", nz_id, iz_id, '', el035, hol_loc, hol_cote_gen, hol_cote, holding[1], holding[2]])

            # catch holding unimported
            else :
                hol_unimported_error = []
                if (current_hol in hol_alma_list) : hol_unimported_error.append("Cette holding existe déjà !")
                if (hol_loc == None) : hol_unimported_error.append("Localisation non renseignée")
                if (hol_cote == None) : hol_unimported_error.append("Cote non renseignée")
                hol_reject_reason = ", ".join(hol_unimported_error)
                save_log(log_holding_unimported, [hol_reject_reason, nz_id, iz_id, '', el035, hol_loc, hol_cote_gen, hol_cote, '', hol_format])
        
        # count number of holding
        hol_len = len(hol_alma_list_id)
        ### END HOLDING CREATION ####


        ### CREATE ITEM ###
        # for each item in record
        for item in record.findall("item_data"):
            # put item barcode, location and cotation in var 
            barcode = item.find("./barcode").text
            # handle case barcode is empty --> barcode = None
            if (barcode == None) : barcode = f'barcode_{datetime.now().strftime("%Y%m%d_%H%M%S%f")}'
            item_loc = item.find('./item_location').text
            item_cote = item.find('alternative_call_number').text
            item_cote2 = None
            item_cote_list = item_cote.split("|")
            if gen_param['cote_j']['bool'].lower()=="true":
                if len(item_cote_list)>1:
                    item_cote = item_cote_list[0]
                    item_cote2 = item_cote_list[1]
            item_cote_gen = item_cote
            if gen_param['item_cote']['bool'].lower()=="true":
                item_cote_gen = hol_cote_gen
            elif cote_regex != "":
                item_cote_gen = get_cote_gen(item_cote, cote_regex)
            if item_cote2 != None :
                item_cote_gen = f"{item_cote_gen} {item_cote2}"
            item_tuple = (item_loc, item_cote_gen)
            # Format item_data xml
            item_str = etree.tostring(item).decode()
            item_str = item_str.replace("\n", " ").replace("\t", " ")
            item_format = format_api(item_str, "item")
            item_format = item_format.encode('UTF-8')                        
            # holding iteration counter                            
            hol_iter = 0

            # for each record check if a holding created with same loc and cote 
            for hol in hol_alma_list_id :
                hol_iter += 1
                # if item not already imported and item location and cote same as holding, item is created in current holding
                if item_loc == hol[0] and item_cote_gen == hol[1] and barcode not in items_imported :
                    cre_item = create_item(api_key_iz, item_format, iz_id, hol[2])
                    # replace barcode value in case he's empty
                    if (cre_item[2] == 200) : 
                        save_log(log_item, [cre_item[1], nz_id, iz_id, hol[2], el035, hol[0], hol[1], "|".join(item_cote_list), cre_item[3]])
                    else :
                        save_log(log_item_unimported, [cre_item[0], barcode, nz_id, iz_id, hol[2], el035, hol[0], hol[1], "|".join(item_cote_list), "", cre_item[2], cre_item[3]])
                    items_imported.append(barcode)
                    break
                
                #print(f"hol_iter : {hol_iter} | hol_len : {hol_len}")
                #print(f"current barcode : {barcode}")
                #print(f"current item : {item_tuple}")
                #print(f"current hol : {hol}")
                #print(f"barcode liste : {items_imported}")

                # if item not imported unil last holding, added in report                                            
                if hol_iter == hol_len and barcode not in items_imported :
                    item_unimported_error = []
                    if(item_loc == None) : item_unimported_error.append("Localisation non renseignée")
                    if(item_cote == None) : item_unimported_error.append("Cote non renseignée")                                                                      
                    if(item_tuple not in hol_alma_list) : item_unimported_error.append("Aucune holding correspondante")
                    item_reject_reason = ", ".join(item_unimported_error)
                    conv_hol_str = []
                    for hol in hol_alma_list :
                        conv_hol_str.append(", ".join(hol))
                    save_log(log_item_unimported, [item_reject_reason, barcode, nz_id, iz_id, "", el035, item_loc, item_cote_gen, "|".join(item_cote_list), " | ".join(conv_hol_str), item_format])

            # catch holding without item in hol_alma_list
            if len(hol_alma_list_id) == 0 :
                save_log(log_item_unimported, ["Holding manquante", barcode, nz_id, iz_id, "", el035, item_loc, item_cote_gen, "|".join(item_cote_list), "", item_format])
        ### END ITEM CREATION ###


        ### REMOVE UNUSED HOLDING ###
        for hol in hol_alma_list_id :
            hol_index = None
            # hol[2] contains hol id or error creation message 
            if hol[2].startswith("22") :
                # check if holding has item
                item_list = get_item_list(api_key_iz, iz_id, hol[2])
                #holdings_logline contain a list of lists :  nz_id, iz_id, holding[0], el035, hol_loc, hol_cote_gen, holding[1], '', '', holding[2]]
                for el in holdings_logline :
                    if (el[2] == hol[2]) :
                        hol_index = holdings_logline.index(el)
                        # add number of items in holdings_logline
                        holdings_logline[hol_index][6] = item_list[0]
                # if resquest returns no error and number of items for this holding == 0
                if item_list[1] == 200 and item_list[0]=="0" :
                    # delete holding
                    del_hol = delete_holding(api_key_iz, iz_id, hol[2])
                    if hol_index != None :
                        # add in holdings_logline API message
                        holdings_logline[hol_index][7] = del_hol
        # save holdings log
        for line in holdings_logline :        
            save_log(log_holding, line)                 
        ### END HOLDING REMOVED ###


on_exit(log_files)

#Fin du calcul de la durée d'exécution du programme
end = datetime.now()
print(f"End time : {end.strftime('%d-%m-%Y %H:%M:%S')}")
print(f"Elapsed time : {end - start}\n===============================")