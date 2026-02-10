-- Migration 004: Create EGX 30 stocks reference table + seed data
-- Part of: Xmore Auth & Watchlist Feature

CREATE TABLE IF NOT EXISTS egx30_stocks (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    name_en VARCHAR(200) NOT NULL,
    name_ar VARCHAR(200) NOT NULL,
    sector_en VARCHAR(100),
    sector_ar VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed EGX 30 stocks (upsert)
INSERT INTO egx30_stocks (symbol, name_en, name_ar, sector_en, sector_ar) VALUES
('COMI.CA', 'Commercial International Bank', 'البنك التجاري الدولي', 'Banking', 'البنوك'),
('HRHO.CA', 'Hermes Holding', 'القابضة المصرية الكويتية (هيرميس)', 'Financial Services', 'الخدمات المالية'),
('TMGH.CA', 'Talaat Moustafa Group', 'مجموعة طلعت مصطفى', 'Real Estate', 'العقارات'),
('SWDY.CA', 'Elsewedy Electric', 'السويدي إليكتريك', 'Industrials', 'الصناعات'),
('EAST.CA', 'Eastern Company', 'الشرقية (إيسترن كومباني)', 'Consumer Staples', 'السلع الأساسية'),
('ETEL.CA', 'Telecom Egypt', 'المصرية للاتصالات', 'Telecom', 'الاتصالات'),
('ABUK.CA', 'Abu Qir Fertilizers', 'أبو قير للأسمدة', 'Materials', 'المواد'),
('ORWE.CA', 'Oriental Weavers', 'السجاد الشرقية (أوريانتال ويفرز)', 'Consumer Discretionary', 'السلع الاستهلاكية'),
('EFIH.CA', 'EFG Hermes', 'إي إف جي هيرميس', 'Financial Services', 'الخدمات المالية'),
('OCDI.CA', 'Orascom Development', 'أوراسكوم للتنمية', 'Real Estate', 'العقارات'),
('PHDC.CA', 'Palm Hills Development', 'بالم هيلز للتعمير', 'Real Estate', 'العقارات'),
('MNHD.CA', 'Madinet Nasr Housing', 'مدينة نصر للإسكان', 'Real Estate', 'العقارات'),
('CLHO.CA', 'Cleopatra Hospital', 'مستشفى كليوباترا', 'Healthcare', 'الرعاية الصحية'),
('EKHO.CA', 'Ezz Steel', 'حديد عز', 'Materials', 'المواد'),
('AMOC.CA', 'Alexandria Mineral Oils', 'الإسكندرية للزيوت المعدنية', 'Energy', 'الطاقة'),
('ESRS.CA', 'Ezz Steel (Rebars)', 'عز الدخيلة للصلب', 'Materials', 'المواد'),
('HELI.CA', 'Heliopolis Housing', 'مصر الجديدة للإسكان', 'Real Estate', 'العقارات'),
('GBCO.CA', 'GB Auto', 'جي بي أوتو', 'Consumer Discretionary', 'السلع الاستهلاكية'),
('CCAP.CA', 'Citadel Capital (Qalaa)', 'القلعة (سيتاديل كابيتال)', 'Financial Services', 'الخدمات المالية'),
('JUFO.CA', 'Juhayna Food', 'جهينة', 'Consumer Staples', 'السلع الأساسية'),
('SKPC.CA', 'Sidi Kerir Petrochemicals', 'سيدي كرير للبتروكيماويات', 'Materials', 'المواد'),
('ORAS.CA', 'Orascom Construction', 'أوراسكوم للإنشاءات', 'Industrials', 'الصناعات'),
('FWRY.CA', 'Fawry', 'فوري', 'Technology', 'التكنولوجيا'),
('EKHOA.CA', 'Ezz Aldekhela', 'عز الدخيلة', 'Materials', 'المواد'),
('BINV.CA', 'Beltone Financial', 'بلتون المالية القابضة', 'Financial Services', 'الخدمات المالية'),
('EIOD.CA', 'E-Finance', 'إي فاينانس', 'Technology', 'التكنولوجيا'),
('TALM.CA', 'Talem Medical', 'تاليم الطبية', 'Healthcare', 'الرعاية الصحية'),
('ADIB.CA', 'Abu Dhabi Islamic Bank Egypt', 'مصرف أبوظبي الإسلامي – مصر', 'Banking', 'البنوك'),
('DMCR.CA', 'Dice Medical & Scientific', 'دايس الطبية والعلمية', 'Healthcare', 'الرعاية الصحية'),
('ASCM.CA', 'Arabian Cement', 'الأسمنت العربية', 'Materials', 'المواد')
ON CONFLICT (symbol) DO UPDATE SET
  name_en = EXCLUDED.name_en,
  name_ar = EXCLUDED.name_ar,
  sector_en = EXCLUDED.sector_en,
  sector_ar = EXCLUDED.sector_ar,
  is_active = TRUE,
  updated_at = CURRENT_TIMESTAMP;
