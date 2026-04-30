import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, router } from "./_core/trpc";
import { TRPCError } from "@trpc/server";
import crypto from "crypto";
import {
  verifyPassword,
  createSession,
  getSessionUser,
  deleteSession,
  getAllRewardLinks,
  claimRewardLink,
  getUserById,
  createRewardLink,
  deactivateRewardLink,
  getUserNotifications,
  markNotificationAsRead,
  deleteNotification,
  getAllKeyPackages,
  getKeyPackageById,
  addPointsToUser,
  incrementKeyPackageUsage,
  purchaseKey,
} from "./localDb";

const ONE_YEAR_MS = 365 * 24 * 60 * 60 * 1000;

function getSessionFromCtx(ctx: any) {
  const cookieHeader = ctx.req.headers.cookie || '';
  const cookies = Object.fromEntries(
    cookieHeader.split(';').map((c: string) => {
      const [k, ...v] = c.trim().split('=');
      return [k?.trim(), v.join('=')];
    }).filter(([k]: [string]) => k)
  );
  const token = cookies['alliff_session'] || cookies[COOKIE_NAME];
  if (!token) return null;
  return getSessionUser(token);
}

export const appRouter = router({
  system: systemRouter,

  auth: router({
    me: publicProcedure.query((opts) => {
      const user = getSessionFromCtx(opts.ctx);
      if (!user) return null;
      return {
        id: user.id,
        name: user.username,
        openId: `local_${user.id}`,
        role: user.isAdmin ? 'admin' : 'user',
        points: user.points,
      };
    }),

    logout: publicProcedure.mutation(({ ctx }) => {
      const cookieHeader = ctx.req.headers.cookie || '';
      const cookies = Object.fromEntries(
        cookieHeader.split(';').map((c: string) => {
          const [k, ...v] = c.trim().split('=');
          return [k?.trim(), v.join('=')];
        }).filter(([k]: [string]) => k)
      );
      const token = cookies['alliff_session'] || cookies[COOKIE_NAME];
      if (token) deleteSession(token);
      const cookieOptions = getSessionCookieOptions(ctx.req);
      ctx.res.clearCookie('alliff_session', { ...cookieOptions, maxAge: -1 });
      ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 });
      return { success: true } as const;
    }),

    loginWithCredentials: publicProcedure
      .input((val: any) => ({
        username: val.username as string,
        password: val.password as string,
      }))
      .mutation(async ({ ctx, input }) => {
        const user = verifyPassword(input.username.trim().toLowerCase(), input.password.trim());
        if (!user) {
          throw new TRPCError({
            code: "UNAUTHORIZED",
            message: "اسم المستخدم أو كلمة المرور غير صحيحة",
          });
        }

        const token = crypto.randomBytes(32).toString('hex');
        const expiresAt = new Date(Date.now() + ONE_YEAR_MS);
        createSession(user.id, token, expiresAt);

        const cookieOptions = getSessionCookieOptions(ctx.req);
        ctx.res.cookie('alliff_session', token, {
          ...cookieOptions,
          maxAge: ONE_YEAR_MS,
          httpOnly: true,
        });

        return {
          success: true,
          message: "تم تسجيل الدخول بنجاح",
          user: {
            id: user.id,
            username: user.username,
            points: user.points,
            isAdmin: user.isAdmin,
          },
        };
      }),
  }),

  gems: router({
    getBalance: publicProcedure.query(async ({ ctx }) => {
      const user = getSessionFromCtx(ctx);
      if (!user) return 0;
      return user.points;
    }),

    addGemsFromLink: publicProcedure
      .input((val: any) => ({
        linkId: val.linkId as string,
      }))
      .mutation(async ({ ctx, input }) => {
        const user = getSessionFromCtx(ctx);
        if (!user) {
          throw new TRPCError({ code: "UNAUTHORIZED", message: "يجب تسجيل الدخول أولاً" });
        }

        const result = claimRewardLink(user.id, input.linkId);
        if (!result.success) {
          throw new TRPCError({
            code: "BAD_REQUEST",
            message: result.error || "فشل استخدام الرابط",
          });
        }

        const updatedUser = getUserById(user.id);
        return {
          success: true,
          gemsAdded: result.pointsAdded,
          newBalance: updatedUser?.points || 0,
        };
      }),
  }),

  shortLinks: router({
    getAll: publicProcedure.query(async () => {
      const links = getAllRewardLinks();
      return links.map(l => ({
        id: l.id,
        linkId: l.linkId,
        gemsPerUse: l.pointsPerUse,
        maxUsers: l.maxUsers,
        usedCount: l.usedCount,
        isActive: l.isActive,
        createdAt: l.createdAt,
        externalUrl: l.externalUrl,
        remaining: l.maxUsers - l.usedCount,
      }));
    }),
  }),

  keyPackages: router({
    getAll: publicProcedure.query(async () => {
      const packages = getAllKeyPackages();
      return packages.map((pkg: any) => ({
        id: pkg.id,
        name: pkg.name,
        durationDays: pkg.duration_days,
        botCount: pkg.bot_count,
        gemsPrice: pkg.points_price,
        maxUsers: pkg.max_users,
        usedCount: pkg.used_count,
        isActive: pkg.is_active === 1,
        remaining: pkg.max_users === -1 ? -1 : pkg.max_users - pkg.used_count,
      }));
    }),
  }),

  purchases: router({
    purchaseWithGems: publicProcedure
      .input((val: any) => ({
        packageId: val.packageId as number,
      }))
      .mutation(async ({ ctx, input }) => {
        const user = getSessionFromCtx(ctx);
        if (!user) throw new TRPCError({ code: "UNAUTHORIZED" });
        
        const pkg = getKeyPackageById(input.packageId);
        
        if (!pkg || pkg.is_active === 0) {
          throw new TRPCError({ code: "NOT_FOUND", message: "العرض غير متاح حالياً" });
        }
        
        if (pkg.max_users !== -1 && pkg.used_count >= pkg.max_users) {
          throw new TRPCError({ code: "BAD_REQUEST", message: "وصل هذا العرض للحد الأقصى من المستخدمين" });
        }
        
        if (user.points < pkg.points_price) {
          throw new TRPCError({ code: "BAD_REQUEST", message: "رصيدك غير كافٍ" });
        }
        
        // خصم النقاط وزيادة عداد الاستخدام وإنشاء المفتاح والإشعار
        const purchaseResult = purchaseKey(user.telegramId!, pkg.id);

        if (!purchaseResult.success) {
          throw new TRPCError({ code: "BAD_REQUEST", message: purchaseResult.error || "فشل عملية الشراء" });
        }
        
        return { 
          success: true, 
          key: purchaseResult.key,
          message: "تم شراء المفتاح بنجاح",
          username: purchaseResult.username,
          password: purchaseResult.password,
        };
      }),
    getMyPurchases: publicProcedure.query(async () => {
      return [];
    }),
  }),

  notifications: router({
    getMyNotifications: publicProcedure.query(async ({ ctx }) => {
      const user = getSessionFromCtx(ctx);
      if (!user) return [];
      const notifications = getUserNotifications(user.id);
      return notifications.map((n: any) => ({
        id: n.id,
        title: n.title,
        message: n.message,
        isRead: n.is_read === 1,
        createdAt: n.created_at,
      }));
    }),
    getUnreadCount: publicProcedure.query(async ({ ctx }) => {
      const user = getSessionFromCtx(ctx);
      if (!user) return 0;
      const notifications = getUserNotifications(user.id);
      return notifications.filter((n: any) => n.is_read === 0).length;
    }),
    markAsRead: publicProcedure
      .input((val: any) => ({ id: val.id as number }))
      .mutation(async ({ ctx, input }) => {
        const user = getSessionFromCtx(ctx);
        if (!user) throw new TRPCError({ code: "UNAUTHORIZED" });
        return markNotificationAsRead(input.id);
      }),
    deleteNotification: publicProcedure
      .input((val: any) => ({ id: val.id as number }))
      .mutation(async ({ ctx, input }) => {
        const user = getSessionFromCtx(ctx);
        if (!user) throw new TRPCError({ code: "UNAUTHORIZED" });
        return deleteNotification(input.id);
      }),
  }),

  telegram: router({
    getShortLinks: publicProcedure.query(async () => {
      return getAllRewardLinks();
    }),
  }),
});

export type AppRouter = typeof appRouter;
