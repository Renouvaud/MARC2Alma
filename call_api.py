""" Local functions """
from general import *
""" Python libraries """
from configparser import NoOptionError
from urllib.parse import quote, urlencode
import requests # API call
import xml.etree.ElementTree as etree
import re # for regex

def sru_search(env, search_type, content):

    if env == 'prod' :
        url = 'https://eu01.alma.exlibrisgroup.com/view/sru/41BCULAUSA_NETWORK'
    if env == 'sb' :
        url = 'https://renouvaud-psb.alma.exlibrisgroup.com/view/sru/41BCULAUSA_NETWORK'
    
    params = {'version': '1.2',
          'operation': 'searchRetrieve',
          'record_schema': 'marcxml',
          'query': f'alma.{search_type}="{content}"',
          'alma.mms_tagSuppressed': 'false'}
    try:
        r = requests.get(url, params=params)

        record_count = get_el(r.text, "numberOfRecords")
        mms_id = ''
        match = re.search('(<controlfield tag="001">)([0-9]+)(</controlfield>)', r.text)
        if match != None:
            mms_id = match.group(2)
        #import pdb; pdb.set_trace()        
        error = get_el(r.text, "diag:message")
        return {'error' : error, 'record_count' : record_count , 'nz_id': mms_id, 'r_code' : r.status_code, 'r_xml' : r.text}
        
    except requests.exceptions.ConnectionError:
        # handle error here or use a `pass` statement
        print('connection error occurred')
        return {'error' : "except erreur : problème de connection au serveur", 'nz_id': '', 'r_code' : '', 'r_xml' : ''}

    except KeyboardInterrupt:
        print("keyboard interrupt")
        return {'error' : 'except erreur : processus interrompu', 'nz_id': '', 'r_code' : '', 'r_xml' : ''}


def create_bib(api_key, record, nz_id='', rule=''):
    """ API call to Alma POST bib record"""
    url = 'https://api-eu.hosted.exlibrisgroup.com/almaws/v1/bibs/'

    # Optional params
    nz_id_param = ''
    rule_param = ''
    if(nz_id != ''):
        nz_id_param = 'from_nz_mms_id'
    if(rule != ''):
        rule_param = 'normalization'

    query_params = urlencode({quote(nz_id_param):'%s' % nz_id, quote(rule_param):'%s' % rule, quote('validate'): 'false', quote('override_warning'): 'true', quote('check_match'): 'false', quote('apikey'): '%s' % api_key})
    headers = {'Content-Type': 'application/xml', 'Accept-Encoding': '*', 'Connection': 'keep-alive'}

    try:
        r = requests.post(url, data=record, headers=headers, params=query_params)
        new_id = get_el(r.text, "mms_id")
        error = get_el(r.text, "errorMessage")

        return error, new_id, r.status_code, r.text

    except requests.exceptions.ConnectionError:
        # handle error here or use a `pass` statement
        print('connection error occurred')
        return "ERREUR : erreur de connection au serveur", "", "", ""

    except KeyboardInterrupt:
        print("keyboard interrupt")
        return "ERREUR : processus interrompu", "", "", ""


def update_bib(api_key, record, mms_id, rule=''):
    """ API call to Alma PUT bib"""
    url = 'https://api-eu.hosted.exlibrisgroup.com/almaws/v1/bibs/{mms_id}'.replace('{mms_id}', quote(mms_id))
    rule_param = ''
    if(rule != ''):
        rule_param = 'normalization'

    query_params = urlencode({quote(rule_param):'%s' % rule, quote('validate'): 'false', quote('stale_version_check'): 'false', quote('apikey'): '%s' % api_key})
    headers = {'Content-Type': 'application/xml', 'Accept-Encoding': '*', 'Connection': 'keep-alive'}

    try:
        r = requests.put(url, data=record, headers=headers, params=query_params)
        error = get_el(r.text, "errorMessage")

        return error, mms_id, r.status_code, r.text

    except requests.exceptions.ConnectionError:
        # handle error here or use a `pass` statement
        print('connection error occurred')
        return "ERREUR : erreur de connection au serveur", "", "", ""

    except KeyboardInterrupt:
        print("keyboard interrupt")
        return "ERREUR : processus interrompu", "", "", ""


def get_bib(zone_api, api_key, mms_id= "", nz_mms_id = "", other_system_id = ""):
    """ 
    API call to Alma GET bib
    zone_api = iz or nz
    zone_api is used to know if mms_id we get is nz_id or iz_id
    """
    url = 'https://api-eu.hosted.exlibrisgroup.com/almaws/v1/bibs/'

    # Optional params
    if(mms_id != ''):
        url = 'https://api-eu.hosted.exlibrisgroup.com/almaws/v1/bibs/{mms_id}'.replace('{mms_id}', quote(mms_id))

    nz_mms_id_param = ''
    if(nz_mms_id != ''):
        nz_mms_id_param = 'nz_mms_id'

    other_system_id_param = ''
    if(other_system_id != ''):
        other_system_id_param = 'other_system_id'

    query_params = urlencode({quote(nz_mms_id_param):'%s' % nz_mms_id, quote('view'): 'full', quote('expand'): 'None', quote(other_system_id_param):'%s' % other_system_id, quote('apikey'): '%s' % api_key})

    try:
        r = requests.get(url, params=query_params)

        record_count = ''
        if other_system_id != '' :
            match = re.search('(<bibs total_record_count=")([0-9]+)("/?>)', r.text)
            if match != None:
                record_count = match.group(2)            
        iz_id = ''
        if zone_api == 'iz' :
            iz_id = get_el(r.text, "mms_id")  
            nz_id = "Empty"
            match = re.search('(<linked_record_id type="NZ">)([0-9]+)(</linked_record_id>)', r.text)
            if match != None:
                nz_id = match.group(2)
        if zone_api == 'nz' :
            nz_id = get_el(r.text, "mms_id")                
        error = get_el(r.text, "errorMessage")
        return {'error' : error, 'record_count' : record_count , 'nz_id': nz_id, 'iz_id' : iz_id, 'r_code' : r.status_code, 'r_xml' : r.text}

    except requests.exceptions.ConnectionError:
        # handle error here or use a `pass` statement
        print('connection error occurred')
        return {'error' : "except erreur : problème de connection au serveur", 'nz_id': '', 'iz_id' : '', 'r_code' : '', 'r_xml' : ''}

    except KeyboardInterrupt:
        print("keyboard interrupt")
        return {'error' : 'except erreur : processus interrompu', 'nz_id': '', 'iz_id' : '', 'r_code' : '', 'r_xml' : ''}


def get_holdings(api_key, mms_id):
    """ API call to Alma GET holdings list """
    url = 'https://api-eu.hosted.exlibrisgroup.com/almaws/v1/bibs/{mms_id}'.replace('{mms_id}', quote(mms_id)) + '/holdings/'
    query_params = urlencode({quote('apikey'): '%s' % api_key})

    try:
        r = requests.get(url, params=query_params)
        # warning: also returns 200 and item number = 0 if holding doesn't exist

        hol_number = "Empty"
        match = re.search('(<holdings total_record_count=")([0-9]+)("/?>)', r.text)
        if match != None:
            hol_number = match.group(2)
        error = get_el(r.text, "errorMessage")
        return error, hol_number, r.status_code, r.text

    except requests.exceptions.ConnectionError:
        # handle error here or use a `pass` statement
        print('connection error occurred')
        return "ERREUR : erreur de connection au serveur", "", "", ""

    except KeyboardInterrupt:
        print("keyboard interrupt")
        return "ERREUR : processus interrompu", "", "", ""


def create_holding(api_key, holding, mms_id):
    """ API call to Alma POST holding"""
    url = 'https://api-eu.hosted.exlibrisgroup.com/almaws/v1/bibs/{mms_id}'.replace('{mms_id}', quote(mms_id)) + '/holdings/'
    query_params = urlencode({quote('apikey'): '%s' % api_key})
    headers = {'Content-Type': 'application/xml', 'Accept-Encoding': '*', 'Connection': 'keep-alive'}

    try:
        r = requests.post(url, data=holding, headers=headers, params=query_params)

        if r.status_code == 200:
            hol_id = get_el(r.text, "holding_id")
            return hol_id, r.status_code, r.text
        else:
            error = get_el(r.text, "errorMessage")
            return error, r.status_code, r.text

    except requests.exceptions.ConnectionError:
        # handle error here or use a `pass` statement
        print('connection error occurred')
        return "ERREUR : erreur de connection au serveur", "", ""

    except KeyboardInterrupt:
        print("keyboard interrupt")
        return "ERREUR : processus interrompu", "", ""


def get_item_list(api_key, mms_id, holding_id):
    """GET item list"""
    url = 'https://api-eu.hosted.exlibrisgroup.com/almaws/v1/bibs/{mms_id}'.replace('{mms_id}', mms_id) + '/holdings/{holding_id}'.replace('{holding_id}', holding_id) + '/items/'
    query_params = urlencode({quote('limit'): '1', quote('offset'): '0', quote('order_by'): 'none', quote('direction'): 'desc', quote('view'): 'brief', quote('apikey'): '%s' % api_key})
    
    try:
        r = requests.get(url, params=query_params)
        item_number = "Empty"
        # warning: also returns 200 and item number = 0 if holding doesn't exist
        if r.status_code == 200:
            match = re.search('(<items total_record_count=")([0-9]+)("/?>)', r.text)
            if match != None:
                item_number = match.group(2)
            return item_number, r.status_code, r.text
        else :
            error = get_el(r.text, "errorMessage")
            return error, r.status_code, r.text

    except requests.exceptions.ConnectionError:
        # handle error here or use a `pass` statement
        print('connection error occurred')
        return "ERREUR : erreur de connection au serveur", "", ""

    except KeyboardInterrupt:
        print("keyboard interrupt")
        return "ERREUR : processus interrompu", "", ""


def get_pf_list(api_key, mms_id):
    """GET portfolio list"""
    url = 'https://api-eu.hosted.exlibrisgroup.com/almaws/v1/bibs/{mms_id}'.replace('{mms_id}', mms_id) + '/portfolios/'
    query_params = urlencode({quote('limit'): '100', quote('offset'): '0', quote('apikey'): '%s' % api_key})
    
    try:
        r = requests.get(url, params=query_params)
        pf_number = "Empty"
        # warning: also returns 200 and item number = 0 if holding doesn't exist
        if r.status_code == 200:
            match = re.search('(<portfolios total_record_count=")([0-9]+)("/?>)', r.text)
            if match != None:
                pf_number = match.group(2)
            return pf_number, r.status_code, r.text
        else :
            error = get_el(r.text, "errorMessage")
            return error, r.status_code, r.text

    except requests.exceptions.ConnectionError:
        # handle error here or use a `pass` statement
        print('connection error occurred')
        return "ERREUR : erreur de connection au serveur", "", ""

    except KeyboardInterrupt:
        print("keyboard interrupt")
        return "ERREUR : processus interrompu", "", ""


def get_pf(api_key, mms_id, pf_id):
    """GET portfolio content"""
    url = 'https://api-eu.hosted.exlibrisgroup.com/almaws/v1/bibs/{mms_id}'.replace('{mms_id}', mms_id) + '/portfolios/{pf_id}'.replace('{pf_id}', pf_id)
    query_params = urlencode({quote('apikey'): '%s' % api_key})
    
    try:
        r = requests.get(url, params=query_params)
        pf_url = "Empty"
        # warning: also returns 200 and item number = 0 if holding doesn't exist
        if r.status_code == 200:
            match = re.search('(<url>jkey=)(.+)(</url>)', r.text)
            if match != None:
                pf_url = match.group(2)
            return pf_url, r.status_code, r.text
        else :
            error = get_el(r.text, "errorMessage")
            return error, r.status_code, r.text

    except requests.exceptions.ConnectionError:
        # handle error here or use a `pass` statement
        print('connection error occurred')
        return "ERREUR : erreur de connection au serveur", "", ""

    except KeyboardInterrupt:
        print("keyboard interrupt")
        return "ERREUR : processus interrompu", "", ""


def delete_holding(api_key, mms_id, holding_id):
    """DELETE holding"""
    url = 'https://api-eu.hosted.exlibrisgroup.com/almaws/v1/bibs/{mms_id}'.replace('{mms_id}', mms_id) + '/holdings/{holding_id}'.replace('{holding_id}', holding_id)
    # param bib=delete --> Method for handling a Bib record left without any holdings
    query_params = urlencode({quote('bib'): 'retain', quote('apikey'): '%s' % api_key})
    
    try:
        r = requests.delete(url, params=query_params)
        # code 204 = ok
        if r.status_code == 204 :
            return "holding supprimée avec succès"
        else :
            error = get_el(r.text, "errorMessage")
            return f"erreur de suppression : {error}", r.status_code, r.text

    except requests.exceptions.ConnectionError:
        # handle error here or use a `pass` statement
        print('connection error occurred')
        return "ERREUR : erreur de connection au serveur", "", ""
        
    except KeyboardInterrupt:
        print("keyboard interrupt")
        return "ERREUR : processus interrompu", "", ""


def create_pf(api_key, portfolio, mms_id):
    """API call POST create portfolio (BIBS API)"""
    url = 'https://api-eu.hosted.exlibrisgroup.com/almaws/v1/bibs/{mms_id}'.replace('{mms_id}', quote(mms_id)) + '/portfolios/'
    query_params = urlencode({quote('apikey'): '%s' % api_key})
    headers = {'Content-Type': 'application/xml', 'Accept-Encoding': '*', 'Connection': 'keep-alive'}

    try:
        r = requests.post(url, data=portfolio, headers=headers, params=query_params)

        if r.status_code == 200:
            pf_id = ""
            match = re.search(f"(<id>)([0-9]+)(</id>)", r.text)
            if match != None:
                pf_id = match.group(2)
            return pf_id, r.status_code, r.text
        else:
            error = get_el(r.text, "errorMessage")
            return error, r.status_code, r.text

    except requests.exceptions.ConnectionError:
        # handle error here or use a `pass` statement
        print('connection error occurred')
        return "ERREUR : erreur de connection au serveur", "", ""

    except KeyboardInterrupt:
        print("keyboard interrupt")
        return "ERREUR : processus interrompu", "", ""


def create_item(api_key, item, mms_id, holding_id, generate_inventory_num_name=""):
    """API call POST create item (BIBS API)"""
    url = 'https://api-eu.hosted.exlibrisgroup.com/almaws/v1/bibs/{mms_id}'.replace('{mms_id}', quote(mms_id)) +'/holdings/{holding_id}'.replace('{holding_id}', quote(holding_id)) + '/items/'
    headers = {'Content-Type': 'application/xml', 'Accept-Encoding': '*', 'Connection': 'keep-alive'}
    if generate_inventory_num_name=="":
        query_params = urlencode({quote('generate_description'): 'false', quote('apikey'): '%s' % api_key})
    else:
        query_params = urlencode({quote('generate_description'): 'false', quote('generate_inventory_num_name'): generate_inventory_num_name, quote('apikey'): '%s' % api_key})
    try:
        r = requests.post(url, data=item, headers=headers, params=query_params)

        barcode = get_el(r.text, "barcode")
        error = get_el(r.text, "errorMessage")
        return error, barcode, r.status_code, r.text

    except requests.exceptions.ConnectionError:
        # handle error here or use a `pass` statement
        print('connection error occurred')
        return "ERREUR : erreur de connection au serveur", "", "", ""

    except KeyboardInterrupt:
        print("keyboard interrupt")
        return "ERREUR : processus interrompu", "", "", ""