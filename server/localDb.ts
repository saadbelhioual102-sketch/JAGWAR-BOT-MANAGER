/**
 * قاعدة بيانات SQLite محلية - تعمل بدون MySQL
 * تخزن المستخدمين والروابط والنقاط
 */
import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';
import { generate } from 'random-words';
import bcrypt from 'bcryptjs';
import { customAlphabet } from 'nanoid';
const generatePassword = customAlphabet('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!@#$%^&*()', 12);

const DB_PATH = path.join(process.cwd(), 'data', 'alliff.db');

// إنشاء مجلد البيانات إن لم يكن موجوداً
fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });

let _db: Database.Database | null = null;

export function getLocalDb(): Database.Database {
  if (!_db) {
    _db = new Database(DB_PATH);
    _db.pragma('journal_mode = WAL');
    _db.pragma('foreign_keys = ON');
    initSchema(_db);
  }
  return _db;
}

function initSchema(db: Database.Database) {
  // 1. إنشاء الجداول الأساسية
  db.exec(`
    CREATE TABLE IF NOT EXISTS local_users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      telegram_id TEXT,
      user_id INTEGER UNIQUE DEFAULT NULL,
      points INTEGER DEFAULT 0,
      is_admin INTEGER DEFAULT 0,
      is_banned INTEGER DEFAULT 0,
      delete_attempts INTEGER DEFAULT 3,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS reward_links (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      link_id TEXT UNIQUE NOT NULL,
      points_per_use INTEGER NOT NULL,
      max_users INTEGER NOT NULL,
      used_count INTEGER DEFAULT 0,
      is_active INTEGER DEFAULT 1,
      external_url TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS link_usage (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      link_id TEXT NOT NULL,
      used_at TEXT DEFAULT (datetime('now')),
      UNIQUE(user_id, link_id)
    );

    CREATE TABLE IF NOT EXISTS sessions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      session_token TEXT UNIQUE NOT NULL,
      user_id INTEGER NOT NULL,
      expires_at TEXT NOT NULL,
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS key_packages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      duration_days INTEGER NOT NULL,
      bot_count INTEGER NOT NULL,
      points_price INTEGER NOT NULL,
      max_users INTEGER DEFAULT -1,
      used_count INTEGER DEFAULT 0,
      is_active INTEGER DEFAULT 1,
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS notifications (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      title TEXT NOT NULL,
      message TEXT NOT NULL,
      is_read INTEGER DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now')),
      FOREIGN KEY (user_id) REFERENCES local_users(id)
    );

    CREATE TABLE IF NOT EXISTS site_settings (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      setting_key TEXT UNIQUE NOT NULL,
      setting_value TEXT,
      updated_at TEXT DEFAULT (datetime('now'))
    );
  `);

  // 2. إضافة قيد فريد لـ external_url إذا لم يكن موجوداً (للمنع القاطع للتكرار)
  try {
    // نتحقق أولاً هل العمود موجود، ثم نحاول إضافة الفهرس الفريد
    const columns = db.prepare("PRAGMA table_info(reward_links)").all() as any[];
    const hasUrl = columns.some(c => c.name === 'external_url');
    if (hasUrl) {
      // حذف أي روابط مكررة حالياً قبل إضافة الفهرس لتجنب الخطأ
      db.exec(`
        DELETE FROM reward_links 
        WHERE id NOT IN (
          SELECT MIN(id) FROM reward_links GROUP BY external_url, points_per_use, max_users
        ) AND external_url IS NOT NULL;
      `);
      // إنشاء فهرس فريد يمنع تكرار نفس الرابط الخارجي لنفس الإعدادات
      db.exec(`CREATE UNIQUE INDEX IF NOT EXISTS idx_reward_links_unique_url ON reward_links(external_url) WHERE external_url IS NOT NULL;`);
    }
  } catch (e) {
    console.error("[LocalDB] Error adding unique index:", e);
  }

  // إدراج الإعدادات الافتراضية
  const hasMaintenance = db.prepare("SELECT 1 FROM site_settings WHERE setting_key = 'maintenance_mode'").get();
  if (!hasMaintenance) {
    db.prepare("INSERT INTO site_settings (setting_key, setting_value) VALUES ('maintenance_mode', '0')").run();
  }
}

// ===== تصدير الدوال المطلوبة (مختصرة للبقاء في السياق) =====

export interface LocalUser {
  id: number;
  username: string;
  passwordHash: string;
  telegramId?: string;
  userId?: number;
  points: number;
  isAdmin: boolean;
  isBanned: boolean;
  deleteAttempts: number;
  createdAt: string;
}

export interface RewardLink {
  id: number;
  linkId: string;
  pointsPerUse: number;
  maxUsers: number;
  usedCount: number;
  isActive: boolean;
  externalUrl?: string;
  createdAt: string;
}

function mapUser(row: any): LocalUser {
  return {
    id: row.id,
    username: row.username,
    passwordHash: row.password_hash,
    telegramId: row.telegram_id || undefined,
    userId: row.user_id || undefined,
    points: row.points,
    isAdmin: row.is_admin === 1,
    isBanned: row.is_banned === 1,
    deleteAttempts: row.delete_attempts,
    createdAt: row.created_at,
  };
}

function mapLink(row: any): RewardLink {
  return {
    id: row.id,
    linkId: row.link_id,
    pointsPerUse: row.points_per_use,
    maxUsers: row.max_users,
    usedCount: row.used_count,
    isActive: row.is_active === 1,
    externalUrl: row.external_url || undefined,
    createdAt: row.created_at,
  };
}

export function createUser(username: string, passwordPlain: string, telegramId?: string): LocalUser | null {
  const db = getLocalDb();
  const hash = bcrypt.hashSync(passwordPlain, 10);
  try {
    const result = db.prepare('INSERT INTO local_users (username, password_hash, telegram_id) VALUES (?, ?, ?)').run(
      username.toLowerCase(), hash, telegramId || null
    );
    return getUserById(Number(result.lastInsertRowid));
  } catch (e) {
    return null;
  }
}

export function getUserById(id: number): LocalUser | null {
  const db = getLocalDb();
  const row = db.prepare('SELECT * FROM local_users WHERE id = ?').get(id);
  return row ? mapUser(row) : null;
}

export function getUserByUsername(username: string): LocalUser | null {
  const db = getLocalDb();
  const row = db.prepare('SELECT * FROM local_users WHERE username = ?').get(username.toLowerCase());
  return row ? mapUser(row) : null;
}

export function getUserByTelegramId(telegramId: string): LocalUser | null {
  const db = getLocalDb();
  const row = db.prepare('SELECT * FROM local_users WHERE telegram_id = ?').get(telegramId);
  return row ? mapUser(row) : null;
}

export function createRewardLink(linkId: string, pointsPerUse: number, maxUsers: number, externalUrl?: string): RewardLink | null {
  const db = getLocalDb();
  try {
    // استخدام INSERT OR IGNORE مع الفهرس الفريد لمنع التكرار نهائياً
    const stmt = db.prepare(`
      INSERT OR IGNORE INTO reward_links (link_id, points_per_use, max_users, external_url, used_count, is_active)
      VALUES (?, ?, ?, ?, 0, 1)
    `);
    stmt.run(linkId, pointsPerUse, maxUsers, externalUrl || null);
    
    // إذا كان الرابط موجوداً مسبقاً، نرجعه بدلاً من إنشاء واحد جديد
    if (externalUrl) {
      const existing = db.prepare('SELECT * FROM reward_links WHERE external_url = ?').get(externalUrl);
      if (existing) return mapLink(existing);
    }
    
    return getRewardLink(linkId);
  } catch (e: any) {
    console.error("[LocalDB] Error in createRewardLink:", e.message);
    return null;
  }
}

export function getRewardLink(linkId: string): RewardLink | null {
  const db = getLocalDb();
  const row = db.prepare('SELECT * FROM reward_links WHERE link_id = ?').get(linkId);
  return row ? mapLink(row) : null;
}

export function getAllRewardLinks(): RewardLink[] {
  const db = getLocalDb();
  const rows = db.prepare('SELECT * FROM reward_links WHERE is_active = 1 ORDER BY created_at DESC').all();
  return rows.map(mapLink);
}

export interface KeyPackage {
  id: number;
  name: string;
  durationDays: number;
  botCount: number;
  pointsPrice: number;
  maxUsers: number;
  usedCount: number;
  isActive: boolean;
  createdAt: string;
}

function mapKeyPackage(row: any): KeyPackage {
  return {
    id: row.id,
    name: row.name,
    durationDays: row.duration_days,
    botCount: row.bot_count,
    pointsPrice: row.points_price,
    maxUsers: row.max_users,
    usedCount: row.used_count,
    isActive: row.is_active === 1,
    createdAt: row.created_at,
  };
}

export function createKeyPackage(name: string, durationDays: number, botCount: number, pointsPrice: number, maxUsers: number = -1): KeyPackage | null {
  const db = getLocalDb();
  try {
    const result = db.prepare('INSERT INTO key_packages (name, duration_days, bot_count, points_price, max_users) VALUES (?, ?, ?, ?, ?)').run(
      name, durationDays, botCount, pointsPrice, maxUsers
    );
    return getKeyPackageById(Number(result.lastInsertRowid));
  } catch (e: any) {
    console.error("[LocalDB] Error in createKeyPackage:", e.message);
    return null;
  }
}

export function getAllKeyPackages(): KeyPackage[] {
  const db = getLocalDb();
  const rows = db.prepare('SELECT * FROM key_packages WHERE is_active = 1 ORDER BY created_at DESC').all();
  return rows.map(mapKeyPackage);
}

export function getKeyPackageById(id: number): KeyPackage | null {
  const db = getLocalDb();
  const row = db.prepare('SELECT * FROM key_packages WHERE id = ?').get(id);
  return row ? mapKeyPackage(row) : null;
}

export function purchaseKey(telegramId: string, packageId: number): { success: boolean; username?: string; password?: string; key?: string; error?: string } {
  const db = getLocalDb();
  const pkg = getKeyPackageById(packageId);
  if (!pkg || !pkg.isActive) {
    return { success: false, error: 'عرض المفتاح غير متاح.' };
  }
  if (pkg.maxUsers !== -1 && pkg.usedCount >= pkg.maxUsers) {
    return { success: false, error: 'انتهى عدد المفاتيح المتاحة لهذا العرض.' };
  }

  let user = getUserByTelegramId(telegramId);
  if (!user) {
    // If user doesn't exist, create a new one with a random username and password
    const newUsername = `user_${Math.random().toString(36).substring(2, 10)}`;
    const newPassword = generatePassword();
    user = createUser(newUsername, newPassword, telegramId);
    if (!user) {
      return { success: false, error: 'فشل إنشاء حساب جديد.' };
    }
  }

  if (user.points < pkg.pointsPrice) {
    return { success: false, error: 'نقاطك غير كافية لشراء هذا المفتاح.' };
  }

  try {
    // محاولة إنشاء الحساب في السيرفر الآخر أولاً
    const botManagerUrl = "https://alliff-alliff-bot-manager.hf.space/api/admin/users/create";
    const botSecret = "alliff_bot_api_secret_2026";
    
    const response = await fetch(botManagerUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-bot-secret': botSecret
      },
      body: JSON.stringify({
        username: user!.username,
        password: newPassword,
        max_bots: pkg.botCount,
        days: pkg.durationDays
      })
    });
    
    const botResult = await response.json();
    
    if (!botResult.success && botResult.error !== "المستخدم موجود بالفعل") {
       return { success: false, error: `فشل إنشاء الحساب في السيرفر: ${botResult.error || botResult.message}` };
    }

    db.transaction(() => {
      // Deduct points
      db.prepare('UPDATE local_users SET points = points - ? WHERE id = ?').run(pkg.pointsPrice, user!.id);
      // Increment used count for package
      db.prepare('UPDATE key_packages SET used_count = used_count + 1 WHERE id = ?').run(packageId);
      // Generate a unique key
      const generatedKey = `KEY-${Math.random().toString(36).substring(2, 15).toUpperCase()}`;
      
      // Create notification for the user
      createNotification(user!.id, 'مفتاح جديد', `تم شراء مفتاح جديد بنجاح.\nالاسم: ${user!.username}\nكلمة السر: ${newPassword}\nالمفتاح: ${generatedKey}\nبالتوفيق`);
      return { success: true, username: user!.username, password: newPassword, key: generatedKey };
    })();
  } catch (e: any) {
    console.error("[LocalDB] Error in purchaseKey:", e.message);
    return { success: false, error: 'فشل عملية الشراء أو الربط بالسيرفر.' };
  }
  return { success: false, error: 'خطأ غير متوقع.' };
}

export function createNotification(userId: number, title: string, message: string): boolean {
  const db = getLocalDb();
  try {
    db.prepare("INSERT INTO notifications (user_id, title, message) VALUES (?, ?, ?)").run(userId, title, message);
    return true;
  } catch (e: any) {
    console.error("[LocalDB] Error in createNotification:", e.message);
    return false;
  }
}

export function deactivateRewardLink(linkId: string): boolean {
  const db = getLocalDb();
  const result = db.prepare('UPDATE reward_links SET is_active = 0 WHERE link_id = ?').run(linkId);
  return result.changes > 0;
}

export function claimRewardLink(userId: number, linkId: string): { success: boolean; pointsAdded?: number; error?: string } {
  const db = getLocalDb();
  const link = getRewardLink(linkId);
  if (!link || !link.isActive) return { success: false, error: 'غير متاح' };
  if (link.usedCount >= link.maxUsers) return { success: false, error: 'انتهى الحد' };
  
  const alreadyUsed = db.prepare('SELECT id FROM link_usage WHERE user_id = ? AND link_id = ?').get(userId, linkId);
  if (alreadyUsed) return { success: false, error: 'تم الاستخدام مسبقاً' };
  
  try {
    db.transaction(() => {
      db.prepare('INSERT INTO link_usage (user_id, link_id) VALUES (?, ?)').run(userId, linkId);
      db.prepare('UPDATE reward_links SET used_count = used_count + 1 WHERE link_id = ?').run(linkId);
      db.prepare('UPDATE local_users SET points = points + ? WHERE id = ?').run(link.pointsPerUse, userId);
    })();
    return { success: true, pointsAdded: link.pointsPerUse };
  } catch (e) {
    return { success: false, error: 'فشل' };
  }
}

// دالات أخرى مطلوبة للـ botApi_v2
export function getAllUsers() { return getLocalDb().prepare('SELECT * FROM local_users').all().map(mapUser); }
export function banUser(id: number) { return getLocalDb().prepare('UPDATE local_users SET is_banned = 1 WHERE id = ?').run(id).changes > 0; }
export function unbanUser(id: number) { return getLocalDb().prepare('UPDATE local_users SET is_banned = 0 WHERE id = ?').run(id).changes > 0; }
export function deleteUser(id: number) { return getLocalDb().prepare('DELETE FROM local_users WHERE id = ?').run(id).changes > 0; }
export function setUserPoints(id: number, p: number) { return getLocalDb().prepare('UPDATE local_users SET points = ? WHERE id = ?').run(p, id).changes > 0; }
export function isBanned(id: number) { return !!getLocalDb().prepare('SELECT 1 FROM local_users WHERE id = ? AND is_banned = 1').get(id); }
export function isMaintenanceMode() { 
  const s = getLocalDb().prepare("SELECT setting_value FROM site_settings WHERE setting_key = 'maintenance_mode'").get() as any;
  return s?.setting_value === '1';
}
export function setMaintenanceMode(v: boolean) { 
  return getLocalDb().prepare("UPDATE site_settings SET setting_value = ? WHERE setting_key = 'maintenance_mode'").run(v ? '1' : '0').changes > 0;
}
export function getDeleteAttempts(id: number) {
  const u = getLocalDb().prepare('SELECT delete_attempts FROM local_users WHERE id = ?').get(id) as any;
  return u?.delete_attempts || 0;
}
export function decrementDeleteAttempts(id: number) {
  return getLocalDb().prepare('UPDATE local_users SET delete_attempts = delete_attempts - 1 WHERE id = ?').run(id).changes > 0;
}
export function addDeleteAttempts(id: number, c: number) {
  return getLocalDb().prepare('UPDATE local_users SET delete_attempts = delete_attempts + ? WHERE id = ?').run(c, id).changes > 0;
}
export function assignUserIdToUser(id: number) {
  const customId = 1000 + id;
  getLocalDb().prepare('UPDATE local_users SET user_id = ? WHERE id = ?').run(customId, id);
  return customId;
}
export function getUserByCustomUserId(uid: number) {
  const row = getLocalDb().prepare('SELECT * FROM local_users WHERE user_id = ?').get(uid);
  return row ? mapUser(row) : null;
}
export function createNotification(uid: number, t: string, m: string) {
  const res = getLocalDb().prepare('INSERT INTO notifications (user_id, title, message) VALUES (?, ?, ?)').run(uid, t, m);
  return res.lastInsertRowid;
}
export function getUserNotifications(uid: number) {
  return getLocalDb().prepare('SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC').all();
}
export function markNotificationAsRead(id: number) {
  return getLocalDb().prepare('UPDATE notifications SET is_read = 1 WHERE id = ?').run(id).changes > 0;
}
export function deleteNotification(id: number) {
  return getLocalDb().prepare('DELETE FROM notifications WHERE id = ?').run(id).changes > 0;
}
export function verifyPassword(u: string, p: string) {
  const user = getUserByUsername(u);
  if (user && bcrypt.compareSync(p, user.passwordHash)) return user;
  return null;
}
export function createSession(uid: number, t: string, e: Date) {
  getLocalDb().prepare('DELETE FROM sessions WHERE user_id = ?').run(uid);
  getLocalDb().prepare('INSERT INTO sessions (session_token, user_id, expires_at) VALUES (?, ?, ?)').run(t, uid, e.toISOString());
}
export function deleteSession(t: string) { getLocalDb().prepare('DELETE FROM sessions WHERE session_token = ?').run(t); }
export function addPointsToUser(uid: number, p: number) {
  return getLocalDb().prepare('UPDATE local_users SET points = points + ? WHERE id = ?').run(p, uid).changes > 0;
}
export function getAllKeyPackages() { return getLocalDb().prepare('SELECT * FROM key_packages WHERE is_active = 1').all(); }
export function getKeyPackageById(id: number) { return getLocalDb().prepare('SELECT * FROM key_packages WHERE id = ?').get(id) as any; }
export function incrementKeyPackageUsage(id: number) { return getLocalDb().prepare('UPDATE key_packages SET used_count = used_count + 1 WHERE id = ?').run(id).changes > 0; }
export function createKeyPackage(n: string, d: number, b: number, p: number, m: number) {
  const res = getLocalDb().prepare('INSERT INTO key_packages (name, duration_days, bot_count, points_price, max_users) VALUES (?, ?, ?, ?, ?)').run(n, d, b, p, m);
  return res.lastInsertRowid;
}
export function deactivateKeyPackage(id: number) { return getLocalDb().prepare('UPDATE key_packages SET is_active = 0 WHERE id = ?').run(id).changes > 0; }
