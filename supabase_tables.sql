-- =============================================
-- Moon Tasker - Supabase Tables
-- Run this in Supabase SQL Editor
-- =============================================

-- 1. 月のサイクルテーブル (user_moon_cycles)
CREATE TABLE IF NOT EXISTS user_moon_cycles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    cycle_start DATE NOT NULL,
    cycle_end DATE NOT NULL,
    goal TEXT DEFAULT '',
    status VARCHAR(20) DEFAULT 'active',  -- active, completed
    self_rating INTEGER DEFAULT 0,
    good_points TEXT DEFAULT '',
    improvement_points TEXT DEFAULT '',
    next_actions TEXT DEFAULT '',
    completed_task_count INTEGER DEFAULT 0,
    target_task_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- user_moon_cycles にRLSポリシーを設定
ALTER TABLE user_moon_cycles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own cycles" ON user_moon_cycles
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own cycles" ON user_moon_cycles
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own cycles" ON user_moon_cycles
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own cycles" ON user_moon_cycles
    FOR DELETE USING (auth.uid() = user_id);

-- 2. サイクルタスクテーブル (user_cycle_tasks)
CREATE TABLE IF NOT EXISTS user_cycle_tasks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    cycle_id UUID NOT NULL REFERENCES user_moon_cycles(id) ON DELETE CASCADE,
    task_id UUID NOT NULL REFERENCES user_tasks(id) ON DELETE CASCADE,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(cycle_id, task_id)
);

-- user_cycle_tasks にRLSポリシーを設定
ALTER TABLE user_cycle_tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own cycle tasks" ON user_cycle_tasks
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM user_moon_cycles WHERE id = cycle_id AND user_id = auth.uid())
    );

CREATE POLICY "Users can insert own cycle tasks" ON user_cycle_tasks
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM user_moon_cycles WHERE id = cycle_id AND user_id = auth.uid())
    );

CREATE POLICY "Users can update own cycle tasks" ON user_cycle_tasks
    FOR UPDATE USING (
        EXISTS (SELECT 1 FROM user_moon_cycles WHERE id = cycle_id AND user_id = auth.uid())
    );

CREATE POLICY "Users can delete own cycle tasks" ON user_cycle_tasks
    FOR DELETE USING (
        EXISTS (SELECT 1 FROM user_moon_cycles WHERE id = cycle_id AND user_id = auth.uid())
    );

-- 3. 生命体テーブル (creatures) - 既に存在する場合はスキップ
CREATE TABLE IF NOT EXISTS creatures (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL DEFAULT 'ルナ',
    mood INTEGER DEFAULT 100,
    evolution_stage INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'active',  -- active, completed, dead, runaway
    last_interaction TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    cooldown_until TIMESTAMP WITH TIME ZONE,
    total_tasks INTEGER DEFAULT 0,
    total_minutes INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- creatures にRLSポリシーを設定
ALTER TABLE creatures ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own creatures" ON creatures
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own creatures" ON creatures
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own creatures" ON creatures
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own creatures" ON creatures
    FOR DELETE USING (auth.uid() = user_id);

-- インデックス作成（パフォーマンス向上）
CREATE INDEX IF NOT EXISTS idx_moon_cycles_user_id ON user_moon_cycles(user_id);
CREATE INDEX IF NOT EXISTS idx_moon_cycles_status ON user_moon_cycles(status);
CREATE INDEX IF NOT EXISTS idx_cycle_tasks_cycle_id ON user_cycle_tasks(cycle_id);
CREATE INDEX IF NOT EXISTS idx_creatures_user_id ON creatures(user_id);

-- 確認メッセージ
SELECT 'Tables created successfully!' AS message;
