from unidecode import unidecode
import re
from pymarc import *
import xml.etree.ElementTree as etree
import io


def sru_normalize(sentence):
    if sentence == None :
        return ""
    rm_crochets = re.sub(r'\[.+\]',' ', sentence)
    rm_punc = no_punc(rm_crochets)
    listed_terms = sru_filter(rm_punc.lower())
    return listed_terms


def no_punc(sentence):
    # ancienne version : [\,\.\;\'\(\)/\\|\&\%\*\"]
    rm_punc = re.sub('[,\.;\'\(\)/\\\|&%\*\"!?:\s*\t\n\[\]]',' ', sentence)
    return rm_punc.strip()


def sru_filter(sentence):
    if sentence == None :
        return ""
    terms_list = sentence.split(" ")
    terms_filter = []
    #det_list = ["le", "la", "les", "un", "une", "des", "et"]
    for el in terms_list:
        if len(el)>1: #and el not in det_list:
            terms_filter.append(el)
    listed_terms = "+".join(terms_filter)
    return listed_terms

def extract_subfield(record, filter_values):
    tag_code =  filter_values.split("|")
    tag = tag_code[0]
    if len(tag_code)<2:
        print("Erreur : check filter_criteria in json file --> tag and code must be given : example : '245|a,b'")
        return None
    code_list = tag_code[1].split("_")
    field_str = ""
    fields = record.get_fields(tag)
    if len(fields) > 0:
        for f in fields:
            for code in code_list:
                if len(code.strip())!=1:
                    continue 
                subfields = f.get_subfields(code)
                field_str = f"{field_str} {' '.join(subfields)}".strip()
    field_str = sru_normalize(field_str)
    return unidecode(field_str)

def str_match(alma_el, file_el):
    # comp words
    set_alma_t = set(alma_el.split("+"))
    set_file_t = set(file_el.split("+"))
    diff_file_t = [word for word in file_el.split("+") if word not in set_alma_t]
    diff_alma_t = [word for word in alma_el.split("+") if word not in set_file_t]
    diff_titles = diff_file_t + diff_alma_t
    if (len(set_file_t)>5 and len(diff_titles)<3) or (len(set_file_t)>2 and len(diff_titles)<2) or len(diff_titles)==0:
        return f"match : {diff_titles}"
    else :
        return f"no match : {diff_titles}"

def double_check(get_record, r_import, filter_el, operateur):
    alma_records = pymarc.parse_xml_to_array(io.StringIO(get_record))
    record_file = etree.tostring(r_import).decode()
    r_file = pymarc.parse_xml_to_array(io.StringIO(record_file))[0]
    valid_rec = []
    log_all_rec = []
    for r_alma in alma_records:
        if r_alma == None:
            continue
        match_el={}
        count=0
        for criteria in filter_el:
            file_el = extract_subfield(r_file, criteria)
            if file_el == None or file_el =="":
                continue
            alma_el = extract_subfield(r_alma, criteria)
            if alma_el == None or alma_el == "":
                continue
            match = str_match(alma_el, file_el)
            if "no match" not in match:
                count+=1
            match_el[criteria] = match
        nz_id =  r_alma.get_fields('001')[0].value()
        if operateur =='and' and len(filter_el) == count:
            valid_rec.append(record_to_xml(r_alma).decode())
        elif operateur =='or' and count>0:
            valid_rec.append(record_to_xml(r_alma).decode())        
        log_all_rec.append({'nz_id': nz_id} | match_el)
    return {'valid_rec_list': valid_rec, 'log_all_rec':log_all_rec} 



