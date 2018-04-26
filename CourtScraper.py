import os
import re
import csv
import time
import random
import requests
from bs4 import BeautifulSoup as bs

"""CourtScraper.py - a python script for crawling, collecting, processing and exporting to csv UK court listings"""

__author__ = 'Ronald Greeff'
__credits__ = "Pavements, for keeping me off the streets"
__license__ = "GPL"
__version__ = "1.0.1"
__email__ = "ron@donrondadon.com"
__status__ = "Production"


############################################################################################
### EXTRACT THE NECESSARY DATA FROM COLLECTED DICTIONARIES AND READY IT FOR WRITE TO CSV ###
############################################################################################

def remove_matched_line(regx_match, a_list):
    """removes a regex match from a list of address lines (usually a line containing a colon)"""

    return [i for i in a_list if not re.match(regx_match, i)]

def list2line(a_list):
    """ Takes in a list of items and converts them into a comma seperated list, so that in CSV they're stored as CS-strings"""

    try:
        return ','.join(a_list)
    except:
        return None

def standardise_dict_data_output(dictionary):
    """Takes the collected information (as a dictionary), checks *if* an element present in the dict, and if so, extracts relevant data which is then standardised and returned for writing to CSV

    Dictionary example: 
    {
        'url': u'https://courttribunalfinder.service.gov.uk//courts/aberystwyth-justice-centre', 
        'pros': {
            u'Crown Court location code': u'3253', 
            u'DX': u'99560 Aberystwyth 2', 
            u'County Court location code': u'102'
        }, 
        'court': u'Aberystwyth Justice Centre', 
        'contact:': {
            'telephone - Enquiries:': u'01970 621 250', 
            'email - County Court:': u'enquiries@aberystwyth.countycourt.gsi.gov.uk'
        }, 
        'address': [
            {
                u'visiting': {
                u'addressLocality': u'Aberystwyth', u'addressRegion': u'Ceredigion', u'streetAddress': [u'Aberystwyth Justice Centre', u'Y Lanfa', u'Trefechan'], u'postalCode': u'SY23 1AS'
                }
            }
        ]
    }
    """

    #################################
    ### CSV fields to be written  ###
    #################################

    court_name = None
    crown_court_id = None
    county_court_id = None
    addresses = None
    telephone = []
    email = []


    ##################
    ### Court name ###
    ##################

    court_name = dictionary['court']


    ###################
    ### Court Codes ###
    ###################

    if dictionary.get('pros'):
        crown_court_id = dictionary.get('pros').get('Crown Court location code')
        county_court_id = dictionary.get('pros').get('County Court location code')


    #################
    ### Addresses ###
    #################

    addresses = {}
    #   >   {u'postal': {'street_address': u'The Glasgow Tribunals Centre\n20 York Street\nGlasgow\nG2 8GT'}, u'visiting': {'town': u'Ayr', 'region': u'Ayrshire', 'street_address': u'Russell House\nKing Street'}}

    if dictionary.get('address'):
        """     address is a list:
        [{u'visiting': {u'addressLocality': u'Bury St Edmunds', u'addressRegion': u'Suffolk', u'streetAddress': [u'Triton House', u"St Andrew's Street North"], u'postalCode': u'IP33 1TR'}}, 
        {u'postal': [u'Civil and family enquiries:', u'Norwich Combined Court', u'The Law Courts', u'Bishop Gate', u'Norwich', u'Norfolk', u'NR3 1UR']}]
        """

        #   for however many dict.items() in address dict
        for i in range(len(dictionary['address'])):

            #   grab the dict.items() for i
            address_item = (dictionary['address'])[i]
            #   i=0 >   {u'visiting': {u'addressLocality': u'Ayr', u'addressRegion': u'Ayrshire', u'streetAddress': [u'Russell House', u'King Street'], u'postalCode': u'KA8 0BD'}}
            #   i=1 >   {u'postal': [u'The Glasgow Tribunals Centre', u'20 York Street', u'Glasgow', u'G2 8GT']}

            #   grab the values for address_item(i) (either a list of a dict)
            deter_address_type = address_item.values()[0]
            #   i=0 >   {u'addressLocality': u'Ayr', u'addressRegion': u'Ayrshire', u'streetAddress': [u'Russell House', u'King Street'], u'postalCode': u'KA8 0BD'}
            #   i=1 >   [u'The Glasgow Tribunals Centre', u'20 York Street', u'Glasgow', u'G2 8GT']


            #   if item is a dictionary, extract the relevant info required for CSV
            if type(deter_address_type) == type(dict()):
 
                addresses[(address_item.keys()[0])] = {

                    "town" : address_item.values()[0].get('addressLocality'), 
                    "region" : address_item.values()[0].get('addressRegion'), 
                    "street_address" : ("\n".join(address_item.values()[0].get('streetAddress')))

                    }

            #   if item is a list, remove newlines, unecessary spaces and colons, then assign that Value to street_address Key
            if type(deter_address_type) == type(list()):

                addresses[(address_item.keys()[0])] = {

                    "street_address" : ("\n".join(remove_matched_line('.*:.*', address_item.values()[0])))

                    }
    else:
        pass


    #####################
    ### Phone & Email ###
    #####################

    if dictionary.get('contact:'):
        # {'telephone - Enquiries:': u'01296 434 401', 'email - Enquiries:': u'enquiries@aylesbury.crowncourt.gsi.gov.uk', 'telephone - Fax:': u'01264 785079', 'email - Listing:': u'listing@aylesbury.crowncourt.gsi.gov.uk'}

        contact = dictionary['contact:']
        tele_enq = contact.get('telephone - Enquiries:')
        email_enq = contact.get('email - Enquiries:')

        ###########
        ## Phone ##
        ###########

        # if there's an enquiries telephone number, grab it, else pass
        if type(tele_enq) == type(list()):
            [telephone.append(tele_enq[0]) if tele_enq else telephone.append(None) for i in tele_enq]
        else:
            [telephone.append(tele_enq) if tele_enq else telephone.append(None)]

        ###########
        ## Email ##
        ###########

        #   if there's a key == "enquiries email address"
        if email_enq:

            #   >   [u'rcjbankclccdjhearings@hmcts.gsi.gov.uk', u'rcjcompgenclcc@hmcts.gsi.gov.uk']
            if type(email_enq) == type(list()):

                # append [email] where email address does not contain 'solicitor'
                [email.append(i) for i in email_enq if not re.findall('solicitor', i)]

            #   >   enquiries@aylesbury.crowncourt.gsi.gov.uk
            else:
                # skip email addresses that contain "solicitor"
                if not re.findall('solicitor', email_enq):
                    [email.append(contact['email - Enquiries:'])]

                else:
                    [email.append(None)]

        #   if there's no key "enquiries email address"
        elif not email_enq:
            for i in range(len(contact)):

                #   if it's a list, line = item in string
                if type(contact.values()[i]) == type(list()):
                    for x in range(len(contact.values()[i])):
                        line = contact.values()[i][x]

                #   if it's a string, line = the string
                else: 
                    line = contact.values()[i]

                if not re.findall('solicitor', line):
                    if re.match('.*enq.*', line):
                        m = re.match('.*enq.*', line)
                        email.append(m.group(0))

        else:
            email.append(None)

        # Convert lists to comma seperated strings
        email = list2line(email)
        telephone = list2line(telephone)

    else:
        pass

    return court_name, crown_court_id, county_court_id, telephone, email, addresses

def check_val(add_type, get_val):
    """encode dictionary "Address" values to UTF-8"""

    try:
        if addresses[add_type]:
            return (addresses[add_type].get(get_val)).encode('utf-8')
    except:
        val = None

    return val



#######################################
### PROCESS ADDRESSES BASED ON TYPE ###
#######################################

def process_flat_address(chunk):
    """         Takes a chunk of flat, multi-lined text (with multiple blank lines in between), removes new-lines and strips blank spaces, then gives you a beautiful list representing each line in the address
    ---------------
            1st Floor

            Piccadilly Exchange

            Piccadilly Plaza

          Manchester                            --->                            [u'1st Floor', u'Piccadilly Exchange', u'Piccadilly Plaza', u'Manchester', u'Greater Manchester', u'M1 4AH']


            Greater Manchester

          M1 4AH

    Maps and Direction
    """

    #         strip trailing spaces from text lines containing newlines <- extract texty bits / leave empty spaces <- remove "Maps and Direction" from chunk
    return [i.strip() if re.search(re.compile(".*\\n\s+$"), i) else i.strip() for i in (re.findall("\S+\s.*", (re.sub("[mM]aps\s+[a-zA-Z].*", "", chunk))))]

def process_span_address(addr_block):
    """         Takes a block of HTML with multiple tags like <span property="SomeProperty">SomeText</span> and gives you a beatiful dictionary like {SomeProperty : SomeText}, where SomeText is converted to a list if == streetAddress
    ---------------
    [<span property="streetAddress">\n            \n              Aberystwyth Justice Centre <br/>\n            \n              Y Lanfa<br/>\n            \n              Trefechan<br/>\n</span>, <span property="addressLocality">Aberystwyth</span>, <span property="addressRegion">Ceredigion</span>, <span property="postalCode">SY23 1AS</span>]
    --->
    {u'addressLocality': u'Aberystwyth', u'addressRegion': u'Ceredigion', u'streetAddress': [u'Aberystwyth Justice Centre', u'Y Lanfa', u'Trefechan'], u'postalCode': u'SY23 1AS'}
    """

    #                       Process each line and create a dict in the form of {attrs : text} for each span tag
    return {(span.attrs.values())[0] : process_single_and_multi_line_address(span.text) for span in addr_block}

def process_single_and_multi_line_address(address_string):
    """         Takes in both multi-lined and single lined text data and returns the multi-lined data as list, otherwise returns a string
    ----------------


                  Aberystwyth Justice Centre
                                                                                    ['Aberystwyth Justice Centre', 'Y Lanfa', 'Trefechan']
                  Y Lanfa                            --->                            ----------------
                                                                                    Aberystwyth
                  Trefechan

    ----------------
    Aberystwyth
    ----------------
    """

    #       stip from everything that isn't a blankline                 <-  if it's multiline                                <- strip single line text
    return [item.strip() for item in re.findall("\S+\s.*", address_string)] if re.search(re.compile("\\n"), address_string) else address_string.strip()



###############################################################################
### COLLECT EVERYTHING CONTAINED WITH THE ADDRESS, CONTACT AND CODES BLOCKS ###
###############################################################################

def extract_court_details(full_link):
    """         Takes in a link of a court pages and dynamically creates dictionaries out of the items available in the form of { html attribute : corresponding data }:

        "addresses":
    [{u'visiting': {u'addressLocality': u'Ayr', u'addressRegion': u'Ayrshire', u'streetAddress': [u'Russell House', u'King Street'], u'postalCode': u'KA8 0BD'}}, {u'postal': [u'The Glasgow Tribunals Centre', u'20 York Street', u'Glasgow', u'G2 8GT']}]

        "contact_details":
    {'email - Employment tribunal:': u'aberdeenet@justice.gov.uk', 'telephone - Employment tribunal:': u'01224 593  137', 'email - Social security and child support:': u'sscsa-glasgow@justice.gov.uk', 'telephone - Fax:': u'0870 761 7766', 'telephone - Social security and child support:': u'0300 790 6234'}

        "pros" (codes):
    {u'DX': u'44457 Strand'}
    {u'Crown Court location code': u'401'}
    """

    #   Main chunk of content containing Addresses, Contacts and Codes
    content_block = (soup(full_link)).find('div', {'class': 'content inner cf court'})

    #   Address-containing chunk
    address_block = content_block.find('div', {'id': 'addresses'})

    #   Contact-containing chunk
    contact_block = content_block.find('div', {'id': 'contacts'})


    #########################
    ##  Process Addresses  ##
    #########################

    #   List of addresses, as there may be "Visiting" and "Postal" (which could be in the span format or flat-text format)
    addresses = []

    #   Collect all the items, skipping "pros" for now
    for item in address_block.find_all('div', attrs={'id': lambda x: x !='pros'}):


        #   Create a dictionary for each type of address, { address type : address data }
        processed_span_address = {}
        processed_flat_address = {}

        #   Is it a span address?
        if item.find('span'):
            span_address = item.find_all('span')
            # return each span address as a dict of keys (attributes) and values (text)
            address_dictionary = process_span_address(span_address)
            span_addr = {item['id']: address_dictionary}
            processed_span_address.update(span_addr)

        #   Is it a flat address?
        else:
            flat_address = ''.join(text for text in item(text=True) if text.parent.name !="h2")
            # return each flat address as a list, split by address line
            address_list = process_flat_address(flat_address)
            flat_addr = {item['id']: address_list}
            processed_flat_address.update(flat_addr)


        #   Add each address-type dictionary to the list of addresses
        if processed_span_address:
            addresses.append(processed_span_address)
        elif processed_flat_address:
            addresses.append(processed_flat_address)
        else:
            pass


    #############################
    ##  Process Pros / Codes   ##
    #############################

    pros = {}

    if address_block.find('div', attrs={'id': 'pros'}):
        dl = address_block.find('div', attrs={'id': 'pros'})
        pros = dict(zip([(remove_colon(x.text)) for x in dl.find_all('dt')], [(remove_colon(y.text)) for y in dl.find_all('dd')]))


    #########################
    ##  Process Contacts   ##
    #########################

    #   Collect div elements excluding spacers
    contact_divs = contact_block.find_all('div', attrs={'class': lambda x: x !='spacer'})

    contact_category = []
    #   example:    [u'email', u'telephone', u'telephone', u'telephone', u'telephone', u'telephone', u'telephone', u'telephone', u'telephone']
    contact_category_keys = []
    #   example:    [u'', u'Enquiries:', u'Registry:', u'Associates:', u'Case progression (A):(Phones will only be answered between 10am-12pm and 2pm-4pm)', u'Case progression (B):(Phones will only be answered between 10am-12pm and 2pm-4pm)', u'Case progression (C):(Phones will only be answered between 10am-12pm and 2pm-4pm)', u'Listing:', u'Disabled access:']
    contact_category_values = []
    #   example:    [u'civilappeals.registry@hmcts.gsi.gov.ukcivilappeals.cmsa@hmcts.gsi.gov.ukcivilappeals.cmsb@hmcts.gsi.gov.ukcivilappeals.cmsc@hmcts.gsi.gov.ukcivilappeals.listing@hmcts.gsi.gov.ukcivilappeals.associates@hmcts.gsi.gov.uk', u'020 7947 6916', u'020 7947 7121', u'020 7947 6879', u'020 7947 6139', u'020 7947 7828', u'020 7947 6096', u'020 7947 6195', u'020 7073 4831020 7947 6915']


    for block in contact_divs:
        """     block:
        ...
        <span class="label-pad" property="contactType" typeof="ContactPoint">Enquiries:</span>                                                                  <- contact_category_keys
        <div class="email-addresses">
        <a href="mailto:birmingham.enquiries@birmingham.crowncourt.gsi.gov.uk" property="email">birmingham.enquiries@birmingham.crowncourt.gsi.gov.uk</a>       <- contact_category, contact_category_values
        </div>
        <div class="phone-number">
        <a href="tel:0121  681 3300" property="telephone">0121  681 3300</a><br/>                                                                               <- contact_category, contact_category_values
        <a href="tel:0121 681 3339" property="telephone">0121 681 3339</a>
        </div>
        ...
        """

        #   Get contact_category_keys
        if not block.find('a'):
            dkeys = re.sub("\\n", "", block.text.strip())
            contact_category_keys.append(dkeys)

        #   If more than one, get list of contact_category_values == 'email'
        elif len(block.find_all('a', {'property' : 'email'})) > 1:

            contact_category.append(block.a.attrs['property'])

            multi_emails = []
            multi_emails_found = block.find_all('a', {'property' : 'email'})

            for i in multi_emails_found:
                multi_emails.append(i.text)

            contact_category_values.append(multi_emails)

        #   If more than one, get list of contact_category_values == 'telephone'
        elif len(block.find_all('a', {'property' : 'telephone'})) > 1:

            contact_category.append(block.a.attrs['property'])

            multi_telephones = []
            multi_telephones_found = block.find_all('a', {'property' : 'telephone'})

            for i in multi_telephones_found:
                multi_telephones.append(i.text)

            contact_category_values.append(multi_telephones)

        #   If just one item
        else:
            contact_category.append(block.a.attrs['property'])
            dvalues = re.sub("\\n", "", block.text.strip())
            contact_category_values.append(dvalues)

    #   Concatenate category with keys, e.g. "email - Enquiries", "telephone - Enquiries"
    keys = ["{} - {}".format(b_,a_) for a_, b_ in zip(contact_category_keys, contact_category)]

    #   zip keys with corresponding values into a dictionary
    contact_details = dict(zip(keys, contact_category_values))

    return addresses, contact_details, pros



##################################
### EXTRACT COURT NAME AND URL ###
##################################

def get_courts(base, buff, char):
    """Works through A-Z of courts Index pages and returns the Court Name and URL link to Court Address page"""

    url = base + buff + str(chr(char))

    links = (soup(url)).find('div', {'class', 'content inner cf'}).find('ul')

    name_link_dict = {}

    for item in links.find_all('a', href=True):

        if len(item.string) > 1:
            court_link = item['href']
            court_name = item.string

            court_detail_url = base + court_link

            name_link_dict[court_name] = court_detail_url

    return name_link_dict
    """     Outbound "name_link_dict":
    {u'Agricultural Land and Drainage - First-tier Tribunal (Property Chamber) ': u'https://courttribunalfinder.service.gov.uk//courts/first-tier-tribunal-property-chamber-agricultural-land-and-drainage', u'Ashford Tribunal Hearing Centre': u'https://courttribunalfinder.service.gov.uk//courts/ashford-tribunal-hearing-centre', u'Administrative Court': u'https://courttribunalfinder.service.gov.uk//courts/administrative-court', u'Admiralty and Commercial Court': u'https://courttribunalfinder.service.gov.uk//courts/admiralty-and-commercial-court', u'Amersham Law Courts': u'https://courttribunalfinder.service.gov.uk//courts/amersham-law-courts', u'Ayr Social Security and Child Support Tribunal': u'https://courttribunalfinder.service.gov.uk//courts/ayr-social-security-and-child-support-tribunal', u'Aylesbury Crown Court': u'https://courttribunalfinder.service.gov.uk//courts/aylesbury-crown-court', u'Aberystwyth Justice Centre': u'https://courttribunalfinder.service.gov.uk//courts/aberystwyth-justice-centre', u'Aldershot Justice Centre': u'https://courttribunalfinder.service.gov.uk//courts/aldershot-magistrates-court', u'Avon and Somerset Central Accounts Department': u'https://courttribunalfinder.service.gov.uk//courts/avon-and-somerset-central-accounts-department', u'Aberdeen Tribunal Hearing Centre': u'https://courttribunalfinder.service.gov.uk//courts/aberdeen-employment-tribunal'}
    """



#############################
### PRIMARY SCRIPT / FLOW ###
#############################

def soup(url): return bs((requests.get(url)).text, "html.parser")

def remove_colon(string): return re.sub(":", "", string)

if __name__ == "__main__":

    BASE = 'https://courttribunalfinder.service.gov.uk/'
    BUFF = 'courts/'

    count_total = 0

    #   Start writing to CSV, starting with the headers
    with open('dictwrite.csv', 'ab') as f:
        writer = csv.DictWriter(
            f, 
            fieldnames = ['court name', 'crown court id', 'county court id', 'telephone', 'email', 'visiting - street address', 'visiting - town', 'visiting - region', 'postal - street address', 'postal - town', 'postal - region']
            )

        try:
            writer.writeheader()

            # chr(65 - 91) == ord(A - Z)
            for i in range(65, 91):

                count_set = 0

                #   name_link_dict: {court_name : court_address_link}
                name_link_dict = get_courts(BASE, BUFF, i)

                for court_name, court_detail_url in name_link_dict.iteritems():

                    #   from each of the name_link_dicts, visit page and get address, contact_details and pros (identifiers)
                    addresses, contact_details, pros = extract_court_details(court_detail_url)

                    #   build a comprehensive dictionary out of the elements collected
                    details_dict = {"court" : court_name, "url" : court_detail_url, "address" : addresses, "contact:" : contact_details, "pros" : pros}
                    #print(details_dict)

                    #   standardise the structure of the collected elements ready to be written to csv
                    court_name, crown_court_id, county_court_id, telephone, email, addresses = standardise_dict_data_output(details_dict)

                    writer.writerow(
                        {
                                'court name' : court_name, 
                                'crown court id' : crown_court_id, 
                                'county court id' : county_court_id,                                 
                                'telephone' : telephone, 
                                'email' : email, 

                                'visiting - street address' : check_val('visiting', 'street_address'),
                                'visiting - town' : check_val('visiting', 'town'),
                                'visiting - region' : check_val('visiting', 'region'),
                                'postal - street address' : check_val('postal', 'street_address'),
                                'postal - town' : check_val('postal', 'town'),
                                'postal - region' : check_val('postal', 'region')
                        }
                    )

                    print("-_-_-_-_-_-_-_-_-_-_Total: {}:{}: {}".format(count_total, count_set, court_name))

                    time.sleep(random.uniform(0.1, 1.0))
                    count_total, count_set = count_total + 1, count_set + 1

                i += 1

        except csv.Error as e:
            sys.exit('file %s, line %d: %s' % (fieldname, reader.line_num, e))
