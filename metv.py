import os
import re
import json
import requests
import concurrent.futures
from datetime import datetime
import traceback

# --- LİG BİLGİLERİ ---
super_lig_sezonlar = {
    32: '2010/2011', 30: '2011/2012', 25: '2012/2013',
    34: '2013/2014', 37: '2014/2015', 24: '2015/2016',
    29: '2016/2017', 23: '2017/2018', 20: '2018/2019',
    994: '2019/2020', 3189: '2020/2021', 3308: '2021/2022',
    3438: '2022/2023', 3580: '2023/2024', 3746: '2024/2025',
    3853: '2025/2026', 
}
super_lig_haftalar = {
    32: range(1, 35), 30: range(1, 35), 25: range(1, 35),
    34: range(1, 35), 37: range(1, 35), 24: range(1, 35),
    29: range(1, 35), 23: range(1, 35), 20: range(1, 35),
    994: range(1, 35), 3189: range(1, 43), 3308: range(1, 39),
    3438: range(1, 39), 3580: range(1, 39), 3746: range(1, 39),
    3853: range(1, 39),
}
super_lig_st = {key: 0 for key in super_lig_sezonlar.keys()}

# --- TFF 1. LİG URL ÇEKME ---
def get_birinci_lig_urls_dynamically():
    page_url = "https://www.beinsports.com.tr/mac-ozetleri-goller/tff-1-lig"
    urls_to_fetch = []
    try:
        response = requests.get(page_url, timeout=20, headers={
            'User-Agent': 'Mozilla/5.0'
        })
        response.raise_for_status()
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', response.text, re.DOTALL)
        if not match: return []
        data = json.loads(match.group(1))
        highlights_data = data.get("props", {}).get("pageProps", {}).get("initialReduxState", {}).get("highlights", {}).get("data", [])
        if not highlights_data: return []

        league_info = highlights_data[0]
        seasons = league_info.get("seasons", [])

        for season in seasons:
            season_name = season.get("name")
            season_id = season.get("id")
            rounds = season.get("rounds", [])
            group_title = f"TFF 1. Lig {season_name}"
            for round_info in rounds:
                round_number = round_info.get("round")
                st_code = round_info.get("st", 0)
                if season_id and round_number:
                    url = f"https://beinsports.com.tr/api/highlights/events?sp=1&o=130&s={season_id}&r={round_number}&st={st_code}"
                    urls_to_fetch.append((url, group_title))
        return urls_to_fetch
    except Exception as e:
        print("TFF 1. Lig veri hatası:", e)
        return []

# --- VERİ ÇEKME VE M3U OLUŞTURMA ---
def fetch_and_parse(url_info):
    url, group_title = url_info
    try:
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        data = response.json()
        events = data.get('Data', {}).get('events', [])
        result = []
        for event in events:
            home = event.get('homeTeam', {}).get('name', 'Ev Sahibi')
            home_score = event.get('homeTeam', {}).get('matchScore', '-')
            away = event.get('awayTeam', {}).get('name', 'Deplasman')
            away_score = event.get('awayTeam', {}).get('matchScore', '-')
            video_url = event.get('highlightVideoUrl')
            logo = event.get('highlightThumbnail', '')
            match_id = event.get('matchId', '')
            if video_url:
                title = f"{home} {home_score}-{away_score} {away}"
                line1 = f'#EXTINF:-1 tvg-id="{match_id}" tvg-logo="{logo}" group-title="{group_title}",{title}\n'
                line2 = f"{video_url}\n"
                result.append((group_title, line1, line2))
        return result
    except Exception as e:
        print(f"Hata URL: {url} - {e}")
        return []

def main():
    output_folder = 'metv'
    os.makedirs(output_folder, exist_ok=True)

    all_urls_to_fetch = []

    # Süper Lig
    for sezon_id, sezon_adi in super_lig_sezonlar.items():
        haftalar = super_lig_haftalar.get(sezon_id, range(1, 39))
        st = super_lig_st.get(sezon_id, 0)
        group_title = f"Süper Lig {sezon_adi}"
        for hafta in haftalar:
            url = f"https://beinsports.com.tr/api/highlights/events?sp=1&o=18&s={sezon_id}&r={hafta}&st={st}"
            all_urls_to_fetch.append((url, group_title))

    # TFF 1. Lig
    all_urls_to_fetch.extend(get_birinci_lig_urls_dynamically())

    grouped_results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_results = executor.map(fetch_and_parse, all_urls_to_fetch)
        for result_list in future_results:
            for group_title, line1, line2 in result_list:
                grouped_results.setdefault(group_title, []).append((line1, line2))

    all_lines_combined = []
    for group_title, lines in sorted(grouped_results.items()):
        safe_folder_name = group_title.replace('/', '-').replace(' ', '_')
        folder_path = os.path.join(output_folder, safe_folder_name)
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, f"{safe_folder_name}.m3u")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n\n")
            for line1, line2 in lines:
                f.write(line1)
                f.write(line2)
                all_lines_combined.append((line1, line2))

    # Master M3U
    all_m3u_path = os.path.join(output_folder, 'all_leagues.m3u')
    with open(all_m3u_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n\n")
        for line1, line2 in all_lines_combined:
            f.write(line1)
            f.write(line2)

if __name__ == "__main__":
    main()
