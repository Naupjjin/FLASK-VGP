import requests as req

s = req.Session()

s.get('http://lotuxctf.com:20001/r3que57s_ch4ll3nge')
print(s.post('http://lotuxctf.com:20001/r3que57s_ch4ll3nge').text)