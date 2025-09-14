# Copyright 2025 Renouvaud
# License GPL-3.0 or later (https://www.gnu.org/licenses/gpl-3.0)

""" Python libraries """
import re 
from pickle import FALSE, TRUE
import xml.etree.ElementTree as etree
from pymarc import *
import collections 

""" Local functions """
from call_api import get_bib, sru_search
from log import save_log
from general import parse_xmlFile, find_etree
from match import double_check


def check_duplicate(xmlFile, xpath_el, none_val, balise1, balise2 = ''):
    """ 
    Check for duplicate values in a given XML element.

    Args:
        xmlFile (str): Path to XML file.
        xpath_el (str): XPath expression to locate elements.
        none_val (bool): If True, allows None/empty values in duplicates.
        balise1 (str): Primary XML tag to check.
        balise2 (str): Secondary XML tag if different from balise1.

    Returns:
        bool: True if duplicates exist, False otherwise.
    """
    duplicate_exist = False
    content_list = []
    for node in parse_xmlFile(xmlFile).findall(xpath_el):
        node = etree.tostring(node).decode()
        if balise2 != '' :
            content = re.search(f'(<{balise1}>)(.+)(</{balise2}>)', node)
        else :
            content = re.search(f'(<{balise1}>)(.+)(</{balise1}>)', node)
        if content != None :
            content = content.group(2)
        content_list.append(content)

    # Find values that occur more than once
    content_multiple = [content for content, count in collections.Counter(content_list).items() if count > 1]
    
    # If None values are allowed, remove them from the duplicates
    if none_val :
        content_multiple = [content for content in content_multiple if content is not None]
    
    # If no duplicates found
    if content_multiple == [] :      
        return duplicate_exist

     # If duplicates found   
    if len(content_multiple)>0 :
        duplicate_exist = True
    print(f"Warning: file {xmlFile} contains duplicate values: {content_multiple}\n"
          f"Check tag <{balise1}> at xpath: '{xpath_el}'\n")
    return duplicate_exist


def bib_to_reject(xmlRecord):
    """ 
    Check if a bibliographic record should be rejected 
    (must contain holding, item, or portfolio).
    """        
    bib_reject_reason = []
    bib_to_reject = False
    el035 = xmlRecord.find('./datafield[@tag="035"]/subfield[@code="a"]')
    if (el035 != None) : el035 = el035.text
    hasitem = xmlRecord.find("./item_data")
    if hasitem is None: 
        bib_reject_reason.append('Record without item')
    hasholding = xmlRecord.find("./holding_data")
    if hasholding is None: 
        bib_reject_reason.append('Record without holding')
    hasportfolio = xmlRecord.find("./portfolio")
    if hasportfolio is None: 
        bib_reject_reason.append('Record without portfolio')

    # Reject if missing both item+holding and no portfolio
    if (hasitem is None or hasholding is None) and hasportfolio is None:
        bib_to_reject = True
    return bib_to_reject, ", ".join(bib_reject_reason)


def get_bib_other_id(zone, api_key, record_id, multi_prefix, bib_match):
    """
    Check if a record exists in Alma by using alternative system IDs (035, ISBN, ISSN...).

    Handles multi-prefix identifiers and updates bib_match dict with results.
    """

    get_record = get_bib(zone, api_key, other_system_id = record_id)    # code 400 = error. If no match found, returns code 200 and xml : <bibs total_record_count="0"/?>
    if zone == "iz" :
        r_exist = bib_match['exist_iz']
    elif zone == "nz" :
        r_exist = bib_match['exist_nz']
    
    # Found a match
    if get_record['record_count'] == "1" :
        r_exist = True
    # Try other prefixes if no match
    elif get_record['record_count'] == "0" and len(multi_prefix) > 0 :
        count = 0
        for prefix in multi_prefix :
            count += 1
            if count == 1 :
                continue
            record_id = record_id.replace(multi_prefix[count-2],prefix)
            get_record = get_bib(zone, api_key, other_system_id = record_id)
            if get_record['record_count'] == "1" :
                r_exist = True
                break
            elif get_record['record_count'] == "0" :
                pass
            else :
                r_exist = True
                bib_match['api_error'] = True
                break
    # No match found
    elif get_record['record_count'] == "0" :
        pass
    # Multiple matches or API error
    else :
        r_exist = True
        bib_match['api_error'] = True

    # Update bib_match dict
    if zone == "iz" :
        bib_match['exist_iz'] = r_exist
    elif zone == "nz" :
        bib_match['exist_nz'] = r_exist
    globals()['bib_match'] = bib_match 
    return get_record 
    

def update_bib_match(get_record, bib_match) :
    """ 
    Update bib_match dict based on API response. 
    """
    if  get_record['r_code'] == 200 :
        bib_match['exist_iz'] = True                
    if get_record['r_code'] == 500 : 
        bib_match['api_error'] = True
    globals()['bib_match'] = bib_match
   

def bib_has_match(xmlRecord, xpath_balise, id_type, multi_prefix, el035, log_bib_match, api_key_nz, api_key_iz, bib_match):
    """
    Check if a bibliographic record already exists in Alma IZ or NZ.
    Updates bib_match dict accordingly and logs results.
    """
    zone = ''
    record_id = None
    # Extract record_id depending on ID type
    if xpath_balise != "" :
        record_id = find_etree(xmlRecord, xpath_balise)
    else :
        if id_type == "nz_id" or id_type == "iz_id" :
            record_id = find_etree(xmlRecord, 'mms_id')
        elif id_type == "035" :
            record_id = el035

    if record_id != None :
        zone = 'iz'
        # Lookup in IZ
        if id_type == "nz_id" :
            get_record = get_bib(zone, api_key_iz, nz_mms_id = record_id)
            update_bib_match(get_record, bib_match)
        elif id_type == "iz_id" :
            get_record = get_bib(zone, api_key_iz, mms_id = record_id)
            update_bib_match(get_record, bib_match)
        elif id_type == "035" :
            get_record = get_bib_other_id(zone, api_key_iz, record_id, multi_prefix, bib_match)
        else :
            print("ERROR: choose a valid 'id_type' in config file. Accepted values: 'iz_id', 'nz_id', '035', 'empty'")
            exit()
        
        # If record exists in IZ
        if bib_match['exist_iz'] and not bib_match['api_error'] :
            bib_match['exist_nz'] = True
            bib_match['nz_id'] = get_record['nz_id']
            bib_match['iz_id'] = get_record['iz_id']
            bib_match['get_record_xml'] = get_record['r_xml']

        # If not in IZ, try NZ
        elif not bib_match['exist_iz'] and not bib_match['api_error']  :
            zone = 'nz'
            if id_type == "nz_id" :
                get_record = get_bib(zone, api_key_nz, mms_id = bib_match['nz_id'])
                update_bib_match(get_record, bib_match)
            elif id_type == "035" :
                get_record = get_bib_other_id(zone, api_key_nz, record_id, multi_prefix, bib_match)
            # if record exists in nz --> keep values
            if bib_match['exist_nz'] and not bib_match['api_error'] :
                bib_match['nz_id'] = get_record['nz_id']
                bib_match['get_record_xml'] = get_record['r_xml']

        # Log results if a match or API error occurred
        # code 400 isn't an error, just no match)
        if bib_match['exist_iz'] or bib_match['exist_nz'] or bib_match['api_error'] :
            save_log(log_bib_match, [zone.upper(), bib_match['sru'],
            get_record['error'], bib_match['nz_id'], bib_match['iz_id'],
            el035, get_record['r_code'], bib_match['get_record_xml']])           
    globals()['bib_match'] = bib_match


def bib_match_valid(bib_match, r_alma, api_key_iz, erreur, code):
    zone = 'nz'                    
    bib_match['exist_nz'] = True
    match = re.search('tag="001">([0-9]+)<', str(r_alma))
    bib_match['nz_id'] = match.group(1)
    bib_match['get_record_xml'] = r_alma

    # check if record exists in iz
    r_alma = get_bib('iz', api_key_iz, nz_mms_id = bib_match['nz_id'])
    if r_alma['r_code'] == 200 :
        erreur = r_alma['error']
        code = r_alma['r_code']
        zone = 'iz'
        bib_match['exist_iz'] = True
        bib_match['iz_id'] = r_alma['iz_id']
        bib_match['get_record_xml'] = r_alma['r_xml']     
    if r_alma['r_code'] == 500 : 
        bib_match['api_error'] = True
        erreur = r_alma['error']
        code = r_alma['r_code']
    return bib_match, zone, erreur, code


def bib_sru(r_import, id_list, el035, api_key_iz, sru_link, log_bib_match, env, bib_match, filter_and, filter_or):
    id_dico = {
        "isbn" : './datafield[@tag="020"]/subfield[@code="a"]',
        "issn" : './datafield[@tag="022"]/subfield[@code="a"]',
        "standard_number" : './datafield[@tag="024"]/subfield[@code="a"]'
    }
    code = ''
    error = ''
    zone = ''
    for id_type in id_list :
        if id_type in id_dico.keys():
            id_path = id_dico[id_type]
            id_value = find_etree(r_import, id_path)
            if id_value != None :
                r_alma = sru_search(sru_link, id_type, id_value)
                erreur = r_alma['error']
                code = r_alma['r_code']
                # un seul record correspond  --> double check
                if r_alma['r_code'] == 200 and r_alma['record_count'] == '1' :
                    # Double check avec éléments renseignés dans filter_criteria
                    #{'nb_valid_rec': len(valid_rec), 'valid_rec_list': valid_rec, 'log_all_rec':log_all_rec} 
                    valid_rec = False
                    if filter_and !=[]:
                        check_filter_and = double_check(r_alma['r_xml'], r_import, filter_and, 'and')
                        bib_match['sru'].append({'filter_and':check_filter_and['log_all_rec']})
                    if filter_or !=[]:
                        check_filter_or = double_check(r_alma['r_xml'], r_import, filter_or, 'or')
                        bib_match['sru'].append({'filter_or':check_filter_or['log_all_rec']})
                    if filter_and !=[] and filter_or !=[]:
                        if check_filter_and['valid_rec_list']!=[] and check_filter_and['valid_rec_list']==check_filter_or['valid_rec_list']:
                            valid_rec = True
                    elif filter_and!=[] and check_filter_and['valid_rec_list']!=[]:
                        valid_rec = True
                    elif filter_or!=[] and check_filter_or['valid_rec_list']!=[]:
                        valid_rec = True
                    # Si pas de correspondance --> création record
                    if not valid_rec:
                        pass
                    # Si double check ok
                    else:
                        valid_match = bib_match_valid(bib_match, r_alma['r_xml'], api_key_iz, erreur, code)
                        bib_match = valid_match[0]
                        zone = valid_match[1]
                        erreur = valid_match[2]
                        code = valid_match[3]
                        break

                # plusieurs correspondances --> double check
                elif r_alma['r_code'] == 200 and int(r_alma['record_count']) > 1 :
                    # Double check avec éléments renseignés dans filter_criteria
                    valid_rec = False
                    no_valid_rec = False
                    if filter_and !=[]:
                        check_filter_and = double_check(r_alma['r_xml'], r_import, filter_and, 'and')
                        bib_match['sru'].append({'filter_and':check_filter_and['log_all_rec']})
                    if filter_or !=[]:
                        check_filter_or = double_check(r_alma['r_xml'], r_import, filter_or, 'or')
                        bib_match['sru'].append({'filter_or':check_filter_or['log_all_rec']})
                    if filter_and !=[] and filter_or !=[]:
                        if check_filter_and['valid_rec_list']!=[]:
                            fusion_valid_rec = [rec for rec in check_filter_and['valid_rec_list'] if rec in check_filter_or['valid_rec_list']]
                            if len(fusion_valid_rec) == 1:
                                valid_rec = True
                            elif fusion_valid_rec == []:
                                no_valid_rec = True
                        else:
                            no_valid_rec = True
                    elif filter_and!=[]:
                        if len(check_filter_and['valid_rec_list'])==1:
                            fusion_valid_rec = check_filter_and['valid_rec_list']
                            valid_rec = True
                        elif check_filter_and['valid_rec_list']==[]:
                            no_valid_rec = True 
                    elif filter_or!=[]:
                        if len(check_filter_or['valid_rec_list'])==1:
                            fusion_valid_rec = check_filter_or['valid_rec_list']
                            valid_rec = True
                        elif check_filter_or['valid_rec_list']==[]:
                            no_valid_rec = True 
                    # Si une seule notice valide passe le double check --> raccrochage
                    if valid_rec:
                        valid_match = bib_match_valid(bib_match, fusion_valid_rec, api_key_iz, erreur, code)
                        bib_match = valid_match[0]
                        zone = valid_match[1]
                        erreur = valid_match[2]
                        code = valid_match[3]
                        break
                    # Sinon, si pas de correspondance --> création record
                    elif no_valid_rec :
                        pass

                    # Si plusieurs notices passent le double check --> erreur
                    else:
                        zone = 'nz'                   
                        bib_match['exist_nz'] = True
                        bib_match['get_record_xml'] = r_alma['r_xml']
                        bib_match['api_error'] = True
                        erreur = 'multi match found : notice non importée !'

                # pas de correspondance --> création record
                elif r_alma['r_code'] == 200 and r_alma['record_count'] == '0' :
                    pass

                # l'appel API renvoie une erreur --> pas d'import, log API ajouté à log_bib_match
                elif r_alma['r_code'] != 200 :
                    bib_match['api_error'] = True
                    bib_match['get_record_xml'] = r_alma['r_xml']     
            else :
                pass # pas d'id correspondant dans le code du fichier source --> pas de recherche sru --> création record
        else :
            print("Valeur non reconnue dand fichier json 'general_params['sru_search']['identifier']'")
            print(f"Processus terminé avec la notice {el035}")
            exit()
    bib_match['get_record_xml'] = bib_match['get_record_xml'].replace("\n", " ").replace("\t", " ")
    globals()['bib_match'] = bib_match
    if bib_match['exist_iz'] or bib_match['exist_nz'] or bib_match['api_error'] :
        save_log(log_bib_match, [zone.upper(), bib_match['sru'], erreur, bib_match['nz_id'], bib_match['iz_id'], el035, code, bib_match['get_record_xml']])    


def add_new_field(f_alma=None, code=None, val_imp=None, log=None, r_alma=None, f_imp=None):
    if r_alma != None:
        r_alma.add_field(f_imp)
        log.append(f"{f_imp} a été ajouté")


def concat_at_end(f_alma=None, code=None, val_imp=None, log=None, r_alma=None, f_imp=None):
    new_val = f"{f_alma.get_subfields(code)[0]} {val_imp}"
    f_alma.delete_subfield(code) # delete only first subfield with given code!
    f_alma.add_subfield(code, new_val, -1)
    add = False
    log.append(f"un élément a été ajouté à la fin du champ '{f_alma}'")
    return add


def add_new_subfield(f_alma=None, code=None, val_imp=None, log=None, r_alma=None, f_imp=None):
    f_alma.add_subfield(code, val_imp, -1)
    add = False
    log.append(f"un sous-champ a été ajouté à '{f_alma}'")
    return add


def match_subfields(f_function, f_imp, f_alma, code, val_added, fields_alma, log):
    for val_imp in f_imp.get_subfields(code):
        if val_imp not in val_added :
            values_alma = f_alma.get_subfields(code)
            add = True
            if len(values_alma) > 0 :
                for val_alma in values_alma:
                    if val_imp in val_alma:
                        add = False
                        val_added.append(val_imp)
                    # comp similarité entre val_imp et val_alma
                    # if similarité élevée not add, else : add_new_el
                    # attention aux champs 505 --> similarité élevée pour différents volumes
                    # attention à ne pas faire de match avec autre champ venant du fichier d'import : passer fields_imp en param
                if add :
                    add = globals()[f_function](f_alma=f_alma, code=code, val_imp=val_imp, log=log, r_alma=None, f_imp=None)
                    val_added.append(val_imp)
        if f_alma == fields_alma[len(fields_alma)-1] and val_imp not in val_added : 
            f_alma.add_subfield(code, val_imp, -1)
            val_added.append(val_imp)
            log.append(f"le sous-champ '{code}' a été ajout : {f_alma}")


def r_update_content(f_function, r_import, r_alma, field, subfields):
    log = []
    if f_function not in globals():
        log.append(f"erreur: élément inconnu dans 'update method' : {f_function}")
        return log[0], r_alma
    fields_imp = r_import.get_fields(field)
    if len(fields_imp) == 0 :
        log.append(f"le champ {field} n'a pas été trouvé dans la source")
        return log[0], r_alma
    fields_alma = r_alma.get_fields(field)        
    if len(fields_imp) > 0 and len(fields_alma) == 0 :
        for f_imp in fields_imp :            
            add_new_field(f_alma=None, code=None, val_imp=None, log=log, r_alma=r_alma, f_imp=f_imp)
        return " ; ".join(log), r_alma
    val_added = []
    for f_imp in fields_imp :
        for f_alma in fields_alma : 
            if f_function == "add_new_field":
                if f_imp.subfields_as_dict().items() == f_alma.subfields_as_dict().items() :
                    val_added.append(f_imp)
                if f_imp not in val_added and f_alma == fields_alma[len(fields_alma)-1] :
                    add_new_field(f_alma=None, code=None, val_imp=None, log=log, r_alma=r_alma, f_imp=f_imp)
                    continue
            if not subfields :
                subfields = [code for code in f_imp.subfields_as_dict().keys()]
            for code in subfields :
                match_subfields(f_function, f_imp, f_alma, code, val_added, fields_alma, log)
    return " ; ".join(log), r_alma
