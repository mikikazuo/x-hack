import random
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse

import pandas as pd
from pandas.errors import EmptyDataError
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def init_driver():
    # ヘッドレスモードは不可
    options = webdriver.ChromeOptions()
    login_data_path = r'C:\Users\boost\Documents\SourceTreePrivate\selenium-login\User Data'
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

    def elements_temp(self, value, attribute='class', tag='div'):
        return self.article.find_elements(By.XPATH, f"div//{tag}[@{attribute}='{value}']")


class Data:
    """
    有用そうなスクレイピング情報
    """

    def __init__(self):
        self.search_word: str | None = None
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
    search_word = '競馬'
    # TODO フォローも合わせて行うかどうか、フォロワー比率を高めたいのでなるべく使わない
    follow_mode = False

    # 許容フォロワー最大比率
    user_follower_ratio = 3

    # いいね最大数
    nice_max = 50
    clicked_nice_sum = 0

    # csvファイル名
    csv_name = 'user.csv'

    def __init__(self):
        self.dt = None
        self.driver = init_driver()
        # プロフィール表示用の新しいタブを作成する
        self.driver.execute_script("window.open()")
        self.driver.get(f"https://twitter.com/search?q={Bot.search_word}&src=typed_query&f=live")
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
        pd.Series([self.dt.user_id]).to_csv('user.csv', mode="a", header=False, index=False)

    def profile_check(self, dt_now):
        """
        TODO フォロワー比率に応じて弾く戦略
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
            print('フォロワー比率が高いためスキップ')
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
        for scroll_idx in range(100):
            dt_now = datetime.utcnow() + timedelta(hours=9)
            print(f'取得回数:{scroll_idx}', f'時刻:{dt_now.strftime("%Y/%m/%d %H:%M:%S")}')
            self.driver_wait(By.TAG_NAME, "article")
            for article_idx, article in enumerate(self.driver.find_elements(By.XPATH, "//article")):
                try:
                    self.driver.execute_script('arguments[0].scrollIntoView({behavior: "smooth", block: "center"});',
                                               article)
                except:  # 広告が大きすぎるなど
                    print("スクロール範囲外")
                    continue
                temp = TempXPath(article)
                # 下部のリアクション数情報、いいね済かどうかの情報も入っている
                bottom_info_list = temp.element_temp(
                    'css-1dbjc4n r-1kbdv8c r-18u37iz r-1wtj0ep r-1s2bzr4 r-hzcoqn').get_attribute("aria-label").split(
                    '、')
                if 'いいね済み' in bottom_info_list:
                    continue
                # 広告を弾くのに利用(広告は投稿時間の記載がない) ＆ その他、ツイートid・ツイート時間情報が入っている
                multi_info = temp.elements_temp(
                    'css-4rbku5 css-18t94o4 css-901oao r-1bwzh9t r-1loqt21 r-xoduu5 r-1q142lx r-1w6e6rj r-1tl8opc r-a023e6 r-16dba41 r-9aw3ui r-rjixqe r-bcqeeo r-3s2u2q r-qvutc0',
                    'class', 'a')
                if not multi_info:
                    continue
                multi_info = multi_info[0]

                self.dt = Data()
                self.dt.search_word = Bot.search_word

                text_elements = temp.elements_temp(
                    'css-901oao r-1nao33i r-37j5jr r-a023e6 r-16dba41 r-rjixqe r-bcqeeo r-bnwqim r-qvutc0')
                if not text_elements:  # 本文がなく画像だけのパターンもあるため弾く
                    continue
                # 本文
                self.dt.text = text_elements[0].text
                if Bot.search_word not in self.dt.text:  # ユーザ名だけに引っかかるパターンは弾く
                    continue
                self.dt.text_length = len(self.dt.text.replace('\n', ''))
                # 本文中のハッシュタグの個数
                self.dt.text_hashtag_num = self.dt.text.count('#')

                self.dt.user_name = temp.element_temp('css-1dbjc4n r-1awozwy r-18u37iz r-1wbh5a2 r-dnmrzs').text
                tweet_url = urlparse(multi_info.get_attribute("href")).path.split('/')
                self.dt.user_id = tweet_url[1]
                self.dt.tweet_id = tweet_url[-1]

                print(f"===== ユーザid:{self.dt.user_id} =====")
                if self.dt.user_id in self.user_list:  # いいねしたことのあるユーザを弾く
                    continue

                # 新しいタブに切り替える
                self.driver.switch_to.window(self.driver.window_handles[1])
                if self.profile_check(dt_now):
                    # 前のタブに切り替え
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    continue
                self.driver.switch_to.window(self.driver.window_handles[0])

                # 引用のマークも含まれてしまっていたのでnot containsで弾いた
                # 最後のsvgタグで取得できなかったため、rect関数で領域をチェック方式にした
                quote_class_value = 'css-1dbjc4n r-1kqtdi0 r-1867qdf r-rs99b7 r-1loqt21 r-adacv r-1ny4l3l r-1udh08x r-o7ynqc r-6416eg'
                self.dt.is_blue_user = temp.article.find_element(By.XPATH,
                                                                 f"div//a[not(contains(@class,'{quote_class_value}'))]//div[@class='css-901oao r-1nao33i r-xoduu5 r-18u37iz r-1q142lx r-1tl8opc r-a023e6 r-16dba41 r-rjixqe r-bcqeeo r-qvutc0']/span").rect[
                                           'height'] != 0

                self.dt.is_reply = '返信先' in temp.element_temp(
                    'css-1dbjc4n r-1iusvr4 r-16y2uox r-1777fci r-kzbkwu').text

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
                temp.element_temp('like', 'data-testid').click()
                Bot.clicked_nice_sum = Bot.clicked_nice_sum + 1
                time.sleep(random.uniform(1, 2))
                if temp.elements_temp('like', 'data-testid'):
                    print("API制限中")
                    raise Exception

                self.save_csv()
            time.sleep(random.uniform(1, 3))
            print(f"いいね総数：{Bot.clicked_nice_sum}")
            if Bot.clicked_nice_sum > Bot.nice_max:
                print('いいね数オーバー')
                break


if __name__ == '__main__':
    bot = Bot()
    bot.start_scroll()
