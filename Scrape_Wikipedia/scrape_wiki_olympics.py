import pandas as pd
from lxml import html
import requests
import os.path
import urllib.parse


root = 'https://en.wikipedia.org'

# ===== ITERATIONSMETHODEN =====

# Iteriert ueber alle Olympiaden
def scrape_olympics(sport_frame):
    page = requests.get('https://en.wikipedia.org/wiki/Category:Competitors_at_the_2016_Summer_Olympics')
    tree = html.fromstring(page.content)
    olympics_relative = tree.xpath('//td/a/@href')
    olympics_year = tree.xpath('//td/a/text()')

    # Bereinigung: letzter Eintrag ist Fehler, dafuer muss 2016-link hinzugefuegt werden
    olympics_relative.pop()
    olympics_year.pop()
    olympics_relative.append('/wiki/Category:Competitors_at_the_2016_Summer_Olympics')

    # gibt index und olympiaden aus
    for i in range (0, len(olympics_year)):
        print(str(i) + " " + str(olympics_year[i]))

    # sucht nach Sportarten für alle Olympiaden
#    for i in range(0,len(olympics_relative))

    # durchsucht nur 2016er Olympiade
    for i in range(27, 28):
        url = add_root(olympics_relative[i])
        year=olympics_year[i]
        print(url)
        print(year)
        scrape_sports(url, year, sport_frame)

# Iteriert ueber alle Sportarten einer bestimmten Olympiade
def scrape_sports(url, year, sport_frame):
    print("SCRAPE SPORTS")
    page = requests.get(url)
    tree = html.fromstring(page.content)
    sports_relative = tree.xpath('//a[@class="CategoryTreeLabel  CategoryTreeLabelNs14 CategoryTreeLabelCategory"]/@href')
    sports_text = tree.xpath('//a[@class="CategoryTreeLabel  CategoryTreeLabelNs14 CategoryTreeLabelCategory"]/text()')

    # gibt alle Sportarten einer Olympiade aus
    for i in range(0, len(sports_relative)):
        print(str(i) + " " + sports_text[i])

    # sucht nach Sportler_innen in einer Sportart einer Olympiade
    for i in range(0, len(sports_relative)):
        sport_url = add_root(sports_relative[i])
        text = sports_text[i]
        sport = text[:text.find("at the")-1]
        print(sport_url)
        print(sport)
        scrape_athletes(sport_url, year, sport, sport_frame)


# Iteriert ueber alle Sportler_innen einer bestimmten Sportart in einer Olympiade
def scrape_athletes(url, year, sport, sport_frame):
    print("SCRAPE ATHLETES")
    page = requests.get(url)
    tree = html.fromstring(page.content)
    athletes_relative = tree.xpath('//a/@href')
    names_x = tree.xpath('//a/text()')
    titles_x = tree.xpath('//li/a/@title')
    sub = tree.xpath('//h2/text()')

    # angleichen von names, titles, urls
    scraped = analyze_athletes(names_x, titles_x, athletes_relative)
    titles = scraped[0]
    names = scraped[1]
    urls = scraped[2]
    next = scraped[3]

    # durchnummerierte Konsolen-Ausgabe der Sportler_innen
    for i in range(0,len(titles)):
        print(str(i)+" "+titles[i]+" "+names[i]+" "+urls[i])
    print("Next: "+next)

    get_values(titles,names,urls,sport,year,sport_frame)

    # falls die anzahl der sportler_innen hoeher ist als die auf einer seite angezeigten 200
    if next:
        scrape_athletes(next, year, sport, sport_frame)
    if 'Subcategories' in sub:
        scrape_sports(url,year,sport_frame)

# bestimmt Werte fuer jede_n Sportler_in einer Sportart und fuegt sie Dataframe hinzu bzw. csv
def get_values(titles, names, urls, sport, year, sport_frame):
    for i in range(0, len(titles)):
        url = add_root(urls[i])
        name = names[i]
        title = titles[i]
        content = get_content(url)
        # genderbestimmung
        gender = get_gender(content)
        # Counts
        wordcount = count_words(reduce_string(content))
        editcount = count_edits(title)
        linkcount = count_links(url)

        married = is_married(reduce_string(content))

        # Zusammenfassung in Series und hinzufügen zum Dataframe
        s = pd.Series(
            {'WikiSport': sport, 'WikiYear': year, 'WikiGender': gender, 'Wordcount': wordcount, 'Editcount': editcount,
             'Linkcount': linkcount, 'Married': married, 'WikiName': name, 'WikiTitle': title, "WikiURL": url})
        print(s)
        sport_frame = sport_frame.append(s, ignore_index='True')

    # Anhaengen an CSV-Datei
    file = 'wikilympics'+str(year)+'.csv'
    if os.path.exists(file):
        sport_frame.to_csv(file, mode='a', header=False)
    else:
        sport_frame.to_csv(file, mode='a', header=True)




# gleicht ggf listen von urls, titles, names an und loescht falsche links
def analyze_athletes(names, titles, urls):
    firsttitle = 0
    firstname = 0
    firsturl = 0
    next = ""

    # loescht ggf den ersten titel, der kein name ist
    for i in range(0,len(titles)):
        if titles[i].find("at the")==-1:
            firsttitle = i
            break
    titles = titles[firsttitle:]

    # findet den ersten titel in namen-liste
    for j in range(0,len(names)):
        if names[j] == titles[0]:
            firstname = j
            break

    # findet den ersten titel in url-liste
    namesplit = titles[0].split(" ")
    print(namesplit)
    if len(namesplit[0]) == 1:
        namesplit.pop(0)
    # url-encodiert den namen
    name = urllib.parse.quote(namesplit[0])
    print(name)
    for l in range(0, len(names)):
        if urls[l].find(name) > -1: # or urls[l].find(namesplit[1])>-1:
            if urls[l].find("at_the") == -1:
                print(urls[l])
                firsturl = l
                break

    # prueft, ob es eine nextpage gibt, weil es mehr als 200 sportler_innen gibt
    for h in range(0, len(names)):
        if names[h] == "next page":
            next = add_root(urls[h-firsturl+firstname])
            break

    # kuerzt alle nicht titel
    names = names[firstname:]
    urls = urls[firsturl:]

    # findet den ersten titel, der kein titel mehr ist und kuerzt entsprechend nach hinten
    lasttitle = len(titles)
    for k in range(0,len(titles)):
        if names[k] != titles[k]:
            lasttitle = k
            break
    titles = titles [:lasttitle]
    names = names [:lasttitle]
    urls = urls[:lasttitle]

    return [titles, names, urls, next]



# ===== HILFSMETHODEN =====

# entfernt umbrueche etc aus String
def reduce_string(string):
    return string.replace('\n', ' ').replace('\r', '').replace("==", "").replace("=", "")


# fuegt ggf bei relativen links root hinzu
def add_root(url):
    if url[1]=='w':
        url=root+url
    elif url[1]=='/':
        url='https:'+url
    return url


# wordcount
def count_words(string):
    counter = 0
    saw_space = False
    for char in string:
        if char == " ":
            if not saw_space:
                counter += 1
            saw_space = True
        else:
            saw_space = False
    return counter


# zaehlt die Edits, fast jeder Edit hat im span-tag zwei Links
def count_edits(title):
    history = 'https://en.wikipedia.org/w/index.php?title='+title+'&offset=&limit=500&action=history'
    page = requests.get(history)
    tree = html.fromstring(page.content)
    edits = tree.xpath('//li/span[@class="mw-history-histlinks"]/a/@href')
    return (len(edits)//2) + 1

# holt sich alles, was zwischen p-tags liegt -> nochmal pruefen, ob dadurch nicht sachen verloren gehen
def get_content(url):
    page = requests.get(url)
    tree = html.fromstring(page.content)
    contents = tree.xpath('//p/text()')
    linktexts = tree.xpath('//p/a/text()')
    content = ''
    for c in contents:
        content += " "+c
    for l in linktexts:
        content += " " + l
    # print("CONTENT: "+content)
    # print("REDUCED: "+reduce_string(content))
    return content

# anzahl links im content zwischen p-tags
def count_links(url):
    page = requests.get(url)
    tree = html.fromstring(page.content)
    linktexts = tree.xpath('//p/a/text()')
    return len(linktexts)


# bestimmt gender aus textanalyse
def get_gender(content):
    c = content.lower()
    gender = '0'
    m_count = c.count(" he ") + c.count(" his ") + c.count(" men")
    f_count = c.count(" she ") + c.count(" her ") + c.count(" women") + c.count(" ladies")
    if m_count>f_count:
        gender = 'm'
    elif f_count > m_count:
        gender = 'f'
    return gender

def is_married(content):
    married = False
    c = content.lower()
    if c.find("married") > -1 or c.find("husband") > -1 or c.find("wife") > -1:
        married = True
    return married



# ===== MAIN =====

# Anlegen des Dataframes und speichern der Spaltenbezeichnungen
sport_frame = pd.DataFrame(columns=['Sport', 'Year', 'Gender', 'Wordcount', 'Editcount', 'Linkcount', 'Married', 'Name', 'Title', 'URL'])
sport_frame = sport_frame[['Sport', 'Year', 'Gender', 'Wordcount', 'Editcount', 'Linkcount', 'Married', 'Name', 'Title', 'URL']]

scrape_olympics(sport_frame)


