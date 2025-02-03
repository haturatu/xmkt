#!/usr/bin/python3
import os
import httpx
import asyncio
import logging
from urllib.parse import urlparse
from twikit import Client
from dotenv import load_dotenv
from datetime import datetime, timedelta

# .envファイルから環境変数を読み込み
load_dotenv()

# logging設定
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('twitter_media_downloader.log'),
        logging.StreamHandler()
    ]
)

class SecureTwitterMediaDownloader:
    def __init__(self):
        # 環境変数から認証情報を取得
        self.username = os.getenv('TWITTER_USERNAME')
        self.email = os.getenv('TWITTER_EMAIL')
        self.password = os.getenv('TWITTER_PASSWORD')
        
        # 保存先とリトライ設定
        self.save_base_folder = os.getenv('SAVE_BASE_FOLDER', '/your/default/dir')
        self.retry_limit = int(os.getenv('RETRY_LIMIT', 5))
        self.retry_delay = int(os.getenv('RETRY_DELAY', 900))
        
        # クッキーファイルのパス
        self.cookie_path = 'twitter_cookies.json'
        
        # Twikitクライアントの初期化
        self.client = Client('en-US')

    def load_usernames(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                return [line.strip() for line in file if line.strip()]
        except FileNotFoundError:
            logging.error(f"ユーザー名ファイル {filename} が見つかりません。")
            return []

    async def authenticate(self):
        try:
            # クッキーファイルの存在と有効性を確認
            if os.path.exists(self.cookie_path):
                cookie_age = datetime.fromtimestamp(os.path.getmtime(self.cookie_path))
                
                # クッキーが7日以内に作成された場合
                if datetime.now() - cookie_age < timedelta(days=7):
                    logging.info("既存のクッキーを使用します。")
                    try:
                        self.client.load_cookies(self.cookie_path)
                        return True
                    except Exception as cookie_error:
                        logging.warning(f"クッキーの読み込みに失敗: {cookie_error}")
            
            # 有効なクッキーがない場合は資格情報でログイン
            logging.info("資格情報を使用してログインします。")
            await self.client.login(
                auth_info_1=self.username,
                auth_info_2=self.email,
                password=self.password
            )
            
            # 新しいクッキーを保存
            self.client.save_cookies(self.cookie_path)
            return True
        
        except Exception as e:
            logging.error(f"認証に失敗しました: {e}")
            return False

    async def download_image(self, url, save_path):
        # 画像をダウンロード
        if os.path.exists(save_path):
            logging.info(f"画像は既に存在します: {save_path}")
            return True

        for attempt in range(self.retry_limit):
            try:
                async with httpx.AsyncClient() as async_client:
                    response = await async_client.get(
                        url, 
                        timeout=httpx.Timeout(10.0, connect=5.0),
                        follow_redirects=True
                    )
                    response.raise_for_status()
                    
                    # ディレクトリが存在することを確認
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    
                    with open(save_path, 'wb') as file:
                        file.write(response.content)
                    
                    logging.info(f"画像を保存: {save_path}")
                    return True
            
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                logging.warning(f"ダウンロード試行 {attempt + 1} に失敗: {e}")
                
                if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 404:
                    logging.info(f"画像が見つかりません (404): {url}")
                    return False
                
                if attempt < self.retry_limit - 1:
                    await asyncio.sleep(self.retry_delay)
        
        logging.error(f"{url} のダウンロードに {self.retry_limit} 回失敗しました")
        return False

    async def process_user_media(self, screen_name):
        try:
            user = await self.client.get_user_by_screen_name(screen_name)
            save_folder = os.path.join(self.save_base_folder, "media", screen_name)
            
            media_tweets = await self.safe_fetch_tweets(user, 'Media')
            if not media_tweets:
                return
            
            error_count = 0
            while media_tweets:
                for tweet in media_tweets:
                    if not tweet.media:
                        continue
                    
                    for media in tweet.media:
                        url = media.get('media_url_https')
                        if url:
                            url = url.replace('.jpg', '?format=jpg&name=orig')
                            filename = f"{screen_name}_{url.split('/')[-1]}.jpeg"
                            save_path = os.path.join(save_folder, filename)
                            await self.download_image(url, save_path)
                
                try:
                    media_tweets = await media_tweets.next()
                except Exception as e:
                    logging.error(f"次のツイートの取得エラー: {e}")
                    error_count += 1
                    if error_count >= 3:
                        logging.warning(f"{screen_name} のエラーが閾値を超えました")
                        break
        
        except Exception as e:
            logging.error(f"{screen_name} の処理中にエラー: {e}")

    async def safe_fetch_tweets(self, user, tweet_type):
        # ツイートを取得
        for attempt in range(self.retry_limit):
            try:
                return await user.get_tweets(tweet_type)
            except Exception as e:
                logging.warning(f"ツイート取得試行 {attempt + 1} に失敗: {e}")
                if attempt < self.retry_limit - 1:
                    await asyncio.sleep(self.retry_delay)
        return None

    async def main(self):
        # 認証を非同期で実行
        if not await self.authenticate():
            logging.critical("認証に失敗しました。終了します。")
            return

        # ユーザー名を読み込む
        screen_names = self.load_usernames('xids')
        
        batch_size = 2
        for i in range(0, len(screen_names), batch_size):
            batch = screen_names[i:i + batch_size]
            await asyncio.gather(*(self.process_user_media(name) for name in batch))

async def run_downloader():
    downloader = SecureTwitterMediaDownloader()
    await downloader.main()

if __name__ == "__main__":
    asyncio.run(run_downloader())
