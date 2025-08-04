""" Local functions """
from log import convert_log_excel, rm_empty_file
""" Python libraries """
import json
import xml.etree.ElementTree as etree
import re # for regex
from pickle import FALSE, TRUE


# Encode record for API
def format_api(record, balise1, balise2=""):
    op_balise1 = '<' + balise1 + '>'
    end_balise1 = '</' + balise1 + '>'
    if balise2 != "":
        op_balise2 = '<' + balise2 + '>'
        end_balise2 = '</' + balise2 + '>'
    else:
        op_balise2 = ""
        end_balise2 = ""
    format = op_balise1 + op_balise2 + record + end_balise2 + end_balise1
    return format


# parse xml file and return complete content
def parse_xmlFile(xmlFile):
    # parse an xml file by name
    parser = etree.XMLParser(encoding="utf-8")
    tree = etree.parse(xmlFile, parser=parser)
    #return etree.tostring(tree.getroot())
    return tree.getroot()


# import data of json file
def read_json(jsonFile):

    with open(jsonFile) as json_file:
        data = json.load(json_file)
    return data


# retrieve element between tag in xml data
def get_el(element, balise):
    match = re.search(f"(<{balise}>)(.+)(</{balise}>)", element)
    if match != None:
        return match.group(2)
    else:
        "Empty" 


# get generic cotation
def get_cote_gen(cote, regex):
    regex.replace("\\\\", "\\")
    if cote != None:
        match = re.search(regex, cote)
        if match != None:
            return cote[:match.start()]
        else:
            return cote
    else:
        return ""


def find_etree(record, xpath):
    record_el = record.find(xpath)
    if record_el != None :
        record_el = record_el.text
    return record_el


def on_exit(dico_files):
    dico_files = rm_empty_file(dico_files)
    convert_log_excel(dico_files)
