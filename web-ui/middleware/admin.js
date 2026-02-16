const ADMIN_COOKIE_NAME = 'xmore_admin_secret';

function getAdminSecretFromRequest(req) {
    const headerSecret = req.headers['x-admin-secret'];
    const cookieSecret = req.cookies ? req.cookies[ADMIN_COOKIE_NAME] : null;
    return headerSecret || cookieSecret || null;
}

function requireAdminSecret(req, res, next) {
    const expectedSecret = process.env.ADMIN_SECRET;
    if (!expectedSecret) {
        return res.status(503).json({
            error: 'Admin interface is not configured',
            details: 'Set ADMIN_SECRET in environment variables'
        });
    }

    const providedSecret = getAdminSecretFromRequest(req);
    if (!providedSecret || providedSecret !== expectedSecret) {
        return res.status(403).json({ error: 'Admin access denied' });
    }

    next();
}

module.exports = {
    ADMIN_COOKIE_NAME,
    getAdminSecretFromRequest,
    requireAdminSecret
};
