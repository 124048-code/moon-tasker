"""
月のサイクル計算ロジック
"""
from datetime import datetime, timedelta
import math


class MoonCycleCalculator:
    """月の満ち欠け計算クラス"""
    
    # 既知の新月の日（基準点）
    KNOWN_NEW_MOON = datetime(2000, 1, 6, 18, 14)
    
    # 月の周期（日）
    LUNAR_CYCLE = 29.53058867
    
    def get_moon_phase(self, date: datetime = None) -> float:
        """
        月齢を計算（0.0 = 新月, 0.5 = 満月, 1.0 = 次の新月）
        
        Returns:
            0.0 ~ 1.0 の値
        """
        if date is None:
            date = datetime.now()
        
        # 基準点からの経過日数
        days_since = (date - self.KNOWN_NEW_MOON).total_seconds() / 86400
        
        # 月齢を計算
        phase = (days_since % self.LUNAR_CYCLE) / self.LUNAR_CYCLE
        
        return phase
    
    def get_moon_phase_name(self, date: datetime = None) -> str:
        """月の満ち欠けの名前を取得"""
        phase = self.get_moon_phase(date)
        
        if phase < 0.0625:
            return "新月 🌑"
        elif phase < 0.1875:
            return "三日月 🌒"
        elif phase < 0.3125:
            return "上弦の月 🌓"
        elif phase < 0.4375:
            return "十日夜の月 🌔"
        elif phase < 0.5625:
            return "満月 🌕"
        elif phase < 0.6875:
            return "寝待月 🌖"
        elif phase < 0.8125:
            return "下弦の月 🌗"
        elif phase < 0.9375:
            return "有明月 🌘"
        else:
            return "新月 🌑"
    
    def get_moon_emoji(self, date: datetime = None) -> str:
        """月の絵文字を取得"""
        phase = self.get_moon_phase(date)
        
        if phase < 0.0625:
            return "🌑"
        elif phase < 0.1875:
            return "🌒"
        elif phase < 0.3125:
            return "🌓"
        elif phase < 0.4375:
            return "🌔"
        elif phase < 0.5625:
            return "🌕"
        elif phase < 0.6875:
            return "🌖"
        elif phase < 0.8125:
            return "🌗"
        elif phase < 0.9375:
            return "🌘"
        else:
            return "🌑"
    
    def get_next_new_moon(self, date: datetime = None) -> datetime:
        """次の新月の日を取得"""
        if date is None:
            date = datetime.now()
        
        phase = self.get_moon_phase(date)
        
        # 次の新月までの日数
        days_until = (1.0 - phase) * self.LUNAR_CYCLE
        
        return date + timedelta(days=days_until)
    
    def get_next_full_moon(self, date: datetime = None) -> datetime:
        """次の満月の日を取得"""
        if date is None:
            date = datetime.now()
        
        phase = self.get_moon_phase(date)
        
        # 次の満月までの日数
        if phase < 0.5:
            days_until = (0.5 - phase) * self.LUNAR_CYCLE
        else:
            days_until = (1.5 - phase) * self.LUNAR_CYCLE
        
        return date + timedelta(days=days_until)
    
    def is_new_moon_period(self, date: datetime = None) -> bool:
        """新月期間かどうか（新月の前後2日）"""
        phase = self.get_moon_phase(date)
        return phase < 0.07 or phase > 0.93
    
    def is_full_moon_period(self, date: datetime = None) -> bool:
        """満月期間かどうか（満月の前後2日）"""
        phase = self.get_moon_phase(date)
        return 0.43 < phase < 0.57
