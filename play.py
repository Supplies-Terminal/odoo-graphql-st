import requests
import json

cellphone = '14168931320'
message = 'hey alvin'
apiUrl = "http://suppliesterminal.api.genvoice.net"
apiKey = "53f88bc22a4ca1613ddcd1568b4fff02"
apiNumber = False

try:
    # https://api.genvoice.net/docs/#api-SMS-SendSMSwithoutFrom
    url = '{}{}'.format(apiUrl, '/api/sms/send')
    if !apiNumber:
        url = "{}/{}".format(url, apiNumber)
    url = "{}/{}".format(url, cellphone)

    print(url)
    data = {'text': message, 'sign': 'ST'}
    print(data)
    headers = {'Content-type': 'application/json', 'x-app-key': apiKey}
    
    r = requests.post(url, data=json.dumps(data), headers=headers)

    print r
    print r.status_code
    if r.status_code == 200:
        print("successed")
    else:
        print 'failed.'
except Exception as e:
    print e
    print e.args[0]
