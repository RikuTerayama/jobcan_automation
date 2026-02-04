/**
 * 議事録テキスト解析と抽出（v2: 精度改善版）
 */

class MinutesExtract {
    /**
     * 決定事項候補を抽出（v2）
     * @param {string[]} lines - 行配列
     * @returns {Array<{id: string, text: string, confidence: number, accepted: boolean, sources: number[]}>}
     */
    static extractDecisions(lines) {
        const decisions = [];
        const strongKeywords = ['決定', '合意', '了承', '確定', '方針'];
        const labelPatterns = [
            /^(決定|Decision|決定事項|結論)[:：]\s*/i,
            /^(合意|了承|承認)[:：]\s*/i
        ];
        
        lines.forEach((line, index) => {
            const normalized = MinutesNormalize.normalizeLine(line);
            if (!normalized || normalized.length === 0) return;
            
            let confidence = 0;
            let text = normalized;
            
            // ラベルパターン（高スコア）
            for (const pattern of labelPatterns) {
                if (pattern.test(normalized)) {
                    text = normalized.replace(pattern, '').trim();
                    confidence = 90;
                    break;
                }
            }
            
            // 強いキーワード（中スコア）
            if (confidence === 0) {
                for (const keyword of strongKeywords) {
                    if (normalized.includes(keyword)) {
                        const match = normalized.match(new RegExp(keyword + '[：:：]?\\s*(.+)', 'i'));
                        if (match && match[1]) {
                            text = match[1].trim();
                            confidence = 70;
                        } else {
                            confidence = 60;
                        }
                        break;
                    }
                }
            }
            
            // 文末が断定形（加点）
            if (confidence > 0 && /(します|する|でいく|です|である)$/.test(text)) {
                confidence += 5;
            }
            
            if (confidence > 0 && text.length > 0 && text.length < 200) {
                decisions.push({
                    id: `dec_${index}`,
                    text: text,
                    confidence: Math.min(confidence, 100),
                    accepted: confidence >= 60,
                    sources: [index + 1]
                });
            }
        });
        
        return this.dedupeAndMerge(decisions, 'text');
    }

    /**
     * ToDo候補を抽出（v2）
     * @param {string[]} lines - 行配列
     * @returns {Array<{id: string, title: string, owner: string, dueRaw: string, dueNormalized: string, status: string, confidence: number, accepted: boolean, sources: number[]}>}
     */
    static extractActions(lines) {
        const actions = [];
        const strongKeywords = ['TODO', 'ToDo', 'Action', '対応', '実施', '提出', '共有', '作成', '確認', '連絡', '更新', '送付'];
        const requestPatterns = [
            /してください/,
            /お願い/,
            /依頼/,
            /必要/
        ];
        const ownerPatterns = [
            /(?:担当|Owner|PIC|by)[：:：]?\s*([^\s,、，]+)/i,
            /([^\s,、，]+)\s*(?:が|が担当|が対応|が実施)/,
            /([^\s,、，]+)\s*(?:に|へ)\s*(?:依頼|依頼する|お願い)/
        ];
        const duePatterns = [
            /(\d{4}[-/]\d{1,2}[-/]\d{1,2})/,
            /(\d{1,2}[-/]\d{1,2})/,
            /(\d{1,2}月\d{1,2}日)/,
            /(本日|今日|明日|明後日|来週|来月|今週|今月|再来週)/,
            /(来週[月火水木金土日]曜|今週[月火水木金土日]曜)/
        ];
        
        lines.forEach((line, index) => {
            const normalized = MinutesNormalize.normalizeLine(line);
            if (!normalized || normalized.length === 0) return;
            
            let confidence = 0;
            let isStrongCandidate = false;
            
            // 行頭パターン（強い候補）
            if (/^(A|Action|TODO|ToDo|タスク)[：:：]\s*/i.test(normalized)) {
                confidence = 85;
                isStrongCandidate = true;
            }
            // 強いキーワード
            else {
                for (const keyword of strongKeywords) {
                    if (normalized.includes(keyword)) {
                        confidence = 70;
                        break;
                    }
                }
            }
            
            // 依頼表現（加点）
            for (const pattern of requestPatterns) {
                if (pattern.test(normalized)) {
                    confidence = Math.max(confidence, 65);
                    break;
                }
            }
            
            if (confidence === 0) return;
            
            // タイトルを抽出
            let title = normalized;
            if (isStrongCandidate) {
                title = title.replace(/^(A|Action|TODO|ToDo|タスク)[：:：]\s*/i, '').trim();
            }
            
            // 担当を抽出
            let owner = '';
            for (const pattern of ownerPatterns) {
                const match = title.match(pattern);
                if (match && match[1]) {
                    owner = match[1].trim();
                    title = title.replace(pattern, '').trim();
                    break;
                }
            }
            
            // 期限を抽出
            let dueRaw = '';
            for (const pattern of duePatterns) {
                const match = title.match(pattern);
                if (match && match[1]) {
                    dueRaw = match[1].trim();
                    title = title.replace(pattern, '').trim();
                    break;
                }
            }
            
            // タイトルを整形（余分な記号を削除）
            title = title.replace(/^[-•・]\s*/, '').trim();
            
            if (title.length > 0 && title.length < 200) {
                actions.push({
                    id: `action_${index}`,
                    title: title,
                    owner: owner,
                    dueRaw: dueRaw,
                    dueNormalized: '', // 後で正規化
                    status: 'open',
                    confidence: Math.min(confidence, 100),
                    accepted: confidence >= 60,
                    sources: [index + 1]
                });
            }
        });
        
        return this.dedupeAndMerge(actions, 'title');
    }

    /**
     * 重複を統合してソート
     * @param {Array} items - アイテム配列
     * @param {string} key - 比較キー
     * @returns {Array}
     */
    static dedupeAndMerge(items, key) {
        const seen = new Map();
        const merged = [];
        
        items.forEach(item => {
            const value = item[key];
            const normalized = value.toLowerCase().trim();
            
            if (seen.has(normalized)) {
                // 既存アイテムに統合
                const existing = seen.get(normalized);
                existing.sources.push(...item.sources);
                existing.sources = [...new Set(existing.sources)].sort((a, b) => a - b);
                // confidenceは高い方を採用
                if (item.confidence > existing.confidence) {
                    existing.confidence = item.confidence;
                    existing.accepted = item.accepted;
                }
            } else {
                // 新規アイテム
                const newItem = { ...item };
                newItem.sources = [...new Set(newItem.sources)].sort((a, b) => a - b);
                seen.set(normalized, newItem);
                merged.push(newItem);
            }
        });
        
        // sourcesでソート
        return merged.sort((a, b) => {
            if (a.sources && b.sources && a.sources.length > 0 && b.sources.length > 0) {
                return a.sources[0] - b.sources[0];
            }
            return 0;
        });
    }

    /**
     * 候補を抽出（v2統合）
     * @param {string[]} lines - 行配列
     * @param {string} baseDate - 基準日（YYYY-MM-DD形式）
     * @returns {{decisions: Array, actions: Array}}
     */
    static extractCandidates(lines, baseDate = null) {
        const decisions = this.extractDecisions(lines);
        const actions = this.extractActions(lines);
        
        // 日付正規化を適用
        actions.forEach(action => {
            if (action.dueRaw) {
                action.dueNormalized = MinutesDate.normalizeDueDate(action.dueRaw, baseDate);
            }
        });
        
        return {
            decisions,
            actions
        };
    }
}
