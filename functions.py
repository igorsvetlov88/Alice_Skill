import requests
import datetime
from bs4 import BeautifulSoup as bs
from random import randint, choice
import sqlite3


def add_help_btn(res):
    if "buttons" in res["response"]:
        res["response"]["buttons"].append(
            {
                "title": "Помощь",
                "hide": True
            }
        )
    else:
        res["response"]["buttons"] = [
            {
                "title": "Помощь",
                "hide": True
            }
        ]


def check_tokens(words, req):
    return any([word in req["request"]["nlu"]["tokens"] for word in words])


def get_location(req):
    location = {}
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.GEO':
            for key in set(entity['value'].keys()):
                if key not in location:
                    location[key] = entity["value"][key].title()
    # именно так, чтобы не было в адресе сразу два города или две улицы, то есть,
    # чтобы адреса были более реалистичными
    return ", ".join(list(location.values()))


def get_coords(address):
    response = requests.get("https://geocode-maps.yandex.ru/1.x/", {
        'geocode': address,
        'format': 'json',
        'apikey': "40d1649f-0493-4b70-98ba-98533de7710b"
    })
    try:
        return response.json()["response"]["GeoObjectCollection"]["featureMember"][0][
            "GeoObject"]["Point"]["pos"].replace(" ", ",")
    except (IndexError, KeyError):
        return None


def get_restaurants(coords):
    if coords is None:
        return None
    response = requests.get("https://search-maps.yandex.ru/v1/", {
        "apikey": "dda3ddba-c9ea-4ead-9010-f43fbc15c6e3",
        "text": "ресторан",
        "lang": "ru_RU",
        "ll": coords,
        "type": "biz"
    })
    org = response.json()["features"]
    return org


def rest_ask_btns(url=None):
    return [
        ({
             "title": choice(["Давай этот", "Пойдет"]),
             "hide": True
         }
         if not url else
         {
             "title": choice(["Давай этот", "Пойдет"]),
             "hide": True,
             "url": url
         }),
        {
            "title": choice(["Не, другой надо", "Другой"]),
            "hide": True
        },
        {
            "title": "Хватит",
            "hide": True
        }
    ]


def reset_smt(what, session):
    if what == "holiday":
        pass
    elif what == "recipe":
        session["recipe"]["key"] = None
        session["recipe"]["recipe"] = None
        session["recipe"]["ask_recipe"] = False
        session["recipe"]["say_recipe"] = False
        session["recipe"]["ask_right_recipe"] = False
    elif what == "restaurant":
        session["restaurant"]["i"] = 0
        session["restaurant"]["ask_info"] = False
        session["restaurant"]["change_rest"] = False


def get_recipe():
    url = 'https://www.russianfood.com/recipes/bytype/?fid=926&page='
    req = requests.get(url + str(randint(1, 44)))
    result = bs(req.content, "html.parser")
    title = result.select(".title_o > .title > a")
    variant = choice(title)
    return variant.text, 'https://www.russianfood.com' + variant.get('href')


def get_ingredients(url_recepie):
    req = requests.get(url_recepie)
    result = bs(req.content, "html.parser")
    ingredients = result.select('.ingr > tr > td > span')
    col_portions = ingredients[1].text.replace('(', '').replace(')', '')
    if 'на' in col_portions and 'порции' in col_portions:
        start = 2
    else:
        col_portions = ''
        start = 1
    for x in range(start, len(ingredients)):
        ingredients[x] = ingredients[x].text
    return col_portions, ingredients[2::]


def get_holidays(dates):  # dates - список дат по типу: ["08.03", "09.03", "10.03"]
    con = sqlite3.connect('holidays.sqlite')
    cur = con.cursor()
    hols = []
    now_lenght = 98
    for d in dates:
        try:
            dat = cur.execute("""SELECT definition FROM days WHERE definition=?""", d).fetchone()[0]
            if len(dat) + now_lenght < 1024:
                hols.append(dat)
                now_lenght += len(dat)
            else:
                break
        except Exception as error:
            print('error')

    return hols


def get_facts(date):  # date - дата, например, "08.03"
    # TODO: написать функцию
    return "пока не сделано"


def get_dates(req):
    command = req['request']['command']
    for symb in '.&?,!;:':
        command = command.replace(symb, '')
    dates = []
    if 'сегодня' in command:
        dates.append(datetime.datetime.now().strftime('%d.%m'))
    elif 'завтра' in command:
        dates.append((datetime.datetime.today() + datetime.timedelta(days=1)).strftime('%d.%m'))
    elif 'следующие' in command or 'следующих' in command:
        srez = command.split(' ')
        for key in ['следующие', 'следующих']:
            if key in command:
                i = srez.index(key)
                break
        try:
            delta_days = int(srez[i - 1])
        except ValueError:
            delta_days = int(srez[i + 1])
        for x in range(0, delta_days + 1):
            dates.append((datetime.datetime.today() + datetime.timedelta(days=x)).strftime('%d.%m'))
    else:
        months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа',
                  'сентября', 'октября', 'ноября', 'декабря']
        ans = []
        for month in months:
            if month in command:
                srez = command.split()
                ans.append(months.index(month) + 1)
                i = srez.index(month)
        try:
            ans.append(int(srez[i - 1]))
        except ValueError:
            if len(srez) > i + 1:
                ans.append(int(srez[i + 1]))
            else:
                return []
        except UnboundLocalError:
            return []

        if ans[0] < 10:
            ans[0] = '0' + str(ans[0])
        else:
            ans[0] = str(ans[0])
        if ans[1] < 10:
            ans[1] = '0' + str(ans[1])
        else:
            ans[1] = str(ans[1])
        dates.append('.'.join(ans[::-1]))
    return list(dates)
