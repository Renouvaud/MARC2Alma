""" Local functions """
from ast import Pass
from general import *
from call_api import *
from log import *
from match import *
""" Python libraries """
import re # for regex
from pickle import FALSE, TRUE
import xml.etree.ElementTree as etree
import io
from pymarc import *
from pymarc import exceptions as exc
import collections # for check duplicate
#import pdb; pdb.set_trace()


def check_duplicate(xmlFile, xpath_el, none_val, balise1, balise2 = ''):
    """ 
        Function to find duplicates in xml file
        do not return an error if specified node not exist
        'none_val' is used to check if node with empty value should be returned as duplicate or not
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

    content_multiple = [content for content, count in collections.Counter(content_list).items() if count > 1]
    # If value None authorized
    if none_val :
        content_multiple = [content for content in content_multiple if content is not None]
    # if specified element node not exist in file --> no duplicates 
    if content_multiple == [] :      
        return duplicate_exist
    if len(content_multiple)>0 :
        duplicate_exist = True
    print(f"Attention, le fichier {xmlFile} contient les valeurs suivantes en double : {content_multiple}\nvoir la balise <{balise1}> à l'emplacement : '{xpath_el}'\n")
    return duplicate_exist


def bib_to_reject(xmlRecord):
    """ 
        Function to check if record has holding and item
    """        
    bib_reject_reason = []
    bib_to_reject = False
    el035 = xmlRecord.find('./datafield[@tag="035"]/subfield[@code="a"]')
    if (el035 != None) : el035 = el035.text
    hasitem = xmlRecord.find("./item_data")
    if (hasitem == None) : bib_reject_reason.append('Notice sans exemplaire')
    hasholding = xmlRecord.find("./holding_data")
    if (hasholding == None) : bib_reject_reason.append('Notice sans holding')
    hasportfolio = xmlRecord.find("./portfolio")
    if (hasportfolio == None) : bib_reject_reason.append('Notice sans portfolio')
    if ((hasitem == None or hasholding == None) and hasportfolio == None):
        bib_to_reject = True
    return  bib_to_reject, ", ".join(bib_reject_reason)


def get_bib_other_id(zone, api_key, record_id, multi_prefix, bib_match):
    # caution with param other_system_id, code 400 = error. If no match found, returns code 200 and xml : <bibs total_record_count="0"/?>
    get_record = get_bib(zone, api_key, other_system_id = record_id)
    if zone == "iz" :
        r_exist = bib_match['exist_iz']
    elif zone == "nz" :
        r_exist = bib_match['exist_nz']
    # we get a match !
    if get_record['record_count'] == "1" :
        r_exist = True
    # check if match found with other prefixes
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
    # just no match
    elif get_record['record_count'] == "0" :
        pass
    # there is a problem : multiples match or API error
    else :
        r_exist = True
        bib_match['api_error'] = True

    # update exist_iz or exist_nz
    if zone == "iz" :
        bib_match['exist_iz'] = r_exist
    elif zone == "nz" :
        bib_match['exist_nz'] = r_exist
    globals()['bib_match'] = bib_match 
    return get_record 
    

def update_bib_match(get_record, bib_match) :
    if  get_record['r_code'] == 200 :
        bib_match['exist_iz'] = True                
    if get_record['r_code'] == 500 : 
        bib_match['api_error'] = True
    globals()['bib_match'] = bib_match
   

def bib_has_match(xmlRecord, xpath_balise, id_type, multi_prefix, el035, log_bib_match, api_key_nz, api_key_iz, bib_match):
    """
        function to check if record is already in Alma iz or nz
        return dict
    """
    zone = ''
    record_id = None
    # get value for record_id
    if xpath_balise != "" :
        record_id = find_etree(xmlRecord, xpath_balise)
    else :
        if id_type == "nz_id" or id_type == "iz_id" :
            record_id = find_etree(xmlRecord, 'mms_id')
        elif id_type == "035" :
            record_id = el035   
    if record_id != None :
        zone = 'iz'
        # check if recrod exists in iz
        if id_type == "nz_id" :
            get_record = get_bib(zone, api_key_iz, nz_mms_id = record_id)
            update_bib_match(get_record, bib_match)
        elif id_type == "iz_id" :
            get_record = get_bib(zone, api_key_iz, mms_id = record_id)
            update_bib_match(get_record, bib_match)
        elif id_type == "035" :
            get_record = get_bib_other_id(zone, api_key_iz, record_id, multi_prefix, bib_match)
        else :
            print("ERREUR : choisir un 'id_type' valide dans le fichier de paramétrage. List des valeurs acceptées : 'iz_id', 'nz_id', '035', 'empty'")
            exit()
        # if exists in iz : keep values
        if bib_match['exist_iz'] and not bib_match['api_error'] :
            bib_match['exist_nz'] = True
            bib_match['nz_id'] = get_record['nz_id']
            bib_match['iz_id'] = get_record['iz_id']
            bib_match['get_record_xml'] = get_record['r_xml']

        # if record not exists in iz, try in nz
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
        # if match or if API returns an error (code 400 isn't an error, just means we didn't find a match)
        if bib_match['exist_iz'] or bib_match['exist_nz'] or bib_match['api_error'] :
            #save_log(log_bib_match, [zone.upper(), get_record['error'], get_record['nz_id'], get_record['iz_id'], el035, get_record['r_code'], get_record['r_xml']])
            save_log(log_bib_match, [zone.upper(), bib_match['sru'], get_record['error'], bib_match['nz_id'], bib_match['iz_id'], el035, get_record['r_code'], bib_match['get_record_xml']])           
    globals()['bib_match'] = bib_match
    #return {'api_error': api_error, 'exist_nz' : exist_nz, 'exist_iz' : exist_iz, 'nz_id' : nz_id, 'iz_id' : iz_id, 'get_xml' : get_record_xml}

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


def bib_sru(r_import, id_list, el035, api_key_iz, log_bib_match, env, bib_match, filter_and, filter_or):
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
                r_alma = sru_search(env, id_type, id_value)
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
