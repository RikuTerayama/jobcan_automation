/**
 * 議事録テキスト解析と抽出
 */

class MinutesParse {
    /**
     * テキストを正規化
     * @param {string} raw - 元のテキスト
     * @returns {string}
     */
    static normalizeText(raw) {
        if (!raw) return '';
        
        // 改行を統一（CRLF → LF）
        let text = raw.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
        
        // 連続する空白を1つに
        text = text.replace(/[ \t]+/g, ' ');
        
        // 行末の空白を削除
        text = text.split('\n').map(line => line.trimEnd()).join('\n');
        
        return text;
    }

    /**
     * テキストを行に分割
     * @param {string} text - テキスト
     * @returns {string[]}
     */
    static splitLines(text) {
        return text.split('\n').filter(line => line.trim().length > 0);
    }

    /**
     * 決定事項候補を抽出
     * @param {string[]} lines - 行配列
     * @returns {Array<{id: string, text: string, sourceLine: number}>}
     */
    static extractDecisionCandidates(lines) {
        const decisions = [];
        const decisionKeywords = ['決定', '合意', '決まった', '了承', '承認', 'Decision', '決定事項'];
        
        lines.forEach((line, index) => {
            const trimmed = line.trim();
            
            // 行頭パターン
            if (/^(決定|Decision|決定事項)[:：]/.test(trimmed)) {
                const text = trimmed.replace(/^(決定|Decision|決定事項)[:：]\s*/, '').trim();
                if (text.length > 0) {
                    decisions.push({
                        id: `dec_${index}`,
                        text: text,
                        sourceLine: index + 1
                    });
                }
            }
            // キーワードを含む行
            else {
                for (const keyword of decisionKeywords) {
                    if (trimmed.includes(keyword)) {
                        // キーワード以降のテキストを抽出
                        const match = trimmed.match(new RegExp(keyword + '[：:：]?\\s*(.+)', 'i'));
                        if (match && match[1]) {
                            const text = match[1].trim();
                            if (text.length > 0 && text.length < 200) {
                                decisions.push({
                                    id: `dec_${index}`,
                                    text: text,
                                    sourceLine: index + 1
                                });
                                break;
                            }
                        }
                    }
                }
            }
        });
        
        return this.dedupeAndSort(decisions, 'text');
    }

    /**
     * ToDo候補を抽出
     * @param {string[]} lines - 行配列
     * @returns {Array<{id: string, title: string, owner: string, due: string, status: string, sourceLine: number}>}
     */
    static extractActionCandidates(lines) {
        const actions = [];
        const actionKeywords = ['TODO', 'ToDo', 'Action', '対応', 'やる', '実施', '確認', '提出', '連絡', 'タスク'];
        const ownerPatterns = [
            /(?:担当|Owner|PIC|by)[：:：]?\s*([^\s,、，]+)/i,
            /([^\s,、，]+)\s*(?:が|が担当|が対応|が実施)/,
            /([^\s,、，]+)\s*(?:に|へ)\s*(?:依頼|依頼する|お願い)/
        ];
        const duePatterns = [
            /(\d{4}[-/]\d{1,2}[-/]\d{1,2})/,
            /(\d{1,2}[-/]\d{1,2})/,
            /(\d{1,2}月\d{1,2}日)/,
            /(本日|明日|明後日|来週|来月|今週|今月)/
        ];
        
        lines.forEach((line, index) => {
            const trimmed = line.trim();
            let isAction = false;
            let isStrongCandidate = false;
            
            // 行頭パターン（強い候補）
            if (/^(A|Action|TODO|ToDo|タスク)[：:：]/.test(trimmed)) {
                isAction = true;
                isStrongCandidate = true;
            }
            // キーワードを含む行
            else {
                for (const keyword of actionKeywords) {
                    if (trimmed.includes(keyword)) {
                        isAction = true;
                        break;
                    }
                }
            }
            
            if (!isAction) return;
            
            // タイトルを抽出
            let title = trimmed;
            if (isStrongCandidate) {
                title = title.replace(/^(A|Action|TODO|ToDo|タスク)[：:：]\s*/i, '').trim();
            }
            
            // 担当を抽出
            let owner = '';
            for (const pattern of ownerPatterns) {
                const match = title.match(pattern);
                if (match && match[1]) {
                    owner = match[1].trim();
                    // タイトルから担当部分を除去
                    title = title.replace(pattern, '').trim();
                    break;
                }
            }
            
            // 期限を抽出
            let due = '';
            for (const pattern of duePatterns) {
                const match = title.match(pattern);
                if (match && match[1]) {
                    due = match[1].trim();
                    // タイトルから期限部分を除去
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
                    due: due,
                    status: 'open',
                    sourceLine: index + 1
                });
            }
        });
        
        return this.dedupeAndSort(actions, 'title');
    }

    /**
     * 重複を除去してソート
     * @param {Array} items - アイテム配列
     * @param {string} key - 比較キー
     * @returns {Array}
     */
    static dedupeAndSort(items, key) {
        const seen = new Set();
        const unique = [];
        
        items.forEach(item => {
            const value = item[key];
            if (!seen.has(value)) {
                seen.add(value);
                unique.push(item);
            }
        });
        
        // sourceLineでソート
        return unique.sort((a, b) => {
            if (a.sourceLine !== undefined && b.sourceLine !== undefined) {
                return a.sourceLine - b.sourceLine;
            }
            return 0;
        });
    }

    /**
     * 候補を抽出
     * @param {string[]} lines - 行配列
     * @returns {{decisions: Array, actions: Array}}
     */
    static extractCandidates(lines) {
        return {
            decisions: this.extractDecisionCandidates(lines),
            actions: this.extractActionCandidates(lines)
        };
    }
}
