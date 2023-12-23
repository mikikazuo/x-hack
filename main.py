import random
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse

import pandas as pd
from pandas.errors import EmptyDataError
from selenium import webdriver
from selenium.common import TimeoutException, ElementClickInterceptedException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

#https://twitter.com/account/access　のURLに飛ばされた　BOTチェックで
#取得回数:64 検索ワード：競馬　アウト   取得回数:50

#取得回数 30ぐらいならセーフか？
def init_driver():
    # ツイートが動的読込のためヘッドレスモードは不可
    options = webdriver.ChromeOptions()
    # 絶対パス指定
    login_data_path = r'C:\Users\81809\PycharmProjects\selenium-login\x-hack'
    options.add_argument('--user-data-dir=' + login_data_path)
    return webdriver.Chrome(options=options)


class TempXPath:
    def __init__(self, article):
        self.article = article

    def element_temp(self, value, attribute='class', tag='div'):
        """
        [コツ]find_elementを２連結する場合は、２段階目で１つ下の階層のタグ(div//)を挟むことが必要
        :param value: 属性値
        :param attribute: 属性名
        :param tag タグ名
        :return:
        """
        return self.article.find_element(By.XPATH, f"div//{tag}[@{attribute}='{value}']")

    def element_contain_temp(self, value, attribute='class', tag='div'):
        return self.article.find_element(By.XPATH, f"div//{tag}[contains(@{attribute},'{value}')]")

    def elements_temp(self, value, attribute='class', tag='div'):
        return self.article.find_elements(By.XPATH, f"div//{tag}[@{attribute}='{value}']")

    def elements_contain_temp(self, value, attribute='class', tag='div'):
        return self.article.find_elements(By.XPATH, f"div//{tag}[contains(@{attribute},'{value}')]")


class Data:
    """
    有用そうなスクレイピング情報
    """

    def __init__(self):
        # TODO 検索ワード
        # self.search_word = Bot.search_words
        self.user_name: str | None = None
        self.user_id: str | None = None
        self.tweet_id: str | None = None
        self.is_blue_user = False
        self.user_profile: str | None = None
        self.user_profile_length: int | None = None
        self.interval_from_user_join: int | None = None
        self.user_follow_num: int | None = None
        self.user_follower_num: int | None = None
        self.is_reply = False
        self.text: str | None = None
        self.text_length: int | None = None
        self.text_hashtag_num: int | None = None
        self.img_sum: int | None = None
        self.is_twitter_card = False
        self.is_quote = False
        self.reply_sum: int = 0
        self.retweet_sum: int = 0
        self.nice_sum: int = 0
        self.impression_sum: int = 0
        self.interval_from_action: int | None = None
        # TODO csvへの登録と参照、一定回数越えでアクション対象外にする戦略
        self.action_sum: int = 1
        # TODO 明示・暗黙的な更新
        self.is_follow = False
        self.is_follower = False


class Bot:
    # 検索ワード
    search_words = ['競馬','騎手','イクイノックス','リバティアイランド','競馬', '馬券',
                    '単勝','競馬', '複勝', '馬連', '競馬',
                    '騎手', '馬単', '3連単', '競馬', '3連複', '三連単', '競馬',
                    '三連複', '穴馬', ]
    #search_words = ['ウマ娘','ナイスネイチャ','キタサンブラック','ドウデュース','ジャスティンパレス','プログノーシス','ダノンベルーガ','ログノーシス','ジャックドール']
    # TODO フォローも合わせて行うかどうか、フォロワー比率を高めたいのでなるべく使わない
    follow_mode = False

    # 許容フォロワー最大比率
    user_follower_ratio = 3

    # いいね最大数
    nice_max = 40
    # 累計のいいね回数
    clicked_nice_sum = 0
    # １単語ごとのいいね回数
    clicked_nice_sum_word = 0
    "upload1_1.jpg"

    # csvファイル名
    csv_name = 'user_2.csv'

    def __init__(self):
        self.dt: Data | None = None
        self.driver = init_driver()
        # プロフィール表示用の新しいタブを作成する
        # self.driver.execute_script("window.open()")
        try:
            self.user_list = pd.read_csv(Bot.csv_name, header=None)[0].to_numpy().tolist()
        except EmptyDataError:
            self.user_list = []

    def driver_wait(self, target, value):
        """
        要素表示までの待機
        """
        WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((target, value)))

    def save_csv(self):
        """
        ユーザ名リスト追加 & csv保存
        """
        self.user_list.append(self.dt.user_id)
        pd.Series([self.dt.user_id]).to_csv(Bot.csv_name, mode="a", header=False, index=False)

    def profile_check(self, dt_now):
        """
        フォロー＆フォロワー数の確認、フォロー操作
        :param dt_now: 現時刻
        :return: エラー時にTrue
        """
        # 新しいタブでURLアクセス
        self.driver.get(f'https://twitter.com/{self.dt.user_id}')
        try:
            self.driver_wait(By.XPATH, "//span[@data-testid='UserJoinDate']")
        except TimeoutException:  # 再読み込みボタンが表示されている状態
            print('プロフィールが読み込めないためスキップ')
            return True

        if self.driver.find_elements(By.XPATH, "//div[@data-testid='userFollowIndicator']"):
            print('フォロワーのためスキップ')
            self.dt.is_follower = True
            self.save_csv()
            return True

        def change_unit(text):
            """　単位の統一　"""
            changed_text = text
            for word, unit in {'万': 10000, '億': 100000000}.items():
                if word in text:
                    return int(float(changed_text.replace(word, '')) * unit)
            return int(changed_text.replace(',', ''))

        follow_follower_num = self.driver.find_elements(By.XPATH,
                                                        "//span[@class='css-901oao css-16my406 r-1nao33i r-1tl8opc r-1b43r93 r-b88u0q r-1cwl3u0 r-bcqeeo r-qvutc0']")
        self.dt.user_follow_num = change_unit(follow_follower_num[0].text)
        self.dt.user_follower_num = change_unit(follow_follower_num[1].text)

        if self.dt.user_follow_num == 0 or self.dt.user_follower_num / self.dt.user_follow_num > Bot.user_follower_ratio:
            # print('フォロワー比率が高いためスキップ')
            self.save_csv()
            return True

        # プロフィール記載がない場合は要素が見つからない
        user_profile = self.driver.find_elements(By.XPATH, "//div[@data-testid='UserDescription']")
        if user_profile:
            self.dt.user_profile = user_profile[0].text
            self.dt.user_profile_length = len(self.dt.user_profile.replace('\n', ''))
        else:
            self.dt.user_profile = ''
            self.dt.user_profile_length = 0
        user_join = datetime.strptime(
            self.driver.find_element(By.XPATH, f"//span[@data-testid='UserJoinDate']").text,
            '%Y年%m月からTwitterを利用しています')
        # 月数差分
        self.dt.interval_from_user_join = (dt_now.year - user_join.year) * 12 + dt_now.month - user_join.month
        return False

    def start_scroll(self):
        skip_cnt = -1
        skip_flag = True
        for scroll_idx in range(100):
            dt_now = datetime.utcnow() + timedelta(hours=9)
            # if temp.elements_contain_temp('css-18t94o4 css-1dbjc4n r-l5o3uw r-42olwf r-sdzlij r-1phboty r-rs99b7 r-2yi16'):  # 新しいツイートを読み込めていない
            #     print("API制限中", f'時刻:{dt_now.strftime("%Y/%m/%d %H:%M:%S")}')
            #     raise Exception
            print(f'取得回数:{scroll_idx}')
            # この時点でBOT検証ページに飛ばされてタイムオーバーエラー
            self.driver_wait(By.TAG_NAME, "article")
            skip_cnt = skip_cnt + 1 if skip_flag else 0
            if skip_cnt > 5:
                print("連続スキップ上限オーバー")
                return False
            skip_flag = True
            for article_idx, article in enumerate(self.driver.find_elements(By.XPATH, "//article")):
                try:
                    self.driver.execute_script('arguments[0].scrollIntoView({behavior: "smooth", block: "center"});',
                                               article)
                except:  # 広告が大きすぎるなど
                    print("スクロール範囲外")
                    continue
                temp = TempXPath(article)

                if temp.elements_contain_temp(
                        'css-18t94o4 css-1dbjc4n r-l5o3uw r-42olwf r-sdzlij r-1phboty r-rs99b7 r-2yi16'):  # 新しいツイートを読み込めていない test
                    print("API制限中", f'時刻:{dt_now.strftime("%Y/%m/%d %H:%M:%S")}')
                    raise Exception
                try:
                    # 下部のリアクション数情報、いいね済かどうかの情報も入っている
                    bottom_info_list = temp.element_contain_temp(
                        'css-175oi2r r-1kbdv8c r-18u37iz r-1wtj0ep r-1ye8kvj r-1s2bzr4').get_attribute("aria-label").split('、')
                except:
                    print("謎エラースキップ(bottom_info_list)")
                    continue
                if 'いいね済み' in bottom_info_list:
                    # print("いいね済みスキップ")
                    continue
                try:
                    # 広告を弾くのに利用(広告は投稿時間の記載がない) ＆ その他、ツイートid・ツイート時間情報が入っている
                    multi_info = temp.elements_temp(
                        'css-1rynq56 r-bcqeeo r-qvutc0 r-1tl8opc r-a023e6 r-rjixqe r-16dba41 r-xoduu5 r-1q142lx r-1w6e6rj r-9aw3ui r-3s2u2q r-1loqt21',
                        'class', 'a')
                except StaleElementReferenceException:
                    print("謎エラースキップ(multi_info)")
                    continue
                if not multi_info:
                    continue
                multi_info = multi_info[0]

                self.dt = Data()

                try:
                    text_elements = temp.elements_temp('tweetText', 'data-testid')
                except StaleElementReferenceException:
                    print("謎エラースキップ(text_elements)")
                    continue
                if not text_elements:  # 本文がなく画像だけのパターンもあるため弾く
                    print("本文がなくスキップ")
                    continue
                # 本文
                try:
                    self.dt.text = text_elements[0].text
                except StaleElementReferenceException:
                    print("謎エラースキップ(self.dt.text)")
                    continue
                if search_word not in self.dt.text:  # ユーザ名だけに引っかかるパターンは弾く
                    # print('ユーザ名のみに引っかかったためスキップ')
                    continue
                self.dt.text_length = len(self.dt.text.replace('\n', ''))
                # 本文中のハッシュタグの個数
                self.dt.text_hashtag_num = self.dt.text.count('#')

                try:
                    self.dt.user_name = temp.element_temp('css-1rynq56 r-dnmrzs r-1udh08x r-3s2u2q r-bcqeeo r-qvutc0 r-37j5jr r-a023e6 r-rjixqe r-16dba41 r-18u37iz r-1wvb978').text
                    tweet_url = urlparse(multi_info.get_attribute("href")).path.split('/')
                except StaleElementReferenceException:
                    print("謎エラースキップ(self.dt.user_name)")
                    continue
                self.dt.user_id = tweet_url[1]
                self.dt.tweet_id = tweet_url[-1]

                try:
                    # print(f"ユーザid:{self.dt.user_id}")
                    if temp.elements_temp('css-1dbjc4n r-o52ifk'):  # 新しいツイートを読み込めていない
                        print("API制限中", f'時刻:{dt_now.strftime("%Y/%m/%d %H:%M:%S")}')
                        raise Exception
                except StaleElementReferenceException:
                    print("謎エラースキップ(temp.elements_temp)")
                    continue
                if self.dt.user_id in self.user_list:  # いいねしたことのあるユーザを弾く
                    # print("いいね済みユーザのためスキップ")
                    continue

                # 新しいタブに切り替える　アクセス制限数節約のためコメントアウト
                # self.driver.switch_to.window(self.driver.window_handles[1])
                # if self.profile_check(dt_now):
                #     # 前のタブに切り替え
                #     self.driver.switch_to.window(self.driver.window_handles[0])
                #     continue
                # self.driver.switch_to.window(self.driver.window_handles[0])

                # 引用のマークも含まれてしまっていたのでnot containsで弾いた
                # 最後のsvgタグで取得できなかったため、rect関数で領域をチェック方式にした
                # 引用領域
                quote_class_value = 'css-175oi2r r-adacv r-1udh08x r-1kqtdi0 r-1867qdf r-rs99b7 r-o7ynqc r-6416eg r-1ny4l3l r-1loqt21'
                try:
                    self.dt.is_blue_user = temp.article.find_element(By.XPATH,
                                                                     f"div//a[not(contains(@class,'{quote_class_value}'))]//div[@class='css-1rynq56 r-bcqeeo r-qvutc0 r-1tl8opc r-a023e6 r-rjixqe r-16dba41 r-xoduu5 r-18u37iz r-1q142lx']/span").rect[
                                               'height'] != 0
                except StaleElementReferenceException:
                    print("原因不明のたまに起きるエラーが発生")
                    continue

                self.dt.is_reply = '返信先' in temp.element_temp(
                    'css-175oi2r r-1iusvr4 r-16y2uox r-1777fci r-kzbkwu').text
                if self.dt.is_reply:  # 返信ツイートを弾く
                    # print("返信ツイートのためスキップ")
                    continue

                self.dt.img_sum = len(temp.elements_temp('画像', 'aria-label'))
                self.dt.is_twitter_card = len(
                    temp.elements_temp('css-1dbjc4n r-1igl3o0 r-pm2fo r-zmljjp r-rull8r r-qklmqi r-1adg3ll')) > 0
                self.dt.is_quote = len(temp.elements_temp(quote_class_value)) > 0

                for info in bottom_info_list:
                    info_split = info.split()
                    if '件の返信' in info_split:
                        self.dt.reply_sum = int(info_split[0])
                    elif '件のリツイート' in info_split:
                        self.dt.retweet_sum = int(info_split[0])
                    elif '件のいいね' in info_split:
                        self.dt.nice_sum = int(info_split[0])
                    elif '件の表示' in info_split:
                        self.dt.impression_sum = int(info_split[0])

                # ツイート時間といいねした時間の秒差分取得
                interval_from_action = multi_info.get_attribute("aria-label")
                is_below_hour = False
                if '現在' in interval_from_action:
                    self.dt.interval_from_action = 0
                    is_below_hour = True
                else:
                    # 差分が時間単位以下の場合
                    for word, unit in {'秒': 1, '分': 60, '時間': 3600}.items():
                        if word in interval_from_action:
                            self.dt.interval_from_action = int(interval_from_action.split()[0]) * unit
                            is_below_hour = True
                            break
                # 差分が日数単位の場合
                if not is_below_hour:
                    if '年' not in interval_from_action:
                        interval_from_action = f'{dt_now.year}年{interval_from_action}'
                    self.dt.interval_from_action = int(
                        (dt_now - datetime.strptime(interval_from_action, '%Y年%m月%d日')).total_seconds())

                # いいねクリック操作
                self.driver_wait(By.XPATH, "//div[@data-testid='like']")
                try:
                    temp.element_temp('like', 'data-testid').click()
                except ElementClickInterceptedException:
                    print("プロフィールダイアログが表示されていいねできないためスキップ")
                    continue
                Bot.clicked_nice_sum_word = Bot.clicked_nice_sum_word + 1
                Bot.clicked_nice_sum = Bot.clicked_nice_sum + 1
                time.sleep(random.uniform(3, 6))
                # 削除された場合のクラス名　'css-901oao css-16my406 r-1tl8opc r-bcqeeo r-qvutc0'
                # TODO ここでBOTチェックが入った　エラー　selenium.common.exceptions.StaleElementReferenceException
                if temp.elements_temp('like', 'data-testid'):
                    print("API制限中", f'時刻:{dt_now.strftime("%Y/%m/%d %H:%M:%S")}')
                    raise Exception

                self.save_csv()
                skip_flag = False

            time.sleep(random.uniform(1, 3))
            print(f"いいね総数：{Bot.clicked_nice_sum}")
            if Bot.clicked_nice_sum_word > Bot.nice_max:
                print('いいね数オーバー', f'時刻:{dt_now.strftime("%Y/%m/%d %H:%M:%S")}')
                Bot.clicked_nice_sum_word = 0
                return True


if __name__ == '__main__':
    bot = Bot()
    for search_word in Bot.search_words:
        print(f"検索ワード：{search_word}")
        bot.driver.get(f"https://twitter.com/search?q={search_word}&src=typed_query&f=live")
        if bot.start_scroll():  # 連続スキップ(False)の場合、次の検索ワードに即移行する
            time.sleep(60 * 15)
