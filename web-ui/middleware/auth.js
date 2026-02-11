/**
 * Xmore — JWT Authentication Middleware
 * 
 * Manages JWT tokens via httpOnly cookies.
 * Provides required and optional auth middleware.
 */

const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret-change-in-production-64chars-minimum-abcdef1234567890';
const JWT_EXPIRES_IN = '7d';
const JWT_REFRESH_THRESHOLD = 3 * 24 * 60 * 60; // Refresh if less than 3 days remaining

const COOKIE_OPTIONS = {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
    path: '/'
};

/**
 * Generate a JWT token for a given user ID.
 */
function generateToken(userId) {
    return jwt.sign({ userId }, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN });
}

/**
 * Required authentication middleware.
 * Blocks request with 401 if no valid token.
 */
function authMiddleware(req, res, next) {
    const token = req.cookies?.xmore_token;
    if (!token) {
        return res.status(401).json({ error: 'Not authenticated' });
    }

    try {
        const decoded = jwt.verify(token, JWT_SECRET);
        req.userId = decoded.userId;

        // Auto-refresh: if token has less than 3 days remaining, issue a new one
        const now = Math.floor(Date.now() / 1000);
        if (decoded.exp && (decoded.exp - now) < JWT_REFRESH_THRESHOLD) {
            const newToken = generateToken(decoded.userId);
            res.cookie('xmore_token', newToken, COOKIE_OPTIONS);
        }

        next();
    } catch (err) {
        res.clearCookie('xmore_token', COOKIE_OPTIONS);
        return res.status(401).json({ error: 'Session expired' });
    }
}

/**
 * Optional authentication middleware.
 * Sets req.userId if logged in, but doesn't block.
 */
function optionalAuth(req, res, next) {
    const token = req.cookies?.xmore_token;
    if (token) {
        try {
            const decoded = jwt.verify(token, JWT_SECRET);
            req.userId = decoded.userId;
        } catch (err) {
            // Ignore invalid/expired token
        }
    }
    next();
}

module.exports = {
    generateToken,
    authMiddleware,
    optionalAuth,
    JWT_SECRET,
    COOKIE_OPTIONS
};
