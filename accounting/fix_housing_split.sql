-- 住房 62条子类拆分修正脚本
-- 生成时间: 2026-05-21
-- 57条自动修正 + 5条待确认（需人工处理后手动追加）

UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = '9a6e838a';  -- 2024-11-07 ¥1,400.34 房贷公积金
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = '946dc48f';  -- 2024-11-07 ¥4,569.24 房贷
UPDATE transactions SET child_category = '物业费', updated_at = datetime('now') WHERE id = '453c17b4';  -- 2024-12-06 ¥445.00 物业
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = 'fdcb4e3f';  -- 2024-12-07 ¥4,569.00 
UPDATE transactions SET child_category = '电费', updated_at = datetime('now') WHERE id = '9c02bbc5';  -- 2024-12-08 ¥370.60 电费
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = 'dd570120';  -- 2024-12-09 ¥1,400.34 房贷
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = 'ff67e074';  -- 2025-01-07 ¥4,497.75 
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = 'a0be6a49';  -- 2025-01-07 ¥1,398.47 
UPDATE transactions SET child_category = '物业费', updated_at = datetime('now') WHERE id = '27e16e17';  -- 2025-01-07 ¥159.00 物业
UPDATE transactions SET child_category = '电费', updated_at = datetime('now') WHERE id = 'a080b1c0';  -- 2025-01-09 ¥292.00 电费
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = '259ccdf0';  -- 2025-02-07 ¥4,497.75 房贷
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = '9df925f1';  -- 2025-02-08 ¥1,391.12 
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = '6e470df6';  -- 2025-03-07 ¥5,888.87 房贷
UPDATE transactions SET child_category = '电费', updated_at = datetime('now') WHERE id = 'dc4bb985';  -- 2025-03-11 ¥281.06 电费
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = '1873b969';  -- 2025-04-07 ¥5,888.87 房贷
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = '86f6f9b4';  -- 2025-05-07 ¥5,888.87 房贷
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = '174908cc';  -- 2025-06-07 ¥5,888.87 房贷
UPDATE transactions SET child_category = '电费', updated_at = datetime('now') WHERE id = 'a26dcc71';  -- 2025-06-09 ¥620.71 电费
UPDATE transactions SET child_category = '水费', updated_at = datetime('now') WHERE id = 'b0c6e3aa';  -- 2025-07-04 ¥126.43 水费
UPDATE transactions SET child_category = '物业费', updated_at = datetime('now') WHERE id = '2aa321ef';  -- 2025-07-04 ¥309.30 物业
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = '72d5f514';  -- 2025-07-07 ¥5,888.87 房贷
UPDATE transactions SET child_category = '电费', updated_at = datetime('now') WHERE id = 'e25819b4';  -- 2025-07-09 ¥794.95 电费
UPDATE transactions SET child_category = '物业费', updated_at = datetime('now') WHERE id = 'aa51b9ea';  -- 2025-08-06 ¥309.30 物业
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = 'cb8c1761';  -- 2025-08-07 ¥5,888.87 房贷
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = '427e1125';  -- 2025-09-08 ¥4,497.75 
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = '83933899';  -- 2025-09-08 ¥1,391.12 
UPDATE transactions SET child_category = '物业费', updated_at = datetime('now') WHERE id = 'f16f01fb';  -- 2025-09-09 ¥427.00 物业
UPDATE transactions SET child_category = '电费', updated_at = datetime('now') WHERE id = '8a3f6750';  -- 2025-09-09 ¥789.56 电费
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = 'c42f7513';  -- 2025-10-07 ¥4,497.75 房贷
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = '8122867c';  -- 2025-10-09 ¥1,391.12 
UPDATE transactions SET child_category = '物业费', updated_at = datetime('now') WHERE id = 'd0c003f1';  -- 2025-10-14 ¥309.30 物业
UPDATE transactions SET child_category = '物业费', updated_at = datetime('now') WHERE id = '3e350b59';  -- 2025-11-05 ¥309.30 物业
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = 'de116b01';  -- 2025-11-07 ¥5,876.00 房贷
UPDATE transactions SET child_category = '水费', updated_at = datetime('now') WHERE id = '247bd6be';  -- 2025-11-07 ¥287.83 水费
UPDATE transactions SET child_category = '电费', updated_at = datetime('now') WHERE id = '3644f9c6';  -- 2025-11-09 ¥437.31 电费
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = 'ff0af861';  -- 2025-12-07 ¥4,497.75 
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = '4f90febb';  -- 2025-12-09 ¥1,330.04 
UPDATE transactions SET child_category = '电费', updated_at = datetime('now') WHERE id = '216557b9';  -- 2025-12-09 ¥319.10 电费
UPDATE transactions SET child_category = '燃气费', updated_at = datetime('now') WHERE id = '785a5597';  -- 2025-12-10 ¥77.26 燃气8月—12月8日，总费用448.5
UPDATE transactions SET child_category = '水费', updated_at = datetime('now') WHERE id = 'a5ff5997';  -- 2026-01-06 ¥332.13 水费
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = '032074d3';  -- 2026-01-07 ¥5,879.73 
UPDATE transactions SET child_category = '物业费', updated_at = datetime('now') WHERE id = 'd7ae2fe5';  -- 2026-01-07 ¥309.30 物业
UPDATE transactions SET child_category = '电费', updated_at = datetime('now') WHERE id = '7867a799';  -- 2026-01-09 ¥256.88 电费
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = '12bf63ae';  -- 2026-02-07 ¥5,879.73 
UPDATE transactions SET child_category = '物业费', updated_at = datetime('now') WHERE id = '261fdb6d';  -- 2026-02-09 ¥309.30 物业
UPDATE transactions SET child_category = '电费', updated_at = datetime('now') WHERE id = 'c9a8d584';  -- 2026-02-09 ¥277.30 电费
UPDATE transactions SET child_category = '燃气费', updated_at = datetime('now') WHERE id = '7ce36843';  -- 2026-03-03 ¥779.70 燃气
UPDATE transactions SET child_category = '水费', updated_at = datetime('now') WHERE id = 'd07cd52c';  -- 2026-03-04 ¥323.27 水费
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = '0bb21468';  -- 2026-03-07 ¥5,879.73 
UPDATE transactions SET child_category = '物业费', updated_at = datetime('now') WHERE id = '13a8865b';  -- 2026-03-09 ¥309.30 物业
UPDATE transactions SET child_category = '电费', updated_at = datetime('now') WHERE id = 'f9b7731a';  -- 2026-03-09 ¥262.36 电费
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = '07eab5b7';  -- 2026-04-07 ¥5,879.73 
UPDATE transactions SET child_category = '电费', updated_at = datetime('now') WHERE id = 'b272adb0';  -- 2026-04-09 ¥361.62 电费
UPDATE transactions SET child_category = '燃气费', updated_at = datetime('now') WHERE id = '9c0281f5';  -- 2026-05-06 ¥773.49 2个月燃气费
UPDATE transactions SET child_category = '房贷', updated_at = datetime('now') WHERE id = '7ff05911';  -- 2026-05-07 ¥5,879.73 
UPDATE transactions SET child_category = '电费', updated_at = datetime('now') WHERE id = '0cb7eafe';  -- 2026-05-07 ¥517.47 电费
UPDATE transactions SET child_category = '物业费', updated_at = datetime('now') WHERE id = '3b5394ec';  -- 2026-05-09 ¥309.30 物业

-- 自动修正: 57条
-- 待确认: 5条
--   2025-03-28 ¥6.00 [测试] 测试  -- TODO: 待x确认
--   2025-04-10 ¥332.95 [空备注小金额]   -- TODO: 待x确认
--   2025-05-07 ¥447.70 [空备注小金额]   -- TODO: 待x确认
--   2025-05-09 ¥419.34 [空备注小金额]   -- TODO: 待x确认
--   2025-05-19 ¥50.00 [补办身份证] 补办身份证  -- TODO: 待x确认
