# MARC2Alma

## About

### EN
This project is a Python script designed to upload a MARC21/XML file containing bibliographic records, holdings, items, and/or portfolios into the Alma ILS. During the import process, record deduplication can be performed using the NZid, IZid, another 035 identifier, or other identifiers such as ISBN, ISSN, or catalog numbers. The script also supports adding global and local fields, as well as defining specific rules to handle record merges.

### FR
Ce projet est un script python qui permet de charger un fichier Marc21/xml contenant des notices bibliographiques, des holdings, des items et / ou des portfolio vers le SIGB Alma. Lors du chargement un dédoublonnage des notices peut être effectué grâce au NZid, au IZid, à un autre identifiant 035 ou encore grâce à un identifiant de type ISBN, ISSN, numéro de catalogue, etc. Il est possible d'ajouter des champs globaux et locaux et de définir des règles spécifiques pour les cas de fusion.

* Author: Noémie Payot (noemie.payot@bcu.unil.ch)
* Year: 2024
* Version: 1.6
* License: GNU General Public License v3.0

## Documentation

### Dependencies

* pymarc
* xml.etree.ElementTree
* csv
* pandas
* json
* re
* datetime
* io
* errno
* pickle
* collections
* unidecode
* urllib.parse
* requests

### Installation

* Clone the repository to your machine.
* Copy secure_params_default.json, rename it to secure_params.json, and set the configuration variables.
* Copy gen_params_default.json, rename it to gen_params.json, and set the configuration variables.
* run main_vxx.py

### Secure_params configuration

#### API keys
Add api keys in the file. Api keys must have read and write access on bibliographic records.
Nz is the abbreviation for Network Zone, iz for Institution Zone, sb for sandbox and prod for the production environment.
E.g. '"api_key_nz_prod" : "<add key here for Network zone in production environment>"'
Add as many iz keys as necessary.

#### SRU search
SRU search can be used to deduplicate bibliographic records.
If necessary, modify the sandbox and production URLs. Link to SRU documentation: https://developers.exlibrisgroup.com/alma/integrations/SRU/

### Gen_params configuration

* env_param: choose Alma environment. Use 'sb' for sandbox env or 'prod' for production
* inst_param: choose Alma institution zone. Abbreviations used must be consistent with those provided in secure_params.json
* file_param :
    * XMLfile_name: input file name without extension
    * XMLfile_path: path to inputfile. E.g. "./" if file in same directory
* secure_file_path: path to secure_params.json. E.g. "./secure_files/" if file in subdirectory 'secure_files',
* rules_param: This parameter allows to apply normalization rules (see documentation https://knowledge.exlibrisgroup.com/Alma/Product_Documentation/010Alma_Online_Help_(English)/Metadata_Management/016Working_with_Rules/020Working_with_Normalization_Rules) to imported or updated bib records. These rules must be added in a process on Alma (see documentation https://knowledge.exlibrisgroup.com/Alma/Product_Documentation/010Alma_Online_Help_(English)/040Resource_Management/080Configuring_Resource_Management/070Configuring_Processes), and the process ID must be entered here. E.g. "nz_rule_sb" : "10279310411000XXXX"
* code_bib_alma: insert Alma library code. If the record already exists in Alma, the library code is used to check whether the desired holding already exists.
* fields_update: allows to specify the fields to add in existing records, as well as the merge method. Tree merge method exist : 1'concat_at_end', 2'add_new_field' or 3'add_new_subfield.
    * update_method:
        1. Concatenates the value to the end of the existing field after a space.
        2. Add field if same field with same subfields doesn't exist, doesn't check indicators. E.g.: add whole field '985 $$2 test $$a 980' even if '985 $$2 vdbcul $$a 980' already exists.
        3. Check in every existing field if subfield already exists before. With same example as before : will only add '$$2 test' in existing 985.
    * subfields: add here each subfields between [] with comma separator --> e.g. ['a', 'b']. To get all subfields, use keyword 'all'. Use "'subfields' : false" if not applicable.
* item_code: if bool is True, item call number in input file (alternative call number) is not used to select holding but simply added in item.
* cote_generique: this setting allows to add multiple items in a same holding. Characters that match the regex (regular expression https://docs.python.org/3/howto/regex.html) are removed from holding call number but not from alternative call number in item. E.g. : '\\s?\\(\\+[0-9]+\\)$' replace '1234567+(3)' by '1234567', '/[0-9]+$' replace 12234567/3 by 1234567". If no replacement is desired for call number in holding, use empty quotes.
* cote_j: if 2nd call number exists (852 $$j in holding), put True, else False. If 'item_cote' param is True, 1st and 2nd call number must be in item alternative_call_number as well : e.g. 'call number1|call number2'.
* check_duplicates: allows to check whether duplicate barcodes, mmsid or 035 datafield exist in the input file. Set True or False if no value is accepted or not.
* check_bib_match: specifies which type of identifier is used for deduplication (iz_id, nz_id or 035 datafield).
    * id_type : choose between 'iz_id', 'nz_id', '035' or 'empty' if no check needed on existing Alma bib recrod.
    * identifier: identifier is usefull to specify xpath of given tag set in id_type param. Use empty quotes if not necessary. default values are following : iz_id --> 'mms_id', nz_id --> 'mms_id', 035 --> './datafield[@tag='035']/subfield[@code='a']'.
    * multi_prefix: is used to specify different prefixes that id_type might have in Alma, if not necessary use empty quotes". If used, first value must be prefix used in input file. Use pipe as separator '|', e.g. '(TEST)edoc|(TEST)part|(TEST)book'
* sru_search: allows to launch an SRU search if no record is found with check_bib_match param.
    * bool: set True tu use SRU sesarch
    * identifier": allowed values are isbn, issn and standard_number". E.g. "identifier" : ["isbn", "issn", "standard_number"]
    * filter_criteria_and : filter_criteria allows you filter the results of the SRU search. if any of the specified subfields does not meet the following criteria, the record candidate is rejected : (nb_words>5 and nb_words_diff<3) or (nb_words>2 and nb_words_diff<2) or nb_words_diff==0. E.g. with two subfields --> "filter_criteria_and" : ["245|a_b"]
    * filter_criteria_or" : E.g. --> "filter_criteria_or" : ["264|b", "300|a"]. filter_criteria_and and filter_criteria_or can be used together and are then combined with the AND operator.
