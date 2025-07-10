from flask import Flask, request, render_template, url_for
import requests
import os
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("RIOT_API_KEY")

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

posts = []

@app.route('/')
def index():
    return render_template("index.html")


@app.route('/community')
def community():
    return render_template('community.html', posts=posts)


@app.route('/write', methods=['GET', 'POST'])
def write():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        author = request.form.get('author', '익명')
        posts.append({'title': title, 'content': content, 'author': author})
        return render_template('success.html')
    return render_template('write.html')


VERSION = "14.13.1"
BASE_URL = f"http://ddragon.leagueoflegends.com/cdn/{VERSION}"

# 챔피언 및 스펠 데이터 불러오기
champ_data = requests.get(f"{BASE_URL}/data/ko_KR/champion.json").json()["data"]
spell_data = requests.get(f"{BASE_URL}/data/ko_KR/summoner.json").json()["data"]

champ_key_map = {v["key"]: k for k, v in champ_data.items()}
champ_name_kr = {v["key"]: v["name"] for k, v in champ_data.items()}
spell_key_map = {v["key"]: k for k, v in spell_data.items()}


def get_account_by_riot_id(game_name, tag_line):
    url = f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{quote(game_name)}/{quote(tag_line)}"
    headers = {"X-Riot-Token": API_KEY}
    return requests.get(url, headers=headers).json()


def get_match_ids_by_puuid(puuid, count=10):
    url = f"https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count={count}"
    headers = {"X-Riot-Token": API_KEY}
    return requests.get(url, headers=headers).json()


def get_match_detail(match_id):
    url = f"https://asia.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": API_KEY}
    return requests.get(url, headers=headers).json()


@app.route('/result')
def result():
    riot_id = request.args.get("summonername")
    count = int(request.args.get("count", 5))

    if not riot_id or "#" not in riot_id:
        return "Riot ID 형식으로 입력해주세요 (예: Hide on bush#KR1)", 400

    game_name, tag_line = riot_id.split("#")
    account_info = get_account_by_riot_id(game_name.strip(), tag_line.strip())

    if "puuid" not in account_info:
        return f"{riot_id} 계정을 찾을 수 없습니다", 404

    puuid = account_info["puuid"]
    match_ids = get_match_ids_by_puuid(puuid, count)

    match_data = []
    for match_id in match_ids:
        detail = get_match_detail(match_id)

        participants = detail["metadata"]["participants"]
        if puuid not in participants:
            continue

        idx = participants.index(puuid)
        p = detail["info"]["participants"][idx]

        champ_id = str(p["championId"])
        spell1 = str(p["summoner1Id"])
        spell2 = str(p["summoner2Id"])

        # 아이템 이미지 리스트 생성 (0은 생략)
        item_list = []
        for i in range(6):
            item_id = p.get(f'item{i}', 0)
            if item_id != 0:
                item_list.append({"img": f"{BASE_URL}/img/item/{item_id}.png"})

        match_data.append({
            "champion": champ_name_kr.get(champ_id, "Unknown"),
            "champion_img": f"{BASE_URL}/img/champion/{champ_key_map.get(champ_id, 'Unknown')}.png",
            "spells": [
                {"name": spell_key_map.get(spell1, "Unknown"), "img": f"{BASE_URL}/img/spell/{spell_key_map.get(spell1, '')}.png"},
                {"name": spell_key_map.get(spell2, "Unknown"), "img": f"{BASE_URL}/img/spell/{spell_key_map.get(spell2, '')}.png"}
            ],
            "KDA": f"{p['kills']} / {p['deaths']} / {p['assists']}",
            "win": p["win"],
            "item_list": item_list
        })

    return render_template("result.html",
                           summoner_name=riot_id,
                           matches=match_data)


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
