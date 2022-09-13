import requests
import json

cellphone = '141689313'
message = 'hey alvin'
apiUrl = "http://1suppliesterminal.api.genvoice.net"
apiKey = "53f88bc22a4ca1613ddcd1568b4fff02"
number = ""

try:
    # https://api.genvoice.net/docs/#api-SMS-SendSMSwithoutFrom
    url = apiUrl + '/api/sms/send'
    if number != "":
        url = url + "/" + number
    url = url + "/" + cellphone

    print url 
    data = {'text': message, 'sign': 'ST'}
    
    headers = {'Content-type': 'application/json', 'x-app-key': apiKey}
    
    r = requests.post(url, data=json.dumps(data), headers=headers)

    print r
    print r.status_code
    if r.status_code == 200:
        print(r)
    else:
        print 'SMS failed.'
except Exception as e:
    print e
    print e.args[0]
