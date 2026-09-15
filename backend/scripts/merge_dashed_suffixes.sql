-- Merge dashed seed suffixes ("-able" etc.) into their plain counterparts
-- created by the morpheme import. "-or" has no plain counterpart, so its
-- dash is simply stripped. Idempotent.

-- 1) Move word links from dashed rows to plain rows (ignore duplicates).
INSERT IGNORE INTO word_suffix (word_id, morpheme_id)
SELECT ws.word_id, p.id
FROM word_suffix ws
JOIN suffixes d ON d.id = ws.morpheme_id AND d.text LIKE '-%'
JOIN suffixes p ON p.text = SUBSTRING(d.text, 2);

-- 2) Delete links that only belonged to dashed rows with a counterpart.
DELETE ws FROM word_suffix ws
JOIN suffixes d ON d.id = ws.morpheme_id AND d.text LIKE '-%'
JOIN suffixes p ON p.text = SUBSTRING(d.text, 2);

-- 3) Delete dashed suffix rows that had a plain counterpart.
DELETE d FROM suffixes d
JOIN suffixes p ON p.text = SUBSTRING(d.text, 2)
WHERE d.text LIKE '-%';

-- 4) Any remaining dashed suffix (e.g. "-or"): just strip the dash.
UPDATE suffixes SET text = SUBSTRING(text, 2) WHERE text LIKE '-%';
