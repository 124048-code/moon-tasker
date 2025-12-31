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
            url = f"{SUPABASE_URL}/rest/v1/profiles"
            headers = self._get_headers()
            headers["Prefer"] = "resolution=merge-duplicates"
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
            return response.status_code in [200, 201]
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
