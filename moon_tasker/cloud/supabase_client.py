"""
Supabase接続とユーザー認証モジュール（HTTP API版）
supabaseパッケージの代わりにhttpxで直接APIを呼び出す
"""
import os
import httpx
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


class SupabaseAuth:
    """Supabase認証を管理するクラス（HTTP API版）"""
    
    def __init__(self):
        self._user = None
        self._session = None
        self._access_token = None
    
    @property
    def is_configured(self) -> bool:
        """Supabaseが設定されているか"""
        return bool(SUPABASE_URL and SUPABASE_KEY)
    
    @property
    def is_authenticated(self) -> bool:
        """ログイン済みか"""
        return self._user is not None
    
    @property
    def user(self) -> Optional[Dict[str, Any]]:
        """現在のユーザー情報"""
        return self._user
    
    @property
    def user_id(self) -> Optional[str]:
        """現在のユーザーID"""
        if self._user:
            return self._user.get("id")
        return None
    
    def _get_headers(self, auth: bool = False) -> dict:
        """APIヘッダーを取得"""
        headers = {
            "apikey": SUPABASE_KEY,
            "Content-Type": "application/json",
        }
        if auth and self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        else:
            headers["Authorization"] = f"Bearer {SUPABASE_KEY}"
        return headers
    
    def sign_in_with_email(self, email: str, password: str) -> dict:
        """Email/Passwordでログイン"""
        if not self.is_configured:
            return {'error': 'Supabaseが設定されていません'}
        
        try:
            url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
            response = httpx.post(
                url,
                headers=self._get_headers(),
                json={"email": email, "password": password},
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                self._access_token = data.get("access_token")
                user_data = data.get("user", {})
                self._user = {
                    "id": user_data.get("id"),
                    "email": user_data.get("email"),
                    "name": user_data.get("user_metadata", {}).get("full_name", email.split("@")[0]),
                    "avatar": user_data.get("user_metadata", {}).get("avatar_url", "")
                }
                return {'success': True}
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('error_description') or error_data.get('msg') or f'エラー({response.status_code})'
                return {'error': error_msg}
        except Exception as e:
            return {'error': f'接続エラー: {str(e)}'}
    
    def sign_up_with_email(self, email: str, password: str) -> dict:
        """Email/Passwordで新規登録"""
        if not self.is_configured:
            return {'error': 'Supabaseが設定されていません'}
        
        try:
            url = f"{SUPABASE_URL}/auth/v1/signup"
            response = httpx.post(
                url,
                headers=self._get_headers(),
                json={"email": email, "password": password},
                timeout=10.0
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                user_data = data.get("user", {})
                self._access_token = data.get("access_token")
                self._user = {
                    "id": user_data.get("id"),
                    "email": user_data.get("email"),
                    "name": email.split("@")[0],
                    "avatar": ""
                }
                return {'success': True}
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('error_description') or error_data.get('msg') or f'エラー({response.status_code})'
                return {'error': error_msg}
        except Exception as e:
            return {'error': f'接続エラー: {str(e)}'}
    
    def sign_out(self) -> bool:
        """ログアウト"""
        self._user = None
        self._session = None
        self._access_token = None
        return True


class SupabaseDB:
    """Supabaseデータベース操作クラス（HTTP API版）"""
    
    def __init__(self, auth: SupabaseAuth):
        self.auth = auth
    
    def _get_headers(self) -> dict:
        """APIヘッダーを取得"""
        headers = {
            "apikey": SUPABASE_KEY,
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        if self.auth._access_token:
            headers["Authorization"] = f"Bearer {self.auth._access_token}"
        else:
            headers["Authorization"] = f"Bearer {SUPABASE_KEY}"
        return headers
    
    # === プロフィール ===
    
    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """ユーザープロフィールを取得"""
        if not SUPABASE_URL:
            return None
        
        try:
            url = f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}&select=*"
            response = httpx.get(url, headers=self._get_headers(), timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                return data[0] if data else None
        except Exception as e:
            print(f"プロフィール取得エラー: {e}")
        return None
    
    def upsert_profile(self, user_id: str, nickname: str, constellation_badge: str = "") -> bool:
        """プロフィールを作成/更新"""
        if not SUPABASE_URL:
            return False
        
        try:
            # Supabase UPSERT: on_conflictパラメータで重複時の更新を指定
            url = f"{SUPABASE_URL}/rest/v1/profiles?on_conflict=id"
            headers = self._get_headers()
            headers["Prefer"] = "return=minimal,resolution=merge-duplicates"
            response = httpx.post(
                url,
                headers=headers,
                json={
                    "id": user_id,
                    "nickname": nickname,
                    "constellation_badge": constellation_badge
                },
                timeout=10.0
            )
            print(f"Upsert profile response: {response.status_code} - {response.text}")
            return response.status_code in [200, 201, 204]
        except Exception as e:
            print(f"プロフィール更新エラー: {e}")
        return False
    
    # === 生命体 ===
    
    def get_creature(self, user_id: str) -> Optional[Dict[str, Any]]:
        """ユーザーの生命体を取得"""
        if not SUPABASE_URL:
            return None
        
        try:
            url = f"{SUPABASE_URL}/rest/v1/creatures?user_id=eq.{user_id}&select=*&order=created_at.desc&limit=1"
            response = httpx.get(url, headers=self._get_headers(), timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                return data[0] if data else None
        except Exception as e:
            print(f"生命体取得エラー: {e}")
        return None
    
    def save_creature(self, user_id: str, creature_data: Dict[str, Any]) -> bool:
        """生命体を保存"""
        if not SUPABASE_URL:
            return False
        
        try:
            creature_data["user_id"] = user_id
            url = f"{SUPABASE_URL}/rest/v1/creatures"
            headers = self._get_headers()
            headers["Prefer"] = "resolution=merge-duplicates"
            response = httpx.post(url, headers=headers, json=creature_data, timeout=10.0)
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"生命体保存エラー: {e}")
        return False
    
    # === フレンド ===
    
    def get_friends(self, user_id: str) -> list:
        """フレンド一覧を取得"""
        if not SUPABASE_URL:
            return []
        
        try:
            url = f"{SUPABASE_URL}/rest/v1/friends?user_id=eq.{user_id}&status=eq.accepted&select=friend_id"
            response = httpx.get(url, headers=self._get_headers(), timeout=10.0)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"フレンド取得エラー: {e}")
        return []
    
    def send_friend_request(self, user_id: str, friend_id: str) -> bool:
        """フレンド申請を送信"""
        if not SUPABASE_URL:
            return False
        
        try:
            url = f"{SUPABASE_URL}/rest/v1/friends"
            response = httpx.post(
                url,
                headers=self._get_headers(),
                json={"user_id": user_id, "friend_id": friend_id, "status": "pending"},
                timeout=10.0
            )
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"フレンド申請エラー: {e}")
        return False
    
    def accept_friend_request(self, user_id: str, friend_id: str) -> bool:
        """フレンド申請を承認"""
        if not SUPABASE_URL:
            return False
        
        try:
            # 申請を承認
            url = f"{SUPABASE_URL}/rest/v1/friends?user_id=eq.{friend_id}&friend_id=eq.{user_id}"
            httpx.patch(url, headers=self._get_headers(), json={"status": "accepted"}, timeout=10.0)
            
            # 相互にフレンド関係を作成
            url = f"{SUPABASE_URL}/rest/v1/friends"
            httpx.post(
                url,
                headers=self._get_headers(),
                json={"user_id": user_id, "friend_id": friend_id, "status": "accepted"},
                timeout=10.0
            )
            return True
        except Exception as e:
            print(f"フレンド承認エラー: {e}")
        return False
    
    def get_friend_creature(self, friend_id: str) -> Optional[Dict[str, Any]]:
        """フレンドの生命体を取得"""
        return self.get_creature(friend_id)
    
    # === プレイリスト ===
    
    def get_user_playlists(self, user_id: str) -> list:
        """ユーザーのプレイリスト一覧を取得"""
        if not SUPABASE_URL:
            print("[GET_USER_PLAYLISTS] No SUPABASE_URL")
            return []
        
        try:
            url = f"{SUPABASE_URL}/rest/v1/user_playlists?user_id=eq.{user_id}&select=*&order=created_at.desc"
            print(f"[GET_USER_PLAYLISTS] URL: {url}")
            response = httpx.get(url, headers=self._get_headers(), timeout=10.0)
            print(f"[GET_USER_PLAYLISTS] Status: {response.status_code}, Response: {response.text[:200] if response.text else 'empty'}")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"プレイリスト取得エラー: {e}")
        return []
    
    def save_user_playlist(self, user_id: str, playlist: Dict[str, Any]) -> Optional[str]:
        """プレイリストを保存（作成/更新）"""
        if not SUPABASE_URL:
            return None
        
        try:
            url = f"{SUPABASE_URL}/rest/v1/user_playlists"
            headers = self._get_headers()
            headers["Prefer"] = "return=representation"
            
            data = {
                "user_id": user_id,
                "name": playlist.get("name", ""),
                "description": playlist.get("description", "")
            }
            
            # IDがあれば更新、なければ作成
            if playlist.get("id"):
                url = f"{SUPABASE_URL}/rest/v1/user_playlists?id=eq.{playlist['id']}"
                response = httpx.patch(url, headers=headers, json=data, timeout=10.0)
            else:
                response = httpx.post(url, headers=headers, json=data, timeout=10.0)
            
            if response.status_code in [200, 201]:
                result = response.json()
                return result[0]["id"] if result else None
        except Exception as e:
            print(f"プレイリスト保存エラー: {e}")
        return None
    
    def delete_user_playlist(self, user_id: str, playlist_id: str) -> bool:
        """プレイリストを削除"""
        if not SUPABASE_URL:
            return False
        
        try:
            url = f"{SUPABASE_URL}/rest/v1/user_playlists?id=eq.{playlist_id}&user_id=eq.{user_id}"
            response = httpx.delete(url, headers=self._get_headers(), timeout=10.0)
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"プレイリスト削除エラー: {e}")
        return False
    
    # === タスク ===
    
    def get_user_tasks(self, user_id: str) -> list:
        """ユーザーのタスク一覧を取得"""
        if not SUPABASE_URL:
            print("[GET_USER_TASKS] No SUPABASE_URL")
            return []
        
        try:
            url = f"{SUPABASE_URL}/rest/v1/user_tasks?user_id=eq.{user_id}&select=*&order=created_at.desc"
            print(f"[GET_USER_TASKS] URL: {url}")
            response = httpx.get(url, headers=self._get_headers(), timeout=10.0)
            print(f"[GET_USER_TASKS] Status: {response.status_code}, Response: {response.text[:200] if response.text else 'empty'}")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"タスク取得エラー: {e}")
        return []
    
    def save_user_task(self, user_id: str, task: Dict[str, Any]) -> Optional[str]:
        """タスクを保存（作成/更新）"""
        if not SUPABASE_URL:
            print("[SAVE_USER_TASK] No SUPABASE_URL")
            return None
        
        try:
            url = f"{SUPABASE_URL}/rest/v1/user_tasks"
            headers = self._get_headers()
            headers["Prefer"] = "return=representation"
            
            data = {
                "user_id": user_id,
                "title": task.get("title", ""),
                "duration": task.get("duration", 25),
                "break_duration": task.get("break_duration", 5),
                "difficulty": task.get("difficulty", 3),
                "priority": task.get("priority", 0),
                "status": task.get("status", "pending")
            }
            
            print(f"[SAVE_USER_TASK] Saving: {data['title']}")
            
            if task.get("id"):
                url = f"{SUPABASE_URL}/rest/v1/user_tasks?id=eq.{task['id']}"
                response = httpx.patch(url, headers=headers, json=data, timeout=10.0)
            else:
                response = httpx.post(url, headers=headers, json=data, timeout=10.0)
            
            print(f"[SAVE_USER_TASK] Status: {response.status_code}, Response: {response.text[:200] if response.text else 'empty'}")
            
            if response.status_code in [200, 201]:
                result = response.json()
                return result[0]["id"] if result else None
        except Exception as e:
            print(f"タスク保存エラー: {e}")
        return None
    
    def delete_user_task(self, user_id: str, task_id: str) -> bool:
        """タスクを削除"""
        if not SUPABASE_URL:
            return False
        
        try:
            url = f"{SUPABASE_URL}/rest/v1/user_tasks?id=eq.{task_id}&user_id=eq.{user_id}"
            response = httpx.delete(url, headers=self._get_headers(), timeout=10.0)
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"タスク削除エラー: {e}")
        return False
    
    # === プレイリストタスク関連 ===
    
    def get_playlist_tasks(self, playlist_id: str) -> list:
        """プレイリスト内のタスクを取得"""
        if not SUPABASE_URL:
            return []
        
        try:
            url = f"{SUPABASE_URL}/rest/v1/user_playlist_tasks?playlist_id=eq.{playlist_id}&select=task_id,task_order,user_tasks(*)&order=task_order"
            response = httpx.get(url, headers=self._get_headers(), timeout=10.0)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"プレイリストタスク取得エラー: {e}")
        return []
    
    def add_task_to_playlist(self, playlist_id: str, task_id: str, order: int = 0) -> bool:
        """タスクをプレイリストに追加"""
        if not SUPABASE_URL:
            return False
        
        try:
            url = f"{SUPABASE_URL}/rest/v1/user_playlist_tasks"
            response = httpx.post(
                url,
                headers=self._get_headers(),
                json={"playlist_id": playlist_id, "task_id": task_id, "task_order": order},
                timeout=10.0
            )
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"プレイリストタスク追加エラー: {e}")
        return False
    
    def remove_task_from_playlist(self, playlist_id: str, task_id: str) -> bool:
        """タスクをプレイリストから削除"""
        if not SUPABASE_URL:
            return False
        
        try:
            url = f"{SUPABASE_URL}/rest/v1/user_playlist_tasks?playlist_id=eq.{playlist_id}&task_id=eq.{task_id}"
            response = httpx.delete(url, headers=self._get_headers(), timeout=10.0)
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"プレイリストタスク削除エラー: {e}")
        return False
    
    # === バッジ ===
    
    def get_user_badges(self, user_id: str) -> list:
        """ユーザーの獲得済みバッジ一覧を取得"""
        if not SUPABASE_URL:
            return []
        
        try:
            url = f"{SUPABASE_URL}/rest/v1/user_badges?user_id=eq.{user_id}&select=*"
            response = httpx.get(url, headers=self._get_headers(), timeout=10.0)
            print(f"[GET_USER_BADGES] Status: {response.status_code}")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"バッジ取得エラー: {e}")
        return []
    
    def save_user_badge(self, user_id: str, badge_name: str) -> bool:
        """バッジを保存（獲得記録）"""
        if not SUPABASE_URL:
            return False
        
        try:
            url = f"{SUPABASE_URL}/rest/v1/user_badges"
            headers = self._get_headers()
            headers["Prefer"] = "return=minimal,resolution=merge-duplicates"
            response = httpx.post(
                url + "?on_conflict=user_id,badge_name",
                headers=headers,
                json={"user_id": user_id, "badge_name": badge_name},
                timeout=10.0
            )
            print(f"[SAVE_USER_BADGE] {badge_name}: {response.status_code}")
            return response.status_code in [200, 201, 204]
        except Exception as e:
            print(f"バッジ保存エラー: {e}")
        return False
    
    def sync_all_badges(self, user_id: str, badge_names: list) -> int:
        """複数バッジを一括同期"""
        count = 0
        for name in badge_names:
            if self.save_user_badge(user_id, name):
                count += 1
        return count
    
    # === フレンドリクエスト ===
    
    def find_user_by_code(self, friend_code: str) -> Optional[Dict]:
        """フレンドコードでユーザーを検索（UUIDの先頭8文字）"""
        if not SUPABASE_URL:
            return None
        
        try:
            # プロフィールテーブルからuser_idの先頭8文字で検索
            url = f"{SUPABASE_URL}/rest/v1/profiles?select=*"
            response = httpx.get(url, headers=self._get_headers(), timeout=10.0)
            print(f"[FIND_USER] Status: {response.status_code}")
            if response.status_code == 200:
                profiles = response.json()
                for p in profiles:
                    uid = p.get('user_id', '')
                    if uid and uid[:8].lower() == friend_code.lower():
                        return p
        except Exception as e:
            print(f"ユーザー検索エラー: {e}")
        return None
    
    def send_friend_request(self, from_user_id: str, friend_code: str) -> bool:
        """フレンドリクエストを送信"""
        if not SUPABASE_URL:
            return False
        
        try:
            # フレンドコードでユーザーを検索
            target_user = self.find_user_by_code(friend_code)
            if not target_user:
                print(f"[SEND_FRIEND_REQUEST] User not found: {friend_code}")
                return False
            
            to_user_id = target_user.get('user_id')
            if to_user_id == from_user_id:
                print("[SEND_FRIEND_REQUEST] Cannot add self")
                return False
            
            url = f"{SUPABASE_URL}/rest/v1/friend_requests"
            headers = self._get_headers()
            headers["Prefer"] = "return=minimal,resolution=ignore-duplicates"
            response = httpx.post(
                url + "?on_conflict=from_user_id,to_user_id",
                headers=headers,
                json={"from_user_id": from_user_id, "to_user_id": to_user_id, "status": "pending"},
                timeout=10.0
            )
            print(f"[SEND_FRIEND_REQUEST] Status: {response.status_code}")
            return response.status_code in [200, 201, 204]
        except Exception as e:
            print(f"フレンドリクエスト送信エラー: {e}")
        return False
    
    def get_pending_requests(self, user_id: str) -> list:
        """受信したフレンドリクエストを取得"""
        if not SUPABASE_URL:
            return []
        
        try:
            url = f"{SUPABASE_URL}/rest/v1/friend_requests?to_user_id=eq.{user_id}&status=eq.pending&select=*"
            response = httpx.get(url, headers=self._get_headers(), timeout=10.0)
            if response.status_code == 200:
                requests = response.json()
                # 送信者のプロフィールを取得して追加
                for req in requests:
                    from_id = req.get('from_user_id')
                    profile = self.get_profile(from_id)
                    req['from_nickname'] = profile.get('nickname', 'Unknown') if profile else 'Unknown'
                return requests
        except Exception as e:
            print(f"リクエスト取得エラー: {e}")
        return []
    
    def accept_friend_request(self, request_id: str, user_id: str) -> bool:
        """フレンドリクエストを承認"""
        if not SUPABASE_URL:
            return False
        
        try:
            # リクエストを承認に更新
            url = f"{SUPABASE_URL}/rest/v1/friend_requests?id=eq.{request_id}&to_user_id=eq.{user_id}"
            response = httpx.patch(
                url,
                headers=self._get_headers(),
                json={"status": "accepted"},
                timeout=10.0
            )
            print(f"[ACCEPT_FRIEND] Status: {response.status_code}")
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"承認エラー: {e}")
        return False
    
    def reject_friend_request(self, request_id: str, user_id: str) -> bool:
        """フレンドリクエストを拒否"""
        if not SUPABASE_URL:
            return False
        
        try:
            url = f"{SUPABASE_URL}/rest/v1/friend_requests?id=eq.{request_id}&to_user_id=eq.{user_id}"
            response = httpx.delete(url, headers=self._get_headers(), timeout=10.0)
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"拒否エラー: {e}")
        return False
    
    def get_friends_list(self, user_id: str) -> list:
        """承認済みフレンド一覧を取得"""
        if not SUPABASE_URL:
            return []
        
        try:
            # 自分が送信して承認されたもの + 自分が受信して承認したもの
            url1 = f"{SUPABASE_URL}/rest/v1/friend_requests?from_user_id=eq.{user_id}&status=eq.accepted&select=*"
            url2 = f"{SUPABASE_URL}/rest/v1/friend_requests?to_user_id=eq.{user_id}&status=eq.accepted&select=*"
            
            friends = []
            
            r1 = httpx.get(url1, headers=self._get_headers(), timeout=10.0)
            if r1.status_code == 200:
                for req in r1.json():
                    friend_id = req.get('to_user_id')
                    profile = self.get_profile(friend_id)
                    friends.append({
                        'friend_id': friend_id,
                        'nickname': profile.get('nickname', 'Unknown') if profile else 'Unknown',
                        'title': profile.get('constellation_badge', '') if profile else ''
                    })
            
            r2 = httpx.get(url2, headers=self._get_headers(), timeout=10.0)
            if r2.status_code == 200:
                for req in r2.json():
                    friend_id = req.get('from_user_id')
                    profile = self.get_profile(friend_id)
                    friends.append({
                        'friend_id': friend_id,
                        'nickname': profile.get('nickname', 'Unknown') if profile else 'Unknown',
                        'title': profile.get('constellation_badge', '') if profile else ''
                    })
            
            return friends
        except Exception as e:
            print(f"フレンド一覧取得エラー: {e}")
        return []

# シングルトンインスタンス
_auth_instance: Optional[SupabaseAuth] = None
_db_instance: Optional[SupabaseDB] = None


def get_auth() -> SupabaseAuth:
    """認証インスタンスを取得"""
    global _auth_instance
    if _auth_instance is None:
        _auth_instance = SupabaseAuth()
    return _auth_instance


def get_cloud_db() -> SupabaseDB:
    """クラウドDBインスタンスを取得"""
    global _db_instance
    if _db_instance is None:
        _db_instance = SupabaseDB(get_auth())
    return _db_instance
