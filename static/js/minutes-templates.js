/**
 * 議事録テンプレート生成
 */

class MinutesTemplates {
    /**
     * テンプレート一覧を取得
     * @returns {Array<{id: string, name: string, description: string}>}
     */
    static getTemplates() {
        return [
            {
                id: 'action',
                name: '決定事項とToDo分解',
                description: '決定事項とToDoを整理した形式'
            },
            {
                id: 'report',
                name: '上司向け報告書',
                description: '背景、目的、論点、決定、次アクション、リスクを含む報告書形式'
            },
            {
                id: 'incident',
                name: 'インシデント用',
                description: 'タイムライン、影響、対応、5Whys、RACIを含むインシデント報告形式'
            }
        ];
    }

    /**
     * 決定事項とToDo分解テンプレートを生成
     * @param {Object} meta - メタ情報
     * @param {Array} decisions - 決定事項配列
     * @param {Array} actions - ToDo配列
     * @param {string} rawText - 原文
     * @returns {string}
     */
    static renderActionTemplate(meta, decisions, actions, rawText) {
        let md = `# ${meta.title || '議事録'}\n\n`;
        
        if (meta.date) {
            md += `**日付:** ${meta.date}\n`;
        }
        if (meta.participants) {
            md += `**参加者:** ${meta.participants}\n`;
        }
        if (meta.author) {
            md += `**作成者:** ${meta.author}\n`;
        }
        
        md += '\n---\n\n';
        
        // 決定事項（acceptedのみ）
        md += '## 決定事項\n\n';
        const acceptedDecisions = decisions.filter(dec => dec.accepted !== false);
        if (acceptedDecisions.length > 0) {
            acceptedDecisions.forEach(dec => {
                md += `- ${dec.text}\n`;
            });
        } else {
            md += '（決定事項なし）\n';
        }
        
        md += '\n---\n\n';
        
        // ToDo（acceptedのみ）
        md += '## ToDo\n\n';
        const acceptedActions = actions.filter(action => action.accepted !== false);
        if (acceptedActions.length > 0) {
            md += '| タスク | 担当 | 期限 | 状態 |\n';
            md += '|--------|------|------|------|\n';
            acceptedActions.forEach(action => {
                const status = action.status === 'done' ? '✅ 完了' : '⏳ 未完了';
                // 期限表示: dueNormalizedがあれば優先、なければdueRaw、なければdue
                let dueDisplay = action.dueNormalized || action.dueRaw || action.due || '-';
                if (action.dueNormalized && action.dueRaw && action.dueNormalized !== action.dueRaw) {
                    dueDisplay = `${action.dueNormalized}（原文: ${action.dueRaw}）`;
                }
                md += `| ${action.title} | ${action.owner || '-'} | ${dueDisplay} | ${status} |\n`;
            });
        } else {
            md += '（ToDoなし）\n';
        }
        
        return md;
    }

    /**
     * 標準（サマリ付き）テンプレートを生成
     * @param {Object} meta - メタ情報
     * @param {Array} decisions - 決定事項配列
     * @param {Array} actions - ToDo配列
     * @param {string} rawText - 原文
     * @returns {string}
     */
    static renderStandardWithSummary(meta, decisions, actions, rawText) {
        let md = `# ${meta.title || '議事録'}\n\n`;
        if (meta.date) {
            md += `**日付:** ${meta.date}\n`;
        }
        if (meta.participants) {
            md += `**参加者:** ${meta.participants}\n`;
        }
        if (meta.author) {
            md += `**作成者:** ${meta.author}\n`;
        }
        md += '\n---\n\n';
        md += '## サマリ\n\n';
        md += '（必要に応じて追記）\n\n';
        md += '---\n\n';
        md += '## 決定事項\n\n';
        const acceptedDecisions = decisions.filter(dec => dec.accepted !== false);
        if (acceptedDecisions.length > 0) {
            acceptedDecisions.forEach(dec => {
                md += `- ${dec.text}\n`;
            });
        } else {
            md += '（決定事項なし）\n';
        }
        md += '\n---\n\n';
        md += '## ToDo\n\n';
        const acceptedActions = actions.filter(action => action.accepted !== false);
        if (acceptedActions.length > 0) {
            md += '| タスク | 担当 | 期限 | 状態 |\n';
            md += '|--------|------|------|------|\n';
            acceptedActions.forEach(action => {
                const status = action.status === 'done' ? '✅ 完了' : '⏳ 未完了';
                const dueDisplay = action.dueNormalized || action.dueRaw || action.due || '-';
                md += `| ${action.title} | ${action.owner || '-'} | ${dueDisplay} | ${status} |\n`;
            });
        } else {
            md += '（ToDoなし）\n';
        }
        return md;
    }

    /**
     * 上司向け報告書テンプレートを生成
     * @param {Object} meta - メタ情報
     * @param {Array} decisions - 決定事項配列
     * @param {Array} actions - ToDo配列
     * @param {string} rawText - 原文
     * @param {Object} userSections - ユーザー入力セクション
     * @returns {string}
     */
    static renderReportTemplate(meta, decisions, actions, rawText, userSections = {}) {
        let md = `# ${meta.title || '会議報告書'}\n\n`;
        
        if (meta.date) {
            md += `**日付:** ${meta.date}\n`;
        }
        if (meta.participants) {
            md += `**参加者:** ${meta.participants}\n`;
        }
        if (meta.author) {
            md += `**作成者:** ${meta.author}\n`;
        }
        
        md += '\n---\n\n';
        
        // 背景
        md += '## 背景\n\n';
        md += userSections.background || '（背景を記入してください）\n';
        md += '\n';
        
        // 目的
        md += '## 目的\n\n';
        md += userSections.purpose || '（目的を記入してください）\n';
        md += '\n';
        
        // 主要論点
        md += '## 主要論点\n\n';
        md += userSections.discussion || '（主要な論点を記入してください）\n';
        md += '\n';
        
        // 決定（acceptedのみ）
        md += '## 決定事項\n\n';
        const acceptedDecisions = decisions.filter(dec => dec.accepted !== false);
        if (acceptedDecisions.length > 0) {
            acceptedDecisions.forEach(dec => {
                md += `- ${dec.text}\n`;
            });
        } else {
            md += '（決定事項なし）\n';
        }
        md += '\n';
        
        // 次アクション（acceptedのみ）
        md += '## 次アクション\n\n';
        const acceptedActions = actions.filter(action => action.accepted !== false);
        if (acceptedActions.length > 0) {
            acceptedActions.forEach(action => {
                const status = action.status === 'done' ? '✅' : '⏳';
                md += `- ${status} ${action.title}`;
                if (action.owner) md += ` (担当: ${action.owner})`;
                // 期限表示: dueNormalizedがあれば優先
                const dueDisplay = action.dueNormalized || action.dueRaw || action.due;
                if (dueDisplay) {
                    if (action.dueNormalized && action.dueRaw && action.dueNormalized !== action.dueRaw) {
                        md += ` (期限: ${action.dueNormalized}（原文: ${action.dueRaw}）)`;
                    } else {
                        md += ` (期限: ${dueDisplay})`;
                    }
                }
                md += '\n';
            });
        } else {
            md += '（次アクションなし）\n';
        }
        md += '\n';
        
        // リスク・懸念
        md += '## リスク・懸念事項\n\n';
        md += userSections.risks || '（リスクや懸念事項を記入してください）\n';
        
        return md;
    }

    /**
     * インシデント用テンプレートを生成
     * @param {Object} incidentMeta - インシデントメタ情報
     * @param {Array} decisions - 決定事項配列
     * @param {Array} actions - ToDo配列
     * @param {string} rawText - 原文
     * @param {Object} incidentSections - インシデントセクション
     * @returns {string}
     */
    static renderIncidentTemplate(incidentMeta, decisions, actions, rawText, incidentSections = {}) {
        let md = `# ${incidentMeta.title || 'インシデント報告書'}\n\n`;
        
        if (incidentMeta.date) {
            md += `**発生日時:** ${incidentMeta.date}\n`;
        }
        if (incidentMeta.severity) {
            md += `**重要度:** ${incidentMeta.severity}\n`;
        }
        if (incidentMeta.systems) {
            md += `**影響システム:** ${incidentMeta.systems}\n`;
        }
        
        md += '\n---\n\n';
        
        // タイムライン
        md += '## タイムライン\n\n';
        md += incidentSections.timeline || '（タイムラインを記入してください）\n';
        md += '\n';
        
        // 影響範囲
        md += '## 影響範囲\n\n';
        md += incidentSections.impact || '（影響範囲を記入してください）\n';
        md += '\n';
        
        // 暫定対応
        md += '## 暫定対応\n\n';
        md += incidentSections.temporary || '（暫定対応を記入してください）\n';
        md += '\n';
        
        // 恒久対応
        md += '## 恒久対応\n\n';
        md += incidentSections.permanent || '（恒久対応を記入してください）\n';
        md += '\n';
        
        // 再発防止
        md += '## 再発防止策\n\n';
        md += incidentSections.prevention || '（再発防止策を記入してください）\n';
        md += '\n';
        
        // 5Whys
        md += '## 5Whys分析\n\n';
        md += incidentSections.why5 || '（5Whys分析を記入してください）\n';
        md += '\n';
        
        // RACI
        md += '## RACI\n\n';
        md += incidentSections.raci || '（RACIを記入してください）\n';
        md += '\n';
        
        // 対応一覧（acceptedのみ）
        md += '## 対応一覧\n\n';
        const acceptedActions = actions.filter(action => action.accepted !== false);
        if (acceptedActions.length > 0) {
            md += '| タスク | 担当 | 期限 | 状態 |\n';
            md += '|--------|------|------|------|\n';
            acceptedActions.forEach(action => {
                const status = action.status === 'done' ? '✅ 完了' : '⏳ 未完了';
                // 期限表示: dueNormalizedがあれば優先
                let dueDisplay = action.dueNormalized || action.dueRaw || action.due || '-';
                if (action.dueNormalized && action.dueRaw && action.dueNormalized !== action.dueRaw) {
                    dueDisplay = `${action.dueNormalized}（原文: ${action.dueRaw}）`;
                }
                md += `| ${action.title} | ${action.owner || '-'} | ${dueDisplay} | ${status} |\n`;
            });
        } else {
            md += '（対応項目なし）\n';
        }
        
        return md;
    }
}
