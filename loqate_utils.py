import json
import urllib
from urllib.parse import urlencode
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


fieldsformat = {'field93format': 'MPAN18', 'field67format': 'GasMeterSerial13', 'field109format': 'MPANTopLine12',
                'field66format': 'GasMeterSerial12', 'field146format': 'MPRN9', 'field77format': 'GasMeterSerial3',
                'field10format': 'ElectricMeterSerial18', 'field27format': 'ElectricMeterType15',
                'field85format': 'MPAN10', 'field95format': 'MPAN1', 'field61format': 'GSPID7',
                'field97format': 'MPAN2', 'field74format': 'GasMeterSerial1', 'field137format': 'MPRN1',
                'field138format': 'MPRN20', 'field106format': 'MPANPostcode', 'field45format': 'GSPID11',
                'field33format': 'ElectricMeterType20', 'field125format': 'MPANTopLine8', 'field135format': 'MPRN18',
                'field6format': 'ElectricMeterSerial14', 'field103format': 'MPAN8', 'field99format': 'MPAN4',
                'field50format': 'GSPID16', 'field148format': 'MPRNPostcode', 'field81format': 'GasMeterSerial7',
                'field57format': 'GSPID3', 'field34format': 'ElectricMeterType2', 'field101format': 'MPAN6',
                'field129format': 'MPRN12', 'field100format': 'MPAN5', 'field128format': 'MPRN11',
                'field91format': 'MPAN16', 'field151format': 'UMRRN', 'field42format': 'EnergyUseOnly',
                'field18format': 'ElectricMeterSerial6', 'field9format': 'ElectricMeterSerial17',
                'field88format': 'MPAN13', 'field115format': 'MPANTopLine18', 'field116format': 'MPANTopLine19',
                'field30format': 'ElectricMeterType18', 'field2format': 'ElectricMeterSerial10',
                'field96format': 'MPAN20', 'field145format': 'MPRN8', 'field132format': 'MPRN15',
                'field21format': 'ElectricMeterSerial9', 'field8format': 'ElectricMeterSerial16',
                'field15format': 'ElectricMeterSerial3', 'field38format': 'ElectricMeterType6',
                'field56format': 'GSPID2', 'field112format': 'MPANTopLine15', 'field5format': 'ElectricMeterSerial13',
                'field133format': 'MPRN16', 'field126format': 'MPANTopLine9', 'field110format': 'MPANTopLine13',
                'field4format': 'ElectricMeterSerial12', 'field104format': 'MPAN9', 'field65format': 'GasMeterSerial11',
                'field39format': 'ElectricMeterType7', 'field59format': 'GSPID5', 'field127format': 'MPRN10',
                'field92format': 'MPAN17', 'field46format': 'GSPID12', 'field62format': 'GSPID8',
                'field75format': 'GasMeterSerial20', 'field3format': 'ElectricMeterSerial11',
                'field122format': 'MPANTopLine5', 'field119format': 'MPANTopLine2', 'field150format': 'UDPRN',
                'field87format': 'MPAN12', 'field78format': 'GasMeterSerial4', 'field70format': 'GasMeterSerial16',
                'field71format': 'GasMeterSerial17', 'field144format': 'MPRN7', 'field14format': 'ElectricMeterSerial2',
                'field41format': 'ElectricMeterType9', 'field51format': 'GSPID17',
                'field25format': 'ElectricMeterType13', 'field40format': 'ElectricMeterType8',
                'field11format': 'ElectricMeterSerial19', 'field76format': 'GasMeterSerial2',
                'field48format': 'GSPID14', 'field58format': 'GSPID4', 'field47format': 'GSPID13',
                'field130format': 'MPRN13', 'field12format': 'ElectricMeterSerial1',
                'field36format': 'ElectricMeterType4', 'field124format': 'MPANTopLine7',
                'field28format': 'ElectricMeterType16', 'field63format': 'GSPID9',
                'field19format': 'ElectricMeterSerial7', 'field105format': 'MPANCount',
                'field26format': 'ElectricMeterType14', 'field120format': 'MPANTopLine3', 'field139format': 'MPRN2',
                'field83format': 'GasMeterSerial9', 'field113format': 'MPANTopLine16', 'field102format': 'MPAN7',
                'field98format': 'MPAN3', 'field108format': 'MPANTopLine11', 'field55format': 'GSPID20',
                'field20format': 'ElectricMeterSerial8', 'field22format': 'ElectricMeterType10',
                'field94format': 'MPAN19', 'field142format': 'MPRN5', 'field35format': 'ElectricMeterType3',
                'field131format': 'MPRN14', 'field29format': 'ElectricMeterType17', 'field80format': 'GasMeterSerial6',
                'field52format': 'GSPID18', 'field64format': 'GasMeterSerial10', 'field32format': 'ElectricMeterType1',
                'field53format': 'GSPID19', 'field7format': 'ElectricMeterSerial15', 'field143format': 'MPRN6',
                'field49format': 'GSPID15', 'field147format': 'MPRNCount', 'field121format': 'MPANTopLine4',
                'field118format': 'MPANTopLine20', 'field86format': 'MPAN11', 'field54format': 'GSPID1',
                'field84format': 'LargeGasUser', 'field68format': 'GasMeterSerial14', 'field107format': 'MPANTopLine10',
                'field73format': 'GasMeterSerial19', 'field69format': 'GasMeterSerial15',
                'field111format': 'MPANTopLine14', 'field24format': 'ElectricMeterType12',
                'field31format': 'ElectricMeterType19', 'field136format': 'MPRN19', 'field140format': 'MPRN3',
                'field90format': 'MPAN15', 'field114format': 'MPANTopLine17', 'field43format': 'FuelFlag',
                'field13format': 'ElectricMeterSerial20', 'field1format': 'DeliveryPointSuffix',
                'field134format': 'MPRN17', 'field60format': 'GSPID6', 'field149format': 'ParentUDPRN',
                'field44format': 'GSPID10', 'field23format': 'ElectricMeterType11',
                'field37format': 'ElectricMeterType5', 'field123format': 'MPANTopLine6',
                'field79format': 'GasMeterSerial5', 'field89format': 'MPAN14', 'field117format': 'MPANTopLine1',
                'field141format': 'MPRN4', 'field16format': 'ElectricMeterSerial4',
                'field17format': 'ElectricMeterSerial5', 'field82format': 'GasMeterSerial8',
                'field72format': 'GasMeterSerial18'
                }


def capture_interactive_find_v1_10(key, text, ismiddleware=True, container=False, origin=False,
                                   countries=False, limit=False, language=False):

    # Build the url
    requestUrl = "https://api.addressy.com/Capture/Interactive/Find/v1.10/json3.ws?"
    requestUrl += "&" + urlencode({"Key": key})
    requestUrl += "&" + urlencode({"Text": text})
    requestUrl += "&" + urlencode({"IsMiddleware": ismiddleware})
    if container:
        requestUrl += "&" + urlencode({"Container": container})
    if origin:
        requestUrl += "&" + urlencode({"Origin": origin})
    if countries:
        requestUrl += "&" + urlencode({"Countries": countries})
    if limit:
        requestUrl += "&" + urlencode({"Limit": limit})
    if language:
        requestUrl += "&" + urlencode({"Language": language})
    # Get the data
    # data = urllib.urlopen(requestUrl).read()
    http = urllib3.PoolManager()
    print ('---create url requested::>>>', requestUrl)
    read_url = http.request('POST', requestUrl)
    print ('--printed hhtp request ::>>>', read_url)
    JSON_object = json.loads(read_url.data.decode('utf-8'))
    print ('--print json object ::>>>>', JSON_object)
    return JSON_object['Items']


def capture_interactive_retrieve_v1_00(Key, Id):

    # Build the url
    requestUrl = "https://api.addressy.com/Capture/Interactive/Retrieve/v1.00/json3.ws?"
    requestUrl += "&" + urlencode({"Key": Key})
    requestUrl += "&" + urlencode({"Id": Id})
    requestUrl += "&" + urlencode({"Fields": 151})
    for key, val in fieldsformat.items():
        requestUrl += "&" + urlencode({key: '{'+val+'}'})
    http = urllib3.PoolManager()
    print ('--printed requested url ::>>>', requestUrl)
    read_url = http.request('POST', requestUrl)
    print ('---read url printed ::>>>>', read_url)
    JSON_object = json.loads(read_url.data.decode('utf-8'))
    print ('--printed json object :::>>>>>', JSON_object)
    return JSON_object['Items']
