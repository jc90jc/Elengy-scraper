import requests
from bs4 import BeautifulSoup
from datetime import datetime
import sqlite3

date_ini = '2022-01-01'
date_end = '2022-12-31'

date_ini = datetime.strptime(date_ini,'%Y-%m-%d') #convert to datetime for easy handle
date_end = datetime.strptime(date_end,'%Y-%m-%d')

finished = False #Boolean to Break when finished scraping through the pages

di = [[]] #to initiate list of lists (inventories&flows), later to .pop() the first '[]'
db = [[]] #to initiate the list of lists (months of berth visits), later to .pop() the first '[]'

for t in range (1,3): #loop through Montoir(1) and Fos(2)
    page=0
    finished= False
    while not finished: #while-loop through the pages, breakpoint is the page with 'No results found' 
        page += 1
        elengy_inputs = [t,page]
        
        elengy_payload = { #variable payload
            'jform[terminal]': str(elengy_inputs[0]),
            'jform[jour1]': str(date_ini.day),
            'jform[mois1]': str(date_ini.month),
            'jform[annee1]': str(date_ini.year),
            'jform[jour2]': str(date_end.day),
            'jform[mois2]': str(date_end.month),
            'jform[annee2]': str(date_end.year),
            'jform[start]': str(elengy_inputs[1]),
            'jform[export]': '0',
            'submit': 'View',
            'option': 'com_transparence',
            'view': 'recherches',
            '7fe7dcd43a68a5ccbd3a9b5d0f17fa7c': '1'
            }
        
        elengy_headers={ #constant headers for the request
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'de-ES,de;q=0.9,en-GB;q=0.8,en;q=0.7,es-CH;q=0.6,es;q=0.5,de-DE;q=0.4,en-US;q=0.3',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Length': '271',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cookie': 'elengy-cookie=!analytics=true; 1948b7c650dda01f145afc6528123287=8qm1i5rjc4vt0kn2fia7jhn4lb',
            'Host': 'www.elengy.com',
            'Origin': 'https://www.elengy.com',
            'Referer': 'https://www.elengy.com/en/clients/operational-management/use-data/recherches.html?article1=&article2=',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Chromium";v="106", "Google Chrome";v="106", "Not;A=Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
            }
        
        #POST, constant Headers and variable Payload
        url = 'https://www.elengy.com/en/clients/operational-management/use-data/recherches.html?article1=92&article2=106'
        response = requests.post(url, headers=elengy_headers, data=elengy_payload)
        soup = BeautifulSoup(response.content, 'html.parser')

        #this part to get the 'last updated' date&time input from source
        if t == 1 and page == 1:
            s_l_upd = soup.find_all('p', {'style': 'text-align: justify;'})
            last_upd_b = datetime.strptime(s_l_upd[0].text.split(' : ')[1], "%d %B %Y").strftime('%Y-%m-%d %H:%M:%S')
            last_upd_i = datetime.strptime(s_l_upd[2].text[8:], "%d %B %Y at %H:%M:%S").strftime('%Y-%m-%d %H:%M:%S')

        #in first loop, berth visits to be scraped

        if t == 1 and page == 1:
            sbs = soup.find_all(['table','h4'], {'style': ['width: 100%;', "text-align: justify; margin-left: 30px;"]})
            for sb in sbs: #loop through the berth h4 & tables (can be 2 or 4 tables, depending on new cal-year's updates)
                if sb.name == 'h4':
                    b_terminal = sb.text #terminal name to DB
                if sb.name == 'table':    
                    [*dbmx] = [ #loop through the month columns: mmm-yy / mmmm-yy, transform to yyyy-mm
                        datetime.strptime(ds.text[:3].title() + ds.text[-3:], "%b-%y").strftime('%Y-%m')
                         for ds in sb.thead.tr.find_all('th')]
                    
                    [*dbux] = [[ #loop through the un- & loadings
                        ds.text
                         for ds in dss.find_all('td')] for dss in sb.tbody.find_all('tr')]
                    for i in range(len(dbmx)):
                        if dbux[0][i] != '':
                            dbx = [[ #temporal berth list, to feed list-of lists
                                dbmx[i],
                                b_terminal,
                                int(dbux[0][i]),
                                int(dbux[1][i]),
                                last_upd_b
                                ]]
                            db.extend(dbx) #temp list to be appended
            db.pop(0) #first empty list of list-of-lists [] to be removed
            hb = ['month', 'terminal', 'unload', 'reload', 'source_last_updated'] #headers (berth visits)

        #if-else to Break in case no more results are given (empty page), else continue
        if soup.find('div', {'id': 'results'}).text.strip() == 'No results found':
            finished= True
        else:
            s = soup.find_all('tbody')[-1] #get the Tbody at the bottom (flux and stocks)

            if t == 1: #terminal name to be later databased
                i_terminal = "Montoir-de-Bretagne"
            else:
                i_terminal = "Fos Tonkin"

            #temp list to add to the list of lists (inventories and regas flows)
            [*dix] = [[
                datetime.strptime(ss.find('td', {'headers': 'jour'}).text,'%d/%m/%Y').strftime('%Y-%m-%d'), #date
                i_terminal,
                int(ss.find('td', {'headers': 'gnl'}).text.replace(" ", "")), #mcm beginning of gas-day
                int(ss.find('td', {'headers': 'nominees'}).text.replace(" ", "")), #kWh nominated
                int(ss.find('td', {'headers': 'allouees'}).text.replace("-", "0").replace(" ", "")), #kWh allocated
                last_upd_i #last updated
                ] for ss in s.find_all('tr')] #loop through the rows

            di.extend(dix) #temp list to be appended
di.pop(0) #first empty list of list-of-lists to be removed
hi = ['date', 'terminal', 'mcm_0', 'kWh_nominated', 'kWh_allocated', 'source_last_updated'] #headers (inventories and regas flows)

#database
dbname = 'lng.sqlite'
conn = sqlite3.connect(dbname) #DB connection and tables creation
table_creation_b= "CREATE TABLE IF NOT EXISTS berths (month text, terminal text, unload integer , reload integer , source_last_updated datetime)"
table_creation_i= "CREATE TABLE IF NOT EXISTS regas (date date, terminal text, mcm_0 integer, kWh_nominated integer, kWh_allocated integer, source_last_updated datetime)"
conn.execute(table_creation_b)
conn.commit()
conn.execute(table_creation_i)
conn.commit()

#insert into instructions
insert_b = "INSERT INTO berths (month, terminal, unload, reload, source_last_updated) VALUES (?, ?, ?, ?, ?)"
insert_i = "INSERT INTO regas (date, terminal, mcm_0, kWh_nominated, kWh_allocated, source_last_updated) VALUES (?, ?, ?, ?, ?, ?)"
 
#loop through list of lists to insert in DB
for i in range(len(di)):
    arguments_i = (di[i][0],di[i][1],di[i][2],di[i][3],di[i][4],di[i][5])
    conn.execute(insert_i, arguments_i)
    conn.commit()

for i in range(len(db)):
    arguments_b = (db[i][0],db[i][1],db[i][2],db[i][3],db[i][4])
    conn.execute(insert_b, arguments_b)
    conn.commit()
