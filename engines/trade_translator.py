"""
Translate trade recommendation reasons to Arabic.
Uses template-based translation (no API calls, no cost).
"""

TEMPLATES_AR = {
    # Signal descriptions
    "agents signal UP": "وكلاء يشيرون لصعود",
    "agents signal DOWN": "وكلاء يشيرون لهبوط",
    "Signal reversed to DOWN": "الإشارة انعكست إلى هبوط — إغلاق المركز",
    "Signal reversed to UP": "الإشارة انعكست إلى صعود",
    "Signal is DOWN, not UP": "الإشارة هبوط وليست صعود",
    "Signal is FLAT, not UP": "الإشارة محايدة وليست صعود",
    
    # Conviction & confidence
    "HIGH conviction": "اقتناع مرتفع",
    "MEDIUM conviction": "اقتناع متوسط",
    "LOW conviction": "اقتناع منخفض",
    "Confidence": "الثقة",
    
    # Risk
    "Risk_Agent PASSED": "وكيل المخاطر: ناجح",
    "Risk_Agent FLAGGED": "وكيل المخاطر: تحذير",
    "Risk_Agent DOWNGRADED": "وكيل المخاطر: تخفيض",
    "Risk_Agent BLOCKED": "وكيل المخاطر: محظور",
    "not safe to enter": "غير آمن للدخول",
    "risk factors": "عوامل مخاطرة",
    "Multiple risk factors": "عوامل مخاطرة متعددة",
    
    # Bull/Bear
    "Bull": "الثور",
    "Bear": "الدب",
    "favorable": "مؤاتية",
    "dominates": "يتفوق على",
    "score": "درجة",
    
    # Position
    "No existing position": "لا يوجد مركز حالي",
    "Opening new long position": "فتح مركز شراء جديد",
    "Position still supported": "المركز لا يزال مدعوماً",
    "Holding since": "محتفظ منذ",
    "days": "أيام",
    "Position at risk": "المركز في خطر",
    "recommending exit": "التوصية بالخروج",
    "Signal too weak to maintain position": "الإشارة ضعيفة جداً للاحتفاظ بالمركز",
    "Risk/reward no longer favorable": "المخاطرة/العائد لم يعد مؤاتياً",
    "Signal FLAT with LOW conviction": "إشارة محايدة باقتناع منخفض",
    "momentum exhausted": "زخم مستنفد",
    
    # Actions
    "BUY": "شراء",
    "SELL": "بيع",
    "HOLD": "احتفاظ",
    "WATCH": "مراقبة",
    
    # Limits & Cooldown
    "Already at max": "وصلت الحد الأقصى",
    "open positions": "مراكز مفتوحة",
    "cooldown after recent SELL": "فترة انتظار بعد بيع حديث",
    "Stock in": "السهم في",
    "-day cooldown": "أيام انتظار",
    
    # Thresholds
    "below": "أقل من",
    "exceeds": "يتجاوز",
    "minimum": "الحد الأدنى",
    "maximum": "الحد الأقصى",
    "threshold": "العتبة",
    "dropped to": "انخفضت إلى",
}

def _to_arabic_numerals(text: str) -> str:
    """Convert Western digits to Arabic-Indic digits."""
    arabic_digits = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')
    return text.translate(arabic_digits)

def translate_reasons(reasons_en: list) -> list:
    """
    Translate English reasons to Arabic using template matching.
    Falls back to English if no template matches.
    """
    reasons_ar = []
    for reason in reasons_en:
        translated = reason
        # Sort keys by length desc to replace longest phrases first
        for en, ar in sorted(TEMPLATES_AR.items(), key=lambda x: len(x[0]), reverse=True):
            if en in translated:
                translated = translated.replace(en, ar)
        
        # Flip numbers to Arabic-Indic numerals
        translated = _to_arabic_numerals(translated)
        reasons_ar.append(translated)
    return reasons_ar
