from flask import Flask, request, jsonify
import json
from random import choice
from functions import add_help_btn, check_tokens, get_location, get_coords, get_restaurants, \
    rest_ask_btns, get_recipe, reset_smt, get_dates, get_facts, get_holidays, get_ingredients

app = Flask(__name__)
sessionStorage = {}

# TODO: сделать разные варианты ответов на одни и те же вопросы
# TODO: разобраться с интентами, я так понимаю это что-то нужно, хотя толком и не знаю, что это


texts = {"help": ["Задайте мне вопрос \"Где поесть?\", на что я вам скажу где можно перекусить или "
                  "задайте вопрос \"Что мне приготовить\", и я помогу вам подобрать рецепт, "
                  "а можете задать вопрос \"Какой сегодня праздник?\" и я вам расскажу о сегдняшних праздниках, "
                  "хотя вы можете спросить и про то, какие праздники будут в следующие, например, 4 дня.",
                  "Вы можете спросить у меня \"Где мне поесть?\", и я вам отвечу куда вы можете сходить,\n"
                  "Задайте вопрос \"Что приготовить\", на что я расскажу вам какой-нибудь рецепт,\n"
                  "Спросите \"Какой сегодня праздник?\" и я вам скажу о празднике, хотя можете "
                  "спросить и про то, какие праздники будут в следующие, например, 23 дня."],
         "can": [
             "Я умею определять, какой будет праздник в названную вами дату, подсказывать что и как вам приготовить или помогать с выбором ресторана."],
         "bad request": ["Не поняла вас.", "Что?", "Еще раз.", "Не очень понятно..."]}

actions_buttons = [
    {
        "title": "Какой сегодня праздник?",
        "hide": True
    },
    {
        "title": "Что мне приготовить?",
        "hide": True
    },
    {
        "title": "Где мне поесть?",
        "hide": True
    }
]
recipe_btns = [
    {
        "title": "Давай",
        "hide": True
    },
    {
        "title": "Не, другое",
        "hide": True
    }
]


@app.route('/post', methods=['POST'])
def main():
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    user_id = request.json['session']['user_id']
    handle_dialog(response, request.json, user_id)
    sessionStorage[user_id]["last_buttons"] = response["response"].get("buttons", []).copy()
    add_help_btn(response)
    return jsonify(response)


def handle_dialog(res, req, user_id):
    if req['session']['new']:
        sessionStorage[user_id] = {
            "state": None,
            "restaurant": {
                "i": 0,
                "orgs": None,
                "ask_info": False,
                "change_rest": False
            },
            "recipe": {
                "key": None,
                "recipe": None,
                "ask_recipe": False,
                "say_recipe": False,
                "ask_right_recipe": False
            },
            "holiday": {

            }
        }
        res["response"]["text"] = "С добрым утром! Вы хотите узнать какой сегодня праздник, " \
                                  "что приготовить на завтрак или, может, куда сходить поесть?"
        res["response"]["card"] = {"type": "BigImage",
                                   "image_id": "1540737/2ed60101ba34854fddbb",
                                   "title": "С добрым утром! Вы хотите узнать какой сегодня праздник, "
                                            "что приготовить на завтрак или, может, куда сходить поесть?"}
        res["response"]["buttons"] = actions_buttons.copy()
        return
    session = sessionStorage[user_id]
    state = session["state"]
    if check_tokens(["помощь", "помоги"], req):
        res["response"]["text"] = choice(texts["help"])
        btns = session["last_buttons"].copy()
        if actions_buttons[0] not in btns:
            btns.extend(actions_buttons.copy())
        res["response"]["buttons"] = btns
    elif check_tokens(["что"], req) and check_tokens(["умеешь"], req):
        res["response"]["text"] = choice(texts["can"])
        btns = session["last_buttons"].copy()
        if actions_buttons[0] not in btns:
            btns.extend(actions_buttons.copy())
        res["response"]["buttons"] = btns
    elif check_tokens(["какой", "какие", "что", "расскажи", "скажи"], req) and \
            check_tokens(["праздник", "праздники"], req):
        session["state"] = "holiday"
        holiday(res, req, session)
    elif check_tokens(["позавтракать", "поесть", "пообедать", "поужинать", "приготовить"], req) and \
            check_tokens(["что"], req):
        session["state"] = "recipe"
        reset_smt("recipe", session)
        recipe(res, req, session)
    elif check_tokens(["позавтракать", "поесть", "пообедать", "поужинать"], req) and \
            check_tokens(["где", "куда"], req):
        session["state"] = "restaurant"
        reset_smt("restaurant", session)
        restaurant(res, req, session, True)
    elif state:
        if state == "holiday":
            holiday(res, req, session)
        elif state == "recipe":
            recipe(res, req, session)
        else:
            restaurant(res, req, session)
    elif check_tokens(["хватит", "достаточно", "пока"], req):
        res["response"]["text"] = "До встречи!"
        res["response"]["end_session"] = True
    else:
        res["response"]["text"] = choice(texts["bad request"])
        res["response"]["buttons"] = session["last_buttons"]


def holiday(res, req, ses):
    # TODO: проверить функцию
    if check_tokens(["хватит", "достаточно", "нет", "не", "надо"], req):
        ses["state"] = None
        res["response"]["text"] = "Хорошо. Так что вы хотите: узнать еще что-нибудь про " \
                                  "праздники, сходить куда-нибудь или приготовить еду?"
        res["response"]["buttons"] = actions_buttons.copy()
    else:
        holidays = get_holidays(get_dates(req))
        if holidays:
            holidays = '\n'.join(holidays)
            res["response"]["text"] = f"{holidays}!\nПро какую дату вы еще хотите узнать?"
            res['response']['buttons'] = [
                {
                    "title": "Нет",
                    "hide": True
                }
            ]
        else:
            res["response"][
                "text"] = "К сожалению либо в это время нет праздников, либо я таких не знаю, " \
                          "про какую дату вы еще хотите узнать?"


def recipe(res, req, ses):
    # TODO: проверить функцию
    rec = ses["recipe"]
    if not rec["ask_recipe"] and not rec["say_recipe"]:
        rec["key"], rec["recipe"] = get_recipe()
        res["response"][
            "text"] = f"Как вам {rec['key']}?\nРассказать рецепт или подобрать что-нибудь другое?"
        rec["ask_recipe"] = True
        res["response"]["buttons"] = recipe_btns.copy()
    elif rec["ask_recipe"]:
        if check_tokens(["расскажи", "рассказывай", "давай", "этот", "скажи", "сказать"], req) and \
                not check_tokens(["другой", "другое"], req):
            rec["say_recipe"] = True
            rec["ask_recipe"] = False
            recipe(res, req, ses)
        elif check_tokens(["другой", "меняй", "другое"], req):
            rec["ask_recipe"] = False
            recipe(res, req, ses)
        else:
            res["response"]["text"] = choice(texts["bad request"])
            res["response"]["buttons"] = ses["last_buttons"].copy()
    elif rec["say_recipe"] and not rec["ask_right_recipe"]:
        ingr = get_ingredients(rec['recipe'])
        ingredients = "• " + '\n• '.join(ingr[1])

        res["response"]["text"] = f"Ингредиенты {ingr[0]}:\n{ingredients}\nНу что, будете готовить?"
        rec["ask_right_recipe"] = True
        res["response"]["buttons"] = [
            {
                "title": "Открыть рецепт",
                "url": rec['recipe'],
                "hide": True
            },
            {
                "title": "Не, другое",
                "hide": True
            }
        ]
    elif rec["ask_right_recipe"]:
        if check_tokens(["да", "пойдет", "давай", "подходит", "открыть", "рецепт"], req):
            res["response"]["text"] = f"Удачи! А не хотите узнать есть ли сегодня праздник, " \
                                      f"приготовить что-нибудь другое или пойти ресторан? ({rec['recipe']})"
            res["response"]["tts"] = f"Удачи! А не хотите узнать есть ли сегодня праздник, " \
                                     f"приготовить что-нибудь другое или пойти ресторан?"
            reset_smt("recipe", ses)
            ses["state"] = None
            res["response"]["buttons"] = actions_buttons.copy()
        elif check_tokens(["нет", "другое", "меняй"], req):
            rec["ask_recipe"] = False
            rec["say_recipe"] = False
            rec["ask_right_recipe"] = False
            recipe(res, req, ses)
        else:
            res["response"]["text"] = choice(texts["bad request"])
            res["response"]["buttons"] = ses["last_buttons"].copy()
    else:
        res["repsonse"]["text"] = "Что-то пошло не так..."
        # по идее до сюда программа не должна доходить вообще


def restaurant(res, req, ses, first=False):
    # TODO: проверить функцию
    # TODO: сделать возможность узнать геолокацию пользователя, не спрашивая напрямую
    rest = ses["restaurant"]
    try:
        location = get_location(req)
        if not rest["orgs"] and location:
            coords = get_coords(location)
            if coords:
                rest["orgs"] = get_restaurants(coords)
                # пусть координаты пользователя не будут меняться во время взаимодействия
                restaurant(res, req, ses)
        elif not rest["orgs"]:
            res["response"]["text"] = ("" if first else choice(
                texts["bad request"]) + " ") + "А по какому адресу вы сейчас находитесь?"
        elif rest["orgs"] and not rest["ask_info"] and not rest["change_rest"]:
            res["response"]["text"] = f"Вы можете пойти в ресторан " \
                                      f"\"{rest['orgs'][rest['i']]['properties']['CompanyMetaData']['name']}\", находящийся по адресу " \
                                      f"\"{rest['orgs'][rest['i']]['properties']['CompanyMetaData']['address']}\", хотите узнать про него побольше или может хотите пойти в другой ресторан?"
            res["response"]["buttons"] = rest_ask_btns(
                rest['orgs'][rest['i']]['properties']['CompanyMetaData']['url'])
            rest["ask_info"] = True
        elif rest["ask_info"]:
            if check_tokens(["этот", "расскажи", "него", "пойдет", "побольше", "узнать", "давай"],
                            req):
                res["response"][
                    "text"] = f"Желаете сменить ресторан или этот вам нравится? ({rest['orgs'][rest['i']]['properties']['CompanyMetaData']['url']})"
                res["response"]["tts"] = "Желаете сменить ресторан или этот вам нравится?"
                res["response"]["buttons"] = rest_ask_btns()
                rest["change_rest"] = True
                rest["ask_info"] = False
            elif check_tokens(["другой", "меняй"], req):
                rest["ask_info"] = False
                rest["i"] += 1
                restaurant(res, req, ses)
            else:
                res["response"]["text"] = choice(texts["bad request"])
                res["response"]["buttons"] = ses["last_buttons"].copy()
        elif rest["change_rest"]:
            if check_tokens(["меняй", "другой", "желаю", "хочу"], req):
                rest["i"] += 1
                rest["change_rest"] = False
                rest["ask_info"] = False
                restaurant(res, req, ses)
            elif check_tokens(["подходит", "пойдет", "ладно", "этот"], req):
                res["response"]["text"] = "Приятного аппетита! А не хотите узнать есть ли сегодня " \
                                          "праздник, приготовить что-нибудь сами или пойти все-таки " \
                                          "в другой ресторан?"
                res["response"]["buttons"] = actions_buttons.copy()
                ses["state"] = None
                reset_smt("restaurant", ses)
            else:
                res["response"]["text"] = choice(texts["bad request"])
                res["response"]["buttons"] = ses["last_buttons"].copy()
        else:
            res["response"]["text"] = "Что-то пошло не так..."
            # по идее до сюда программа не должна доходить вообще
    except IndexError:
        res["response"]["text"] = "Кажется в вашем районе рестораны закончились, давайте что-то " \
                                  "другое, не хотите узнать какой сегодня прзадник или что " \
                                  "приготовить? "
        btns = actions_buttons.copy()
        btns.pop(2)
        res["response"]["buttons"] = btns


if __name__ == '__main__':
    app.run()
